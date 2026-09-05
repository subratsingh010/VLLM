from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any

import psutil
import typer
from prometheus_client.parser import text_string_to_metric_families


@dataclass(frozen=True)
class CapacityPoint:
    id: str
    axis: str
    input_tokens: int
    output_tokens: int
    max_concurrency: int
    request_rate: float | str
    requests: int


def load_matrix(path: Path) -> tuple[dict[str, Any], list[CapacityPoint]]:
    matrix: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return matrix, [CapacityPoint(**point) for point in matrix["points"]]


def build_official_command(
    *,
    vllm_binary: Path,
    base_url: str,
    served_model: str,
    tokenizer: Path,
    point: CapacityPoint,
    matrix: dict[str, Any],
    pipeline: str,
    result_dir: Path,
) -> list[str]:
    return [
        str(vllm_binary),
        "bench",
        "serve",
        "--backend",
        "openai-chat",
        "--endpoint",
        "/v1/chat/completions",
        "--base-url",
        base_url,
        "--model",
        served_model,
        "--served-model-name",
        served_model,
        "--tokenizer",
        str(tokenizer),
        "--dataset-name",
        "random",
        "--random-input-len",
        str(point.input_tokens),
        "--random-output-len",
        str(point.output_tokens),
        "--random-range-ratio",
        "0",
        "--num-prompts",
        str(point.requests),
        "--num-warmups",
        str(matrix["warmups"]),
        "--max-concurrency",
        str(point.max_concurrency),
        "--request-rate",
        str(point.request_rate),
        "--burstiness",
        str(matrix["burstiness"]),
        "--seed",
        str(matrix["seed"]),
        "--temperature",
        "0",
        "--top-p",
        "1",
        "--ignore-eos",
        "--percentile-metrics",
        "ttft,tpot,itl,e2el",
        "--metric-percentiles",
        ",".join(map(str, matrix["percentiles"])),
        "--extra-body",
        '{"chat_template_kwargs":{"enable_thinking":false}}',
        "--save-result",
        "--save-detailed",
        "--disable-tqdm",
        "--result-dir",
        str(result_dir),
        "--result-filename",
        "official.json",
        "--request-id-prefix",
        f"{pipeline}-{point.id}-",
        "--metadata",
        f"pipeline={pipeline}",
        f"capacity_point={point.id}",
    ]


def find_model_processes(model_path: Path) -> list[psutil.Process]:
    needle = str(model_path.resolve())
    roots: list[psutil.Process] = []
    # Do not prefetch cmdline through process_iter(attrs=...). On macOS a
    # short-lived protected process can make the iterator itself raise a
    # SystemError before our per-process exception handler runs.
    for process in psutil.process_iter():
        try:
            command = " ".join(process.cmdline() or [])
            if "vllm" in command and "serve" in command and needle in command:
                roots.append(process)
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError, SystemError):
            continue
    by_pid: dict[int, psutil.Process] = {}
    for root in roots:
        by_pid[root.pid] = root
        for child in root.children(recursive=True):
            by_pid[child.pid] = child
    return list(by_pid.values())


def scrape_metrics(url: str, wanted: set[str]) -> list[dict[str, Any]]:
    try:
        with urllib.request.urlopen(url, timeout=1) as response:
            body = response.read().decode()
    except Exception:
        return []
    values: list[dict[str, Any]] = []
    for family in text_string_to_metric_families(body):
        for sample in family.samples:
            if sample.name in wanted:
                values.append(
                    {
                        "name": sample.name,
                        "labels": dict(sample.labels),
                        "value": float(sample.value),
                    }
                )
    return values


