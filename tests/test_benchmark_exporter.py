from __future__ import annotations

import json
from pathlib import Path

from observability import benchmark_exporter


def test_render_metrics_reads_saved_artifacts_only(tmp_path: Path, monkeypatch) -> None:
    point = tmp_path / "pipeline_a" / "capacity-run" / "point-01"
    point.mkdir(parents=True)
    (point / "official.json").write_text(
        json.dumps(
            {
                "p50_ttft_ms": 10.0,
                "p95_ttft_ms": 20.0,
                "p99_e2el_ms": 100.0,
                "request_throughput": 2.5,
                "output_throughput": 50.0,
                "total_token_throughput": 75.0,
                "completed": 5,
                "failed": 1,
            }
        ),
        encoding="utf-8",
    )
    (point / "resources.jsonl").write_text(
        json.dumps(
            {
                "system_memory_percent": 60,
                "swap_used_bytes": 1024,
                "vllm_metrics": [{"name": "vllm:kv_cache_usage_perc", "value": 0.25}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(benchmark_exporter, "DATA_ROOT", tmp_path)

    rendered = benchmark_exporter.render_metrics().decode()

    assert 'metric="ttft",pipeline="pipeline_a",point="point-01",quantile="0.50"' in rendered
    assert 'kind="requests_per_second"' in rendered
    assert 'outcome="failed"' in rendered
    assert 'kind="kv_cache_percent"' in rendered
    assert " 25.0" in rendered


def test_resource_parser_skips_truncated_line(tmp_path: Path) -> None:
    resource_file = tmp_path / "resources.jsonl"
    resource_file.write_text('{"system_memory_percent": 42}\n{"truncated"', encoding="utf-8")

    assert benchmark_exporter.resource_maxima(tmp_path / "official.json")["memory_percent"] == 42
