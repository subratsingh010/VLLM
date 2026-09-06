from __future__ import annotations

import itertools
import json
import re
import shlex
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class TuningSource:
    kind: str
    label: str
    model_path: str
    dtype: str
    served_model: str
    source_path: str


def read_json(path: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return value


def build_candidates(search: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    serve: dict[str, Any] = {}
    bench: dict[str, Any] = {}
    for sequences, batched in itertools.product(
        search["max_num_seqs"], search["max_num_batched_tokens"]
    ):
        name = f"seqs-{sequences}-batch-{batched}"
        serve[name] = {
            "max_num_seqs": sequences,
            "max_num_batched_tokens": batched,
            "enable_prefix_caching": False,
        }
    for sequences in search["max_num_seqs"]:
        bench[f"concurrency-{sequences}"] = {"max_concurrency": sequences}
    return serve, bench


def validate_source(variant_run: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    status = read_json(variant_run / "RUN_STATUS.json")
    if status.get("status") != "complete":
        raise ValueError("Pipeline B source run must be complete before tuning")
    inventory = read_json(variant_run / "metadata" / "artifact_inventory.json")
    if not Path(inventory["model_path"]).is_dir():
        raise ValueError("verified source model path is missing")
    return status, inventory


def resolve_source(source: Path, dtype: str, served_model: str) -> TuningSource:
    source = source.resolve()
    if (source / "RUN_STATUS.json").is_file():
        status, inventory = validate_source(source)
        variant = read_json(source / "metadata" / "variant.json")
        resolved_dtype = "auto" if variant["quantized"] else str(variant["precision"])
        return TuningSource(
            kind="pipeline_b_run",
            label=str(status["variant"]),
            model_path=str(Path(inventory["model_path"]).resolve()),
            dtype=resolved_dtype,
            served_model=served_model,
            source_path=str(source),
        )
    required = ("config.json", "tokenizer.json", "tokenizer_config.json")
    if not source.is_dir() or any(not (source / name).is_file() for name in required):
        raise ValueError("source must be a complete Pipeline B run or a local model directory")
    if not list(source.glob("*.safetensors")):
        raise ValueError("local model source has no safetensors weights")
    label = "pipeline_a" if source == (ROOT / "models" / "pipeline_a").resolve() else source.name
    if not RUN_ID.fullmatch(label):
        raise ValueError("model directory name is not safe as a result label")
    return TuningSource(
        kind="local_model_directory",
        label=label,
        model_path=str(source),
        dtype=dtype,
        served_model=served_model,
        source_path=str(source),
    )


def prepare(
    source: Path,
    tuning_run_id: str,
    dtype: str = "auto",
    served_model: str = "Qwen/Qwen3-1.7B",
) -> Path:
    if not RUN_ID.fullmatch(tuning_run_id):
        raise ValueError("invalid tuning run ID")
    resolved = resolve_source(source, dtype, served_model)
    search = read_json(ROOT / "pipeline_3" / "config" / "search_space.json")
    workload = read_json(ROOT / "pipeline_3" / "config" / "workload.json")
    objective = read_json(ROOT / "pipeline_3" / "config" / "objective.json")
    serve_params, bench_params = build_candidates(search)
    if len(serve_params) > int(search["max_candidates"]):
        raise ValueError("search exceeds configured candidate safety limit")
    destination = ROOT / "pipeline_3" / "results" / resolved.label / tuning_run_id
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "official_sweep").mkdir()
    for name, value in (
        ("serve_params.json", serve_params),
        ("bench_params.json", bench_params),
        ("search_space.json", search),
        ("workload.json", workload),
        ("objective.json", objective),
    ):
        (destination / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    port = 8300
    vllm = "/Users/subrat/.venv-vllm-metal/bin/vllm"
    model_arg = shlex.quote(resolved.model_path)
    served_model_arg = shlex.quote(resolved.served_model)
    dtype_arg = shlex.quote(resolved.dtype)
    serve_cmd = (
        f"{vllm} serve {model_arg} --host 127.0.0.1 --port {port} "
        f"--served-model-name {served_model_arg} --dtype {dtype_arg} --max-model-len 4096 "
        "--max-num-seqs 1 --max-num-batched-tokens 1024 --generation-config vllm "
        "--no-enable-prefix-caching"
    )
    bench_cmd = (
        f"{vllm} bench serve --backend openai-chat --base-url http://127.0.0.1:{port} "
        f"--endpoint /v1/chat/completions --model {served_model_arg} "
        f"--tokenizer {model_arg} --dataset-name random "
        f"--random-input-len {workload['input_tokens']} "
        f"--random-output-len {workload['output_tokens']} --random-range-ratio 0 "
        f"--num-prompts {workload['requests']} --num-warmups {workload['warmups']} "
        f"--seed {workload['seed']} --request-rate inf --temperature 0 --top-p 1 "
        "--ignore-eos --disable-tqdm "
        "--extra-body '{\"chat_template_kwargs\":{\"enable_thinking\":false}}'"
    )
    plan = {
        "status": "planned",
        "created_at": datetime.now(UTC).isoformat(),
        "source": asdict(resolved),
        "variant": resolved.label,
        "model_path": resolved.model_path,
        "serve_cmd": serve_cmd,
        "bench_cmd": bench_cmd,
        "candidate_count": len(serve_params),
        "official_utility": "vllm bench sweep serve",
        "executed": False,
    }
    (destination / "PLAN.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return destination


def main(
    source: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    tuning_run_id: Annotated[str, typer.Option()],
    dtype: Annotated[str, typer.Option()] = "auto",
    served_model: Annotated[str, typer.Option()] = "Qwen/Qwen3-1.7B",
) -> None:
    typer.echo(prepare(source, tuning_run_id, dtype, served_model))


if __name__ == "__main__":
    typer.run(main)
