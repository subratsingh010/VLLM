from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import matplotlib.pyplot as plt
import typer

POINT_METRICS = (
    "p50_ttft_ms", "p95_ttft_ms", "p99_ttft_ms",
    "p50_tpot_ms", "p95_tpot_ms", "p99_tpot_ms",
    "p50_itl_ms", "p95_itl_ms", "p99_itl_ms",
    "p50_e2el_ms", "p95_e2el_ms", "p99_e2el_ms",
    "request_throughput", "output_throughput", "total_token_throughput",
    "error_rate", "peak_system_memory_percent", "peak_swap_used_bytes",
    "peak_kv_cache_usage",
)
POINT_CONFIGURATION = (
    "axis",
    "input_tokens",
    "output_tokens",
    "max_concurrency",
    "request_rate",
    "requests",
)


@dataclass(frozen=True)
class CompletedRun:
    variant: str
    run_id: str
    path: Path
    status: dict[str, Any]


@dataclass(frozen=True)
class CompletedTuningRun:
    source_label: str
    run_id: str
    path: Path
    plan: dict[str, Any]


def json_sha256(path: Path) -> str:
    value = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def read_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def discover_completed(variants_root: Path) -> list[CompletedRun]:
    discovered: list[CompletedRun] = []
    for status_path in sorted(variants_root.glob("*/*/RUN_STATUS.json")):
        status = json.loads(status_path.read_text(encoding="utf-8"))
        if status.get("status") != "complete":
            continue
        run = status_path.parent
        required = (
            run / "analysis" / "capacity.csv",
            run / "analysis" / "operating_envelope.json",
            run / "metadata" / "model.json",
            run / "metadata" / "benchmark_matrix.json",
        )
        if not all(path.is_file() for path in required):
            continue
        discovered.append(
            CompletedRun(str(status["variant"]), str(status["run_id"]), run, status)
        )
    return discovered


def discover_completed_tuning(tuning_root: Path) -> list[CompletedTuningRun]:
    discovered: list[CompletedTuningRun] = []
    if not tuning_root.is_dir():
        return discovered
    for winner_path in sorted(tuning_root.glob("*/*/analysis/winner.json")):
        run = winner_path.parent.parent
        plan_path = run / "PLAN.json"
        ranking_path = run / "analysis" / "ranking.csv"
        report_path = run / "analysis" / "REPORT.md"
        if not all(path.is_file() for path in (plan_path, ranking_path, report_path)):
            continue
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        discovered.append(
            CompletedTuningRun(run.parent.name, run.name, run, plan)
        )
    return discovered


