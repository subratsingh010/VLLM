from pathlib import Path


def test_batch_script_has_required_safety_guards() -> None:
    script = Path("pipeline_b/scripts/run_all_variants.sh").read_text(encoding="utf-8")
    assert '--confirm must exactly match --batch-id' in script
    assert 'DEFAULT_VARIANTS="fp16 int8_mlx int4_mlx"' in script
    assert 'trap cleanup EXIT INT TERM' in script
    assert 'benchmark_variant.sh' in script
    assert 'finalize_variant' in script
    assert 'unsupported batch variant' in script
