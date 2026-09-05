from __future__ import annotations

import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer

from pipeline_b.scripts.common import (
    ROOT,
    converted_model_dir,
    ensure_prepared,
    variant_config,
)
from pipeline_b.scripts.state import require_state, transition

MLX_CONVERT = Path("/Users/subrat/.venv-vllm-metal/bin/mlx_lm.convert")


def build_command(variant: str, run_id: str) -> tuple[list[str], Path]:
    config = variant_config(variant)
    if config["conversion"] != "mlx_lm" or config.get("bits") not in (4, 8):
        raise ValueError(f"{variant} is not an allow-listed integer conversion variant")
    source = ROOT / str(config["source"])
    output = converted_model_dir(variant, run_id)
    command = [
        str(MLX_CONVERT),
        "--hf-path",
        str(source),
        "--mlx-path",
        str(output),
        "--quantize",
        "--q-bits",
        str(config["bits"]),
        "--q-group-size",
        str(config["group_size"]),
    ]
    return command, output


def write_plan(run: Path, command: list[str], output: Path, variant: str) -> Path:
    plan = {
        "variant": variant,
        "created_at": datetime.now(UTC).isoformat(),
        "argv": command,
        "output": str(output),
        "executed": False,
    }
    path = run / "conversion" / "command.json"
    path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return path


def main(
    variant: Annotated[str, typer.Option()],
    run_id: Annotated[str, typer.Option()],
    execute: Annotated[
        bool, typer.Option(help="Actually run conversion; omitted means plan only")
    ] = False,
    confirm: Annotated[
        str | None, typer.Option(help="Must exactly equal run-id when --execute is used")
    ] = None,
) -> None:
    run = ensure_prepared(variant, run_id)
    status = require_state(run, {"configured", "conversion_planned"})
    command, output = build_command(variant, run_id)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite converted model: {output}")
    plan_path = write_plan(run, command, output, variant)
    if status["status"] == "configured":
        transition(run, "conversion_planned", {"command_file": str(plan_path)})
    typer.echo(json.dumps({"plan": str(plan_path), "argv": command}, indent=2))
    if not execute:
        typer.echo("Plan only: no conversion was run. Add --execute --confirm RUN_ID manually.")
        return
    if confirm != run_id:
        raise ValueError("--confirm must exactly match --run-id")
    output.parent.mkdir(parents=True, exist_ok=True)
    log_path = run / "conversion" / "conversion.log"
    started = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=False)
    metadata: dict[str, Any] = json.loads(plan_path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "executed": True,
            "returncode": completed.returncode,
            "duration_seconds": time.monotonic() - started,
        }
    )
    plan_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"conversion failed; inspect {log_path}")
    conversion_metadata = {
        "method": "mlx_lm",
        "quantized": True,
        "bits": variant_config(variant)["bits"],
        "group_size": variant_config(variant)["group_size"],
        "executed": True,
        "duration_seconds": metadata["duration_seconds"],
        "returncode": 0,
    }
    (run / "metadata" / "conversion.json").write_text(
        json.dumps(conversion_metadata, indent=2) + "\n", encoding="utf-8"
    )
    transition(run, "converted", {"output": str(output)})


if __name__ == "__main__":
    typer.run(main)
