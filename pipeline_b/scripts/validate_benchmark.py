from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

REQUIRED_OFFICIAL_METRICS = (
    "p50_ttft_ms", "p95_ttft_ms", "p99_ttft_ms",
    "p50_tpot_ms", "p95_tpot_ms", "p99_tpot_ms",
    "p50_itl_ms", "p95_itl_ms", "p99_itl_ms",
    "p50_e2el_ms", "p95_e2el_ms", "p99_e2el_ms",
    "request_throughput", "output_throughput", "total_token_throughput",
)


def validate_benchmark(run: Path) -> dict[str, Any]:
    matrix = json.loads((run / "metadata" / "benchmark_matrix.json").read_text(encoding="utf-8"))
    issues: list[str] = []
    completed_requests = 0
    failed_requests = 0
    for point in matrix["points"]:
        point_dir = run / "benchmark" / point["id"]
        official_path = point_dir / "official.json"
        resources_path = point_dir / "resources.jsonl"
        command_path = point_dir / "command.json"
        if not all(path.is_file() for path in (official_path, resources_path, command_path)):
            issues.append(f"{point['id']}: missing official, command, or resource artifact")
            continue
        try:
            official = json.loads(official_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            issues.append(f"{point['id']}: invalid official JSON")
            continue
        missing = [metric for metric in REQUIRED_OFFICIAL_METRICS if metric not in official]
        if missing:
            issues.append(f"{point['id']}: missing metrics {', '.join(missing)}")
        completed = int(official.get("completed", 0))
        failed = int(official.get("failed", 0))
        if completed + failed != int(point["requests"]):
            issues.append(f"{point['id']}: request count differs from matrix")
        if resources_path.stat().st_size == 0:
            issues.append(f"{point['id']}: resource sample file is empty")
        completed_requests += completed
        failed_requests += failed
    if issues:
        raise ValueError("; ".join(issues))
    return {
        "official_points": len(matrix["points"]),
        "completed_requests": completed_requests,
        "failed_requests": failed_requests,
    }


def main(run: Annotated[Path, typer.Option(exists=True, file_okay=False)]) -> None:
    typer.echo(json.dumps(validate_benchmark(run), indent=2))


if __name__ == "__main__":
    typer.run(main)
