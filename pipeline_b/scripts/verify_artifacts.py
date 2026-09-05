from __future__ import annotations

import json
from typing import Annotated, Any

import typer

from pipeline_b.scripts.common import ensure_prepared, model_path, sha256, variant_config
from pipeline_b.scripts.state import require_state, transition

REQUIRED_COMMON = ("config.json", "tokenizer.json", "tokenizer_config.json")


def verify(variant: str, run_id: str) -> dict[str, Any]:
    run = ensure_prepared(variant, run_id)
    selected = variant_config(variant)
    required_state = {"converted"} if selected["quantized"] else {"configured"}
    require_state(run, required_state)
    model = model_path(variant, run_id)
    issues: list[str] = []
    if not model.is_dir():
        issues.append(f"model directory is missing: {model}")
    for name in REQUIRED_COMMON:
        if not (model / name).is_file():
            issues.append(f"required artifact is missing: {name}")
    weights = sorted(model.glob("*.safetensors")) if model.is_dir() else []
    if not weights:
        issues.append("no safetensors weights found")
    config_path = model / "config.json"
    quantization: dict[str, Any] | None = None
    if config_path.is_file():
        model_config = json.loads(config_path.read_text(encoding="utf-8"))
        raw_quantization = model_config.get("quantization")
        if isinstance(raw_quantization, dict):
            quantization = raw_quantization
    if selected["quantized"]:
        if quantization is None:
            issues.append("converted config.json has no MLX quantization metadata")
        else:
            if quantization.get("bits") != selected["bits"]:
                issues.append("converted quantization bit width differs from variant config")
            if quantization.get("group_size") != selected["group_size"]:
                issues.append("converted quantization group size differs from variant config")
    elif quantization is not None:
        issues.append("floating-point variant unexpectedly contains quantization metadata")
    if issues:
        raise ValueError("; ".join(issues))
    files = sorted([*weights, *(model / name for name in REQUIRED_COMMON)])
    index = model / "model.safetensors.index.json"
    if index.is_file():
        files.append(index)
    inventory = {
        "variant": variant,
        "model_path": str(model),
        "quantized": selected["quantized"],
        "quantization": quantization,
        "size_bytes": sum(path.stat().st_size for path in files),
        "artifacts": [
            {
                "path": str(path.relative_to(model)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }
    output = run / "metadata" / "artifact_inventory.json"
    output.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    transition(run, "artifacts_verified", {"inventory": str(output)})
    return inventory


def main(variant: Annotated[str, typer.Option()], run_id: Annotated[str, typer.Option()]) -> None:
    typer.echo(json.dumps(verify(variant, run_id), indent=2))


if __name__ == "__main__":
    typer.run(main)
