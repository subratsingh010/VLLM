import json
from pathlib import Path

import pytest

from pipeline_3.scripts.prepare_tuning import build_candidates, validate_source
from pipeline_3.scripts.rank_results import rank


def test_search_builds_six_linked_candidates() -> None:
    serve, bench = build_candidates(
        {"max_num_seqs": [1, 2, 4], "max_num_batched_tokens": [1024, 2048]}
    )
    assert len(serve) == 6
    assert len(bench) == 3
    assert {value["max_num_seqs"] for value in serve.values()} == {1, 2, 4}


def test_source_must_be_complete(tmp_path: Path) -> None:
    (tmp_path / "metadata").mkdir()
    (tmp_path / "RUN_STATUS.json").write_text(json.dumps({"status": "analyzed"}))
    (tmp_path / "metadata" / "artifact_inventory.json").write_text("{}")
    with pytest.raises(ValueError, match="must be complete"):
        validate_source(tmp_path)


def test_rank_uses_saved_official_metrics_and_constraints(tmp_path: Path) -> None:
    (tmp_path / "objective.json").write_text(
        json.dumps(
            {
                "constraints": {
                    "p95_ttft_ms_max": 5000,
                    "p95_e2el_ms_max": 20000,
                    "failed_max": 0,
                }
            }
        )
    )
    first = tmp_path / "official_sweep" / "tuning" / "candidate-a" / "run=0.json"
    second = tmp_path / "official_sweep" / "tuning" / "candidate-b" / "run=0.json"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_text(
        json.dumps(
            {
                "max_num_seqs": 1,
                "max_num_batched_tokens": 1024,
                "p95_ttft_ms": 2000,
                "p95_e2el_ms": 10000,
                "failed": 0,
                "output_throughput": 10,
            }
        )
    )
    second.write_text(
        json.dumps(
            {
                "max_num_seqs": 2,
                "max_num_batched_tokens": 1024,
                "p95_ttft_ms": 6000,
                "p95_e2el_ms": 15000,
                "failed": 0,
                "output_throughput": 20,
            }
        )
    )
    rows = rank(tmp_path)
    assert rows[0]["max_num_seqs"] == 1
    assert rows[0]["eligible"] is True
    assert rows[1]["eligible"] is False
