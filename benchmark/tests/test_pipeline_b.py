import json
from pathlib import Path

import pytest

from pipeline_b.scripts.common import json_sha256, variant_config
from pipeline_b.scripts.quantize import build_command
from pipeline_b.scripts.validate_variant import validate


def test_allow_list_rejects_unknown_variant() -> None:
    with pytest.raises(ValueError, match="unsupported variant"):
        variant_config("gptq")


def test_quantization_command_uses_local_source_and_allowed_bits() -> None:
    command, output = build_command("int4_mlx", "test-run")
    assert command[command.index("--q-bits") + 1] == "4"
    assert "models/pipeline_a" in command[command.index("--hf-path") + 1]
    assert output.parts[-2:] == ("int4_mlx", "test-run")


def test_bf16_is_not_integer_quantization() -> None:
    config = variant_config("bf16")
    assert config["category"] == "floating_point"
    assert config["quantized"] is False


def test_validation_never_performs_model_action() -> None:
    result = validate("int8_mlx")
    assert result["performs_model_action"] is False


def test_json_hash_ignores_formatting(tmp_path: Path) -> None:
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    first.write_text(json.dumps({"a": 1, "b": [2, 3]}))
    second.write_text('{\n  "b": [2, 3], "a": 1\n}')
    assert json_sha256(first) == json_sha256(second)
