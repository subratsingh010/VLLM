from __future__ import annotations

import itertools
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


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


def prepare(variant_run: Path, tuning_run_id: str) -> Path:
    if not RUN_ID.fullmatch(tuning_run_id):
        raise ValueError("invalid tuning run ID")
    status, inventory = validate_source(variant_run)
    search = read_json(ROOT / "pipeline_3" / "config" / "search_space.json")
    workload = read_json(ROOT / "pipeline_3" / "config" / "workload.json")
    objective = read_json(ROOT / "pipeline_3" / "config" / "objective.json")
    serve_params, bench_params = build_candidates(search)
    if len(serve_params) > int(search["max_candidates"]):
        raise ValueError("search exceeds configured candidate safety limit")
    destination = ROOT / "pipeline_3" / "results" / str(status["variant"]) / tuning_run_id
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
    variant = read_json(variant_run / "metadata" / "variant.json")
    dtype = "auto" if variant["quantized"] else variant["precision"]
    port = 8300
    vllm = "/Users/subrat/.venv-vllm-metal/bin/vllm"
    serve_cmd = (
        f"{vllm} serve {inventory['model_path']} --host 127.0.0.1 --port {port} "
        f"--served-model-name Qwen/Qwen3-1.7B --dtype {dtype} --max-model-len 4096 "
        "--max-num-seqs 1 --max-num-batched-tokens 1024 --generation-config vllm "
        "--no-enable-prefix-caching"
    )
    bench_cmd = (
        f"{vllm} bench serve --backend openai-chat --base-url http://127.0.0.1:{port} "
        "--endpoint /v1/chat/completions --model Qwen/Qwen3-1.7B "
        f"--tokenizer {inventory['model_path']} --dataset-name random "
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
        "source_variant_run": str(variant_run),
        "variant": status["variant"],
        "model_path": inventory["model_path"],
        "serve_cmd": serve_cmd,
        "bench_cmd": bench_cmd,
        "candidate_count": len(serve_params),
        "official_utility": "vllm bench sweep serve",
        "executed": False,
    }
    (destination / "PLAN.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return destination


def main(
    variant_run: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    tuning_run_id: Annotated[str, typer.Option()],
) -> None:
    typer.echo(prepare(variant_run.resolve(), tuning_run_id))


if __name__ == "__main__":
    typer.run(main)
