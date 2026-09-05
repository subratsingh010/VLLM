from benchmark.capacity_analysis import find_knee


def test_knee_requires_latency_spike_and_throughput_plateau() -> None:
    rows = [
        {
            "id": "c1",
            "axis": "concurrency",
            "max_concurrency": 1,
            "output_throughput": 10,
            "p95_e2el_ms": 100,
            "failed": 0,
        },
        {
            "id": "c2",
            "axis": "concurrency",
            "max_concurrency": 2,
            "output_throughput": 15,
            "p95_e2el_ms": 120,
            "failed": 0,
        },
        {
            "id": "c4",
            "axis": "concurrency",
            "max_concurrency": 4,
            "output_throughput": 15.1,
            "p95_e2el_ms": 180,
            "failed": 0,
        },
    ]
    assert find_knee(rows, "concurrency") == "c4"


def test_knee_is_none_without_saturation_signal() -> None:
    rows = [
        {
            "id": "r1",
            "axis": "request_rate",
            "request_rate": 0.1,
            "output_throughput": 10,
            "p95_e2el_ms": 100,
            "failed": 0,
        },
        {
            "id": "r2",
            "axis": "request_rate",
            "request_rate": 0.2,
            "output_throughput": 15,
            "p95_e2el_ms": 110,
            "failed": 0,
        },
    ]
    assert find_knee(rows, "request_rate") is None
