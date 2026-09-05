import json
from pathlib import Path

import pytest

from pipeline_b.scripts.state import require_state, transition
from pipeline_b.scripts.validate_benchmark import validate_benchmark


def make_run(tmp_path: Path, state: str = "configured") -> Path:
    run = tmp_path / "run"
    run.mkdir()
    (run / "RUN_STATUS.json").write_text(
        json.dumps({"status": state, "history": [], "variant": "int4_mlx", "run_id": "run"})
    )
    return run


def test_state_transition_is_recorded(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    updated = transition(run, "conversion_planned", {"test": True})
    assert updated["status"] == "conversion_planned"
    assert updated["history"][-1]["details"] == {"test": True}


def test_invalid_state_transition_is_rejected(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    with pytest.raises(ValueError, match="configured -> benchmarked"):
        transition(run, "benchmarked")


def test_required_state_gate(tmp_path: Path) -> None:
    run = make_run(tmp_path, "converted")
    with pytest.raises(ValueError, match="expected"):
        require_state(run, {"artifacts_verified"})


def test_benchmark_validation_preserves_failed_requests(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    metadata = run / "metadata"
    metadata.mkdir()
    (metadata / "benchmark_matrix.json").write_text(
        json.dumps(
            {
                "points": [
                    {
                        "id": "point-1",
                        "requests": 2,
                    }
                ]
            }
        )
    )
    point = run / "benchmark" / "point-1"
    point.mkdir(parents=True)
    metrics = {
        "completed": 1,
        "failed": 1,
        "p50_ttft_ms": 1,
        "p95_ttft_ms": 1,
        "p99_ttft_ms": 1,
        "p50_tpot_ms": 1,
        "p95_tpot_ms": 1,
        "p99_tpot_ms": 1,
        "p50_itl_ms": 1,
        "p95_itl_ms": 1,
        "p99_itl_ms": 1,
        "p50_e2el_ms": 1,
        "p95_e2el_ms": 1,
        "p99_e2el_ms": 1,
        "request_throughput": 1,
        "output_throughput": 1,
        "total_token_throughput": 1,
    }
    (point / "official.json").write_text(json.dumps(metrics))
    (point / "command.json").write_text("{}")
    (point / "resources.jsonl").write_text("{}\n")
    result = validate_benchmark(run)
    assert result["completed_requests"] == 1
    assert result["failed_requests"] == 1


def test_benchmark_validation_rejects_wrong_request_count(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    metadata = run / "metadata"
    metadata.mkdir()
    (metadata / "benchmark_matrix.json").write_text(
        json.dumps({"points": [{"id": "missing", "requests": 2}]})
    )
    with pytest.raises(ValueError, match="missing official"):
        validate_benchmark(run)
