from __future__ import annotations

import json
import platform
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from pipeline_b.scripts.common import (
    PIPELINE,
    ROOT,
    base_config,
    converted_model_dir,
    json_sha256,
    run_dir,
    variant_config,
)
from pipeline_b.scripts.validate_variant import validate

SUBDIRECTORIES = ("metadata", "conversion", "serving", "benchmark", "analysis", "quality")


def prepare(variant: str, run_id: str) -> Path:
    validation = validate(variant)
    if not validation["valid"]:
        issues = validation["issues"]
        if not isinstance(issues, list):
            raise TypeError("validation issues must be a list")
        raise ValueError("; ".join(str(issue) for issue in issues))
    destination = run_dir(variant, run_id)
    destination.mkdir(parents=True, exist_ok=False)
    for name in SUBDIRECTORIES:
        (destination / name).mkdir()
    base, selected = base_config(), variant_config(variant)
    matrix_source = ROOT / str(base["benchmark_matrix"])
    (destination / "metadata" / "base_model.json").write_text(
        json.dumps(base, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "metadata" / "variant.json").write_text(
        json.dumps(selected, indent=2) + "\n", encoding="utf-8"
    )
    conversion = {
        "method": selected["conversion"],
        "quantized": selected["quantized"],
        "bits": selected.get("bits"),
        "group_size": selected.get("group_size"),
        "executed": False,
    }
    (destination / "metadata" / "conversion.json").write_text(
        json.dumps(conversion, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "metadata" / "benchmark_matrix.json").write_text(
        matrix_source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    environment = {
        "created_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "machine": platform.machine(),
        "platform": platform.platform(),
        "configured_versions": {
            "backend": base["backend_version"],
            "mlx": base["mlx_version"],
            "mlx_lm": base["mlx_lm_version"],
        },
    }
    (destination / "metadata" / "environment.json").write_text(
        json.dumps(environment, indent=2) + "\n", encoding="utf-8"
    )
    status = {
        "schema_version": "1.0",
        "status": "configured",
        "variant": variant,
        "run_id": run_id,
        "base_model": base["model_id"],
        "base_revision": base["revision"],
        "benchmark_matrix_sha256": json_sha256(matrix_source),
        "converted_model_path": (
            str(converted_model_dir(variant, run_id))
            if selected["conversion"] == "mlx_lm"
            else None
        ),
        "history": [],
    }
    (destination / "RUN_STATUS.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    (destination / "REPORT.md").write_text(
        (PIPELINE / "templates" / "REPORT.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return destination


def main(variant: Annotated[str, typer.Option()], run_id: Annotated[str, typer.Option()]) -> None:
    typer.echo(prepare(variant, run_id))


if __name__ == "__main__":
    typer.run(main)
