from pathlib import Path

from benchmark.official_runner import CapacityPoint, build_official_command, load_matrix

ROOT = Path(__file__).parents[2]


def test_capacity_matrix_is_unique_and_within_context() -> None:
    _, points = load_matrix(ROOT / "benchmark" / "capacity_matrix.json")
    assert len({point.id for point in points}) == len(points)
    assert all(point.input_tokens + point.output_tokens <= 4096 for point in points)
    assert {point.axis for point in points} == {
        "token_length",
        "output_length",
        "concurrency",
        "request_rate",
    }


def test_command_delegates_metrics_to_official_vllm() -> None:
    matrix, _ = load_matrix(ROOT / "benchmark" / "capacity_matrix.json")
    point = CapacityPoint("test", "concurrency", 512, 64, 2, "inf", 12)
    command = build_official_command(
        vllm_binary=Path("/vllm"),
        base_url="http://gateway",
        served_model="qwen",
        tokenizer=Path("/model"),
        point=point,
        matrix=matrix,
        pipeline="pipeline_a",
        result_dir=Path("/results"),
    )
    assert command[:3] == ["/vllm", "bench", "serve"]
    assert command[command.index("--percentile-metrics") + 1] == "ttft,tpot,itl,e2el"
    assert command[command.index("--metric-percentiles") + 1] == "50,95,99"
    assert "--save-detailed" in command
    assert "--ignore-eos" in command