def tuning_rows(runs: list[CompletedTuningRun]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for run in runs:
        winner = json.loads(
            (run.path / "analysis" / "winner.json").read_text(encoding="utf-8")
        ).get("winner")
        rows.append(
            {
                "source_run": f"{run.source_label}/{run.run_id}",
                "source_kind": run.plan.get("source", {}).get("kind", "legacy_pipeline_b_run"),
                "model_path": run.plan.get("model_path", ""),
                "candidate_count": run.plan.get("candidate_count", ""),
                "winner_found": winner is not None,
                "max_num_seqs": "" if winner is None else winner.get("max_num_seqs", ""),
                "max_num_batched_tokens": (
                    "" if winner is None else winner.get("max_num_batched_tokens", "")
                ),
                "mean_p95_ttft_ms": "" if winner is None else winner.get("mean_p95_ttft_ms", ""),
                "mean_p95_e2el_ms": "" if winner is None else winner.get("mean_p95_e2el_ms", ""),
                "mean_output_throughput": (
                    "" if winner is None else winner.get("mean_output_throughput", "")
                ),
                "failed": "" if winner is None else winner.get("failed", ""),
            }
        )
    return rows


def percentage_difference(baseline: float, candidate: float) -> float | None:
    return None if baseline == 0 else (candidate - baseline) / baseline * 100


def compare_point_rows(
    baseline: dict[str, dict[str, str]], candidate: dict[str, dict[str, str]], label: str
) -> list[dict[str, str | float | None]]:
    if baseline.keys() != candidate.keys():
        raise ValueError(f"{label}: benchmark point IDs do not match Pipeline A")
    rows: list[dict[str, str | float | None]] = []
    for point_id in sorted(baseline):
        mismatches = [
            key
            for key in POINT_CONFIGURATION
            if baseline[point_id].get(key) != candidate[point_id].get(key)
        ]
        if mismatches:
            raise ValueError(
                f"{label}/{point_id}: workload configuration differs: {', '.join(mismatches)}"
            )
        for metric in POINT_METRICS:
            raw_a, raw_b = baseline[point_id].get(metric, ""), candidate[point_id].get(metric, "")
            if raw_a == "" or raw_b == "":
                continue
            a, b = float(raw_a), float(raw_b)
            rows.append(
                {
                    "variant_run": label,
                    "point": point_id,
                    "metric": metric,
                    "pipeline_a": a,
                    "pipeline_b": b,
                    "absolute_difference_b_minus_a": b - a,
                    "percentage_difference_from_a": percentage_difference(a, b),
                }
            )
    return rows


def validate_run(run: CompletedRun, baseline_matrix_sha256: str) -> None:
    matrix = run.path / "metadata" / "benchmark_matrix.json"
    if (
        run.status.get("benchmark_matrix_sha256") != baseline_matrix_sha256
        or json_sha256(matrix) != baseline_matrix_sha256
    ):
        raise ValueError(f"{run.variant}/{run.run_id}: benchmark matrix differs from Pipeline A")


def model_row(run: CompletedRun, baseline_size: int) -> dict[str, str | int | float | None]:
    model = json.loads((run.path / "metadata" / "model.json").read_text(encoding="utf-8"))
    size = int(model["size_bytes"])
    return {
        "variant_run": f"{run.variant}/{run.run_id}",
        "pipeline_a_model_size_bytes": baseline_size,
        "pipeline_b_model_size_bytes": size,
        "absolute_difference_b_minus_a": size - baseline_size,
        "percentage_difference_from_a": percentage_difference(float(baseline_size), float(size)),
    }


def knee_rows(baseline_path: Path, run: CompletedRun) -> list[dict[str, str | None]]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))["knee_points"]
    candidate = json.loads(
        (run.path / "analysis" / "operating_envelope.json").read_text(encoding="utf-8")
    )["knee_points"]
    return [
        {
            "variant_run": f"{run.variant}/{run.run_id}",
            "axis": axis,
            "pipeline_a_knee": baseline.get(axis),
            "pipeline_b_knee": candidate.get(axis),
        }
        for axis in sorted(set(baseline) | set(candidate))
    ]