def resource_sample(model_path: Path, metrics_url: str, gateway_metrics_url: str) -> dict[str, Any]:
    processes = find_model_processes(model_path)
    rss = 0
    cpu = 0.0
    for process in processes:
        try:
            rss += process.memory_info().rss
            cpu += process.cpu_percent(interval=None)
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    memory, swap = psutil.virtual_memory(), psutil.swap_memory()
    return {
        "timestamp_ns": time.time_ns(),
        "model_process_count": len(processes),
        "model_process_rss_bytes": rss,
        "model_process_cpu_percent": cpu,
        "system_available_bytes": memory.available,
        "system_memory_percent": memory.percent,
        "swap_used_bytes": swap.used,
        "vllm_metrics": scrape_metrics(
            metrics_url,
            {
                "vllm:num_requests_running",
                "vllm:num_requests_waiting",
                "vllm:kv_cache_usage_perc",
                "vllm:prefix_cache_hits",
                "vllm:prefix_cache_queries",
                "vllm:prompt_tokens_total",
                "vllm:generation_tokens_total",
            },
        ),
        "gateway_metrics": scrape_metrics(
            gateway_metrics_url,
            {
                "llm_gateway_requests_total",
                "llm_gateway_active_requests",
                "llm_gateway_queued_requests",
            },
        ),
        "metal_utilization": None,
        "metal_utilization_reason": "no reliable non-privileged sampler validated",
    }


def run_point(
    command: list[str],
    point: CapacityPoint,
    model_path: Path,
    metrics_url: str,
    gateway_metrics_url: str,
    point_dir: Path,
    timeout_seconds: float,
    interval_seconds: float,
) -> None:
    point_dir.mkdir(parents=True, exist_ok=False)
    (point_dir / "command.json").write_text(
        json.dumps({"argv": command, "point": asdict(point)}, indent=2) + "\n"
    )
    with (
        (point_dir / "stdout.log").open("w", encoding="utf-8") as output,
        (point_dir / "resources.jsonl").open("w", encoding="utf-8") as resources,
    ):
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT, text=True)
        started = time.monotonic()
        while process.poll() is None:
            resources.write(
                json.dumps(resource_sample(model_path, metrics_url, gateway_metrics_url)) + "\n"
            )
            resources.flush()
            if time.monotonic() - started > timeout_seconds:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                raise TimeoutError(f"official benchmark point timed out: {point.id}")
            time.sleep(interval_seconds)
        if process.returncode:
            raise RuntimeError(f"official benchmark point failed: {point.id}")


def main(
    pipeline: Annotated[str, typer.Option()],
    base_url: Annotated[str, typer.Option()],
    served_model: Annotated[str, typer.Option()],
    model_path: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option()],
    metrics_url: Annotated[str, typer.Option()] = "http://127.0.0.1:8101/metrics",
    gateway_metrics_url: Annotated[str, typer.Option()] = "http://127.0.0.1:8111/metrics",
    matrix_path: Annotated[Path, typer.Option()] = Path("benchmark/capacity_matrix.json"),
    vllm_binary: Annotated[Path, typer.Option()] = Path("/Users/subrat/.venv-vllm-metal/bin/vllm"),
) -> None:
    matrix, points = load_matrix(matrix_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    matrix_output = output_dir / "matrix.json"
    if matrix_output.exists():
        saved_matrix = json.loads(matrix_output.read_text(encoding="utf-8"))
        if saved_matrix != matrix:
            raise ValueError("refusing to resume with a different capacity matrix")
    else:
        matrix_output.write_text(json.dumps(matrix, indent=2) + "\n")
    for point in points:
        point_dir = output_dir / point.id
        if (point_dir / "official.json").exists():
            continue
        if point_dir.exists():
            raise FileExistsError(
                f"incomplete point directory must be archived before resume: {point_dir}"
            )
        command = build_official_command(
            vllm_binary=vllm_binary,
            base_url=base_url,
            served_model=served_model,
            tokenizer=model_path,
            point=point,
            matrix=matrix,
            pipeline=pipeline,
            result_dir=point_dir,
        )
        run_point(
            command,
            point,
            model_path,
            metrics_url,
            gateway_metrics_url,
            point_dir,
            float(matrix["point_timeout_seconds"]),
            float(matrix["sampling_interval_seconds"]),
        )


if __name__ == "__main__":
    typer.run(main)
