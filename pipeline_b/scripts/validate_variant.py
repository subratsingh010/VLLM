from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from pipeline_b.scripts.common import ROOT, base_config, json_sha256, variant_config


def validate(variant: str) -> dict[str, object]:
    base = base_config()
    selected = variant_config(variant)
    source = ROOT / str(selected["source"])
    matrix = ROOT / str(base["benchmark_matrix"])
    issues: list[str] = []
    if not source.is_dir():
        issues.append(f"local source is missing: {source}")
    if not matrix.is_file():
        issues.append(f"benchmark matrix is missing: {matrix}")
    if selected["conversion"] == "mlx_lm" and selected.get("bits") not in (4, 8):
        issues.append("only validated MLX 4-bit and 8-bit configurations are allowed")
    if selected["category"] == "floating_point" and selected["quantized"]:
        issues.append("floating-point variants cannot be marked quantized")
    return {
        "variant": variant,
        "valid": not issues,
        "issues": issues,
        "support": selected["support"],
        "source": str(source),
        "matrix": str(matrix),
        "matrix_sha256": json_sha256(matrix) if matrix.is_file() else None,
        "performs_model_action": False,
    }


def main(
    variant: Annotated[str, typer.Option(help="Allow-listed variant name")],
    output: Annotated[Path | None, typer.Option(help="Optional JSON output path")] = None,
) -> None:
    result = validate(variant)
    rendered = json.dumps(result, indent=2) + "\n"
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    typer.echo(rendered, nl=False)
    if not result["valid"]:
        raise typer.Exit(1)


if __name__ == "__main__":
    typer.run(main)
