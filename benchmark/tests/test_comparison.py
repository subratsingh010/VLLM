import csv
import json
from pathlib import Path

import pytest

from comparison.compare import (
    compare_point_rows,
    discover_completed,
    discover_completed_tuning,
    percentage_difference,
)


def write_csv(path: Path, value: float = 1.0) -> None:
    path.parent.mkdir(parents=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "p50_ttft_ms"])
        writer.writeheader()
        writer.writerow({"id": "point", "p50_ttft_ms": value})


def test_discovers_only_complete_runs_with_required_artifacts(tmp_path: Path) -> None:
    complete = tmp_path / "int4_mlx" / "run-1"
    write_csv(complete / "analysis" / "capacity.csv")
    (complete / "analysis" / "operating_envelope.json").write_text("{}")
    (complete / "metadata").mkdir()
    (complete / "metadata" / "model.json").write_text("{}")
    (complete / "metadata" / "benchmark_matrix.json").write_text("{}")
    (complete / "RUN_STATUS.json").write_text(
        json.dumps({"status": "complete", "variant": "int4_mlx", "run_id": "run-1"})
    )
    incomplete = tmp_path / "int8_mlx" / "run-2"
    incomplete.mkdir(parents=True)
    (incomplete / "RUN_STATUS.json").write_text(
        json.dumps({"status": "configured", "variant": "int8_mlx", "run_id": "run-2"})
    )
    assert [run.variant for run in discover_completed(tmp_path)] == ["int4_mlx"]


def test_point_comparison_has_absolute_and_percentage_differences() -> None:
    baseline = {"point": {"p50_ttft_ms": "10"}}
    candidate = {"point": {"p50_ttft_ms": "12"}}
    row = compare_point_rows(baseline, candidate, "int4/run")[0]
    assert row["absolute_difference_b_minus_a"] == 2
    assert row["percentage_difference_from_a"] == 20


def test_rejects_different_point_sets() -> None:
    with pytest.raises(ValueError, match="point IDs"):
        compare_point_rows({"a": {}}, {"b": {}}, "variant/run")


def test_rejects_different_workload_configuration() -> None:
    baseline = {"point": {"input_tokens": "64"}}
    candidate = {"point": {"input_tokens": "512"}}
    with pytest.raises(ValueError, match="workload configuration"):
        compare_point_rows(baseline, candidate, "variant/run")


def test_zero_baseline_percentage_is_unavailable() -> None:
    assert percentage_difference(0, 2) is None


def test_discovers_only_analyzed_tuning_runs(tmp_path: Path) -> None:
    run = tmp_path / "int4_mlx" / "tune-1"
    analysis = run / "analysis"
    analysis.mkdir(parents=True)
    (run / "PLAN.json").write_text(json.dumps({"candidate_count": 6}))
    (analysis / "winner.json").write_text(json.dumps({"winner": None}))
    (analysis / "ranking.csv").write_text("eligible\nFalse\n")
    (analysis / "REPORT.md").write_text("# report\n")
    assert [item.run_id for item in discover_completed_tuning(tmp_path)] == ["tune-1"]