def quality_rows(baseline_path: Path, run: CompletedRun) -> list[dict[str, Any]]:
    candidate_path = run.path / "quality" / "objective.json"
    if not baseline_path.is_file() or not candidate_path.is_file():
        return []
    baseline_raw = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate_raw = json.loads(candidate_path.read_text(encoding="utf-8"))
    baseline = baseline_raw.get("metrics", baseline_raw)
    candidate = candidate_raw.get("metrics", candidate_raw)
    rows: list[dict[str, Any]] = []
    for metric in sorted(set(baseline) & set(candidate)):
        if not isinstance(baseline[metric], int | float) or not isinstance(
            candidate[metric], int | float
        ):
            continue
        a, b = float(baseline[metric]), float(candidate[metric])
        rows.append(
            {
                "variant_run": f"{run.variant}/{run.run_id}",
                "metric": metric,
                "pipeline_a": a,
                "pipeline_b": b,
                "absolute_difference_b_minus_a": b - a,
                "percentage_difference_from_a": percentage_difference(a, b),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_metric(rows: list[dict[str, Any]], metric: str, output: Path) -> None:
    selected = [row for row in rows if row["metric"] == metric]
    if not selected:
        return
    labels = [f'{row["variant_run"]}\n{row["point"]}' for row in selected]
    positions = list(range(len(selected)))
    figure, axis = plt.subplots(figsize=(max(10, len(selected) * 0.65), 5))
    axis.plot(positions, [row["pipeline_a"] for row in selected], marker="o", label="Pipeline A")
    axis.plot(positions, [row["pipeline_b"] for row in selected], marker="s", label="Pipeline B")
    axis.set_xticks(positions, labels, rotation=40, ha="right")
    axis.set_ylabel(metric)
    axis.legend()
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=160)
    plt.close(figure)


def main(
    baseline: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    variants_root: Annotated[Path, typer.Option(file_okay=False)],
    tuning_root: Annotated[Path, typer.Option(file_okay=False)] = Path("pipeline_3/results"),
    output_dir: Annotated[Path, typer.Option()] = Path("comparison/results/comparison-run"),
) -> None:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite comparison output: {output_dir}")
    baseline_csv = baseline.parent.parent / "analysis" / baseline.name / "capacity.csv"
    baseline_matrix = baseline / "matrix.json"
    baseline_config = baseline.parents[1] / "config" / "model.json"
    for required in (baseline_csv, baseline_matrix, baseline_config):
        if not required.is_file():
            raise ValueError(f"Pipeline A artifact missing: {required}")
    baseline_rows = read_csv(baseline_csv)
    matrix_hash = json_sha256(baseline_matrix)
    baseline_size = int(json.loads(baseline_config.read_text(encoding="utf-8"))["downloaded_bytes"])
    completed = discover_completed(variants_root)
    point_rows: list[dict[str, Any]] = []
    model_rows: list[dict[str, Any]] = []
    saturation_rows: list[dict[str, Any]] = []
    objective_rows: list[dict[str, Any]] = []
    completed_tuning = discover_completed_tuning(tuning_root)
    baseline_envelope = (
        baseline.parent.parent / "analysis" / baseline.name / "operating_envelope.json"
    )
    baseline_quality = baseline.parents[1] / "quality" / "objective.json"
    for run in completed:
        validate_run(run, matrix_hash)
        candidate = read_csv(run.path / "analysis" / "capacity.csv")
        point_rows.extend(
            compare_point_rows(baseline_rows, candidate, f"{run.variant}/{run.run_id}")
        )
        model_rows.append(model_row(run, baseline_size))
        saturation_rows.extend(knee_rows(baseline_envelope, run))
        objective_rows.extend(quality_rows(baseline_quality, run))
    write_csv(output_dir / "tables" / "point_comparison.csv", point_rows)
    write_csv(output_dir / "tables" / "model_size_comparison.csv", model_rows)
    write_csv(output_dir / "tables" / "saturation_comparison.csv", saturation_rows)
    write_csv(output_dir / "tables" / "quality_comparison.csv", objective_rows)
    write_csv(output_dir / "tables" / "tuning_runs.csv", tuning_rows(completed_tuning))
    for metric in POINT_METRICS:
        plot_metric(point_rows, metric, output_dir / "charts" / f"{metric}.png")
    manifest = {
        "baseline": str(baseline),
        "baseline_matrix_sha256": matrix_hash,
        "variants": [f"{run.variant}/{run.run_id}" for run in completed],
        "tuning_runs": [f"{run.source_label}/{run.run_id}" for run in completed_tuning],
        "reads_saved_artifacts_only": True,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    report_lines = [
        "# Precision comparison report",
        "",
        "Generated exclusively from completed saved artifacts.",
        "",
        "## Included variant runs",
        "",
        *[f"- `{run.variant}/{run.run_id}`" for run in completed],
        "",
        "## Included Pipeline C tuning runs",
        "",
        *([f"- `{run.source_label}/{run.run_id}`" for run in completed_tuning]
          or ["- No completed tuning runs were discovered."]),
        "",
        "Detailed absolute and percentage differences are in `tables/point_comparison.csv`.",
        "Model-size differences are in `tables/model_size_comparison.csv`.",
        "Saturation knees are in `tables/saturation_comparison.csv`.",
        "Objective quality differences are emitted only when both sides provide them.",
        "Pipeline C winners are listed separately in `tables/tuning_runs.csv` because ",
        "the exploratory tuning workload is not interchangeable with the full baseline matrix.",
        "",
    ]
    (output_dir / "COMPARISON_REPORT.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )


if __name__ == "__main__":
    typer.run(main)
