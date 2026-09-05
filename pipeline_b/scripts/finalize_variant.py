from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from benchmark.capacity_analysis import load_points
from pipeline_b.scripts.common import ensure_prepared, variant_config
from pipeline_b.scripts.state import require_state, transition
from pipeline_b.scripts.validate_benchmark import validate_benchmark


def finalize(variant: str, run_id: str) -> Path:
    run = ensure_prepared(variant, run_id)
    require_state(run, {"analyzed"})
    benchmark = validate_benchmark(run)
    points = load_points(run / "benchmark")
    if len(points) != 12:
        raise ValueError(f"expected 12 complete official benchmark points, found {len(points)}")
    for required in ("capacity.csv", "operating_envelope.json"):
        if not (run / "analysis" / required).is_file():
            raise ValueError(f"analysis artifact is missing: {required}")
    inventory_path = run / "metadata" / "artifact_inventory.json"
    if not inventory_path.is_file():
        raise ValueError("verified artifact inventory is missing")
    metadata: dict[str, Any] = json.loads(inventory_path.read_text(encoding="utf-8"))
    metadata["variant_config"] = variant_config(variant)
    (run / "metadata" / "model.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    transition(run, "complete", benchmark)
    status_path = run / "RUN_STATUS.json"
    return status_path


def main(variant: Annotated[str, typer.Option()], run_id: Annotated[str, typer.Option()]) -> None:
    typer.echo(finalize(variant, run_id))


if __name__ == "__main__":
    typer.run(main)
