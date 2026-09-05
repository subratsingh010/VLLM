from __future__ import annotations

import csv
import json
from itertools import pairwise
from pathlib import Path
from typing import Annotated, Any

import matplotlib.pyplot as plt
import typer


def load_points(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for command_path in sorted(run_dir.glob("*/command.json")):
        point_dir = command_path.parent
        official_path = point_dir / "official.json"
        if not official_path.exists():
            continue
        point = json.loads(command_path.read_text())["point"]
        official = json.loads(official_path.read_text())
        total = int(official.get("completed", 0)) + int(official.get("failed", 0))
        resources = [
            json.loads(line)
            for line in (point_dir / "resources.jsonl").read_text().splitlines()
            if line.strip()
        ]
        kv_values = [
            sample["value"]
            for resource in resources
            for sample in resource["vllm_metrics"]
            if sample["name"] == "vllm:kv_cache_usage_perc"
        ]
        rows.append(
            {
                **point,
                "completed": official.get("completed"),
                "failed": official.get("failed"),
                "error_rate": None if total == 0 else official.get("failed", 0) / total,
                "timeout_rate": None,
                "request_throughput": official.get("request_throughput"),
                "output_throughput": official.get("output_throughput"),
                "total_token_throughput": official.get("total_token_throughput"),
                "p50_ttft_ms": official.get("p50_ttft_ms"),
                "p95_ttft_ms": official.get("p95_ttft_ms"),
                "p99_ttft_ms": official.get("p99_ttft_ms"),
                "p50_tpot_ms": official.get("p50_tpot_ms"),
                "p95_tpot_ms": official.get("p95_tpot_ms"),
                "p99_tpot_ms": official.get("p99_tpot_ms"),
                "p50_itl_ms": official.get("p50_itl_ms"),
                "p95_itl_ms": official.get("p95_itl_ms"),
                "p99_itl_ms": official.get("p99_itl_ms"),
                "p50_e2el_ms": official.get("p50_e2el_ms"),
                "p95_e2el_ms": official.get("p95_e2el_ms"),
                "p99_e2el_ms": official.get("p99_e2el_ms"),
                "peak_model_cpu_percent": max(
                    (resource["model_process_cpu_percent"] for resource in resources),
                    default=None,
                ),
                "peak_model_rss_bytes": max(
                    (resource["model_process_rss_bytes"] for resource in resources), default=None
                ),
                "minimum_system_available_bytes": min(
                    (resource["system_available_bytes"] for resource in resources), default=None
                ),
                "peak_system_memory_percent": max(
                    (resource["system_memory_percent"] for resource in resources), default=None
                ),
                "peak_swap_used_bytes": max(
                    (resource["swap_used_bytes"] for resource in resources), default=None
                ),
                "peak_kv_cache_usage": max(kv_values, default=None),
                "metal_utilization": None,
            }
        )
    return rows


def find_knee(rows: list[dict[str, Any]], axis: str) -> str | None:
    axis_rows = [row for row in rows if row["axis"] == axis]
    key = {
        "token_length": lambda row: row["input_tokens"] + row["output_tokens"],
        "output_length": lambda row: row["output_tokens"],
        "concurrency": lambda row: row["max_concurrency"],
        "request_rate": lambda row: float(row["request_rate"]),
    }[axis]
    axis_rows.sort(key=key)
    for previous, current in pairwise(axis_rows):
        previous_throughput = float(previous["output_throughput"] or 0)
        current_throughput = float(current["output_throughput"] or 0)
        previous_p95 = float(previous["p95_e2el_ms"] or 0)
        current_p95 = float(current["p95_e2el_ms"] or 0)
        latency_spike = previous_p95 > 0 and current_p95 >= previous_p95 * 1.25
        throughput_plateau = (
            previous_throughput > 0 and current_throughput <= previous_throughput * 1.02
        )
        throughput_degrade = (
            previous_throughput > 0 and current_throughput < previous_throughput * 0.95
        )
        if current.get("failed", 0) or throughput_degrade or (latency_spike and throughput_plateau):
            return str(current["id"])
    return None


def write_analysis(run_dir: Path, output_dir: Path) -> None:
    rows = load_points(run_dir)
    if not rows:
        raise ValueError("no completed official vLLM benchmark results found")
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "capacity.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    knees = {axis: find_knee(rows, axis) for axis in {row["axis"] for row in rows}}
    (output_dir / "operating_envelope.json").write_text(
        json.dumps(
            {
                "knee_points": knees,
                "interpretation": (
                    "The practical envelope ends at the tested point immediately before each knee."
                ),
                "rule": (
                    "first failure, >5% throughput degradation, or >=25% P95 spike "
                    "with <=2% throughput gain"
                ),
            },
            indent=2,
        )
        + "\n"
    )
    for axis in ("token_length", "concurrency", "request_rate"):
        selected = [row for row in rows if row["axis"] == axis]
        if not selected:
            continue
        x = list(range(len(selected)))
        figure, left = plt.subplots(figsize=(9, 5))
        left.plot(x, [row["p95_e2el_ms"] for row in selected], marker="o", label="P95 E2EL ms")
        left.plot(x, [row["p99_e2el_ms"] for row in selected], marker="o", label="P99 E2EL ms")
        left.plot(x, [row["p95_ttft_ms"] for row in selected], marker="^", label="P95 TTFT ms")
        right = left.twinx()
        right.plot(
            x,
            [row["output_throughput"] for row in selected],
            marker="s",
            color="green",
            label="output tok/s",
        )
        left.set_xticks(x, [row["id"] for row in selected], rotation=25, ha="right")
        left.set_ylabel("Latency (ms)")
        right.set_ylabel("Output tokens/s")
        left.legend(loc="upper left")
        right.legend(loc="upper right")
        figure.tight_layout()
        figure.savefig(output_dir / f"{axis}.png", dpi=160)
        plt.close(figure)


def main(
    run_dir: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    output_dir: Annotated[Path, typer.Option()],
) -> None:
    write_analysis(run_dir, output_dir)


if __name__ == "__main__":
    typer.run(main)
