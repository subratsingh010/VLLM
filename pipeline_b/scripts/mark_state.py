from __future__ import annotations

import json
from typing import Annotated

import typer

from pipeline_b.scripts.common import ensure_prepared
from pipeline_b.scripts.state import transition


def main(
    variant: Annotated[str, typer.Option()],
    run_id: Annotated[str, typer.Option()],
    target: Annotated[str, typer.Option()],
) -> None:
    if target not in {"serving_started", "serving_stopped", "benchmarked", "analyzed"}:
        raise ValueError(
            "this command may mark serving_started, serving_stopped, benchmarked, or analyzed"
        )
    run = ensure_prepared(variant, run_id)
    typer.echo(json.dumps(transition(run, target), indent=2))


if __name__ == "__main__":
    typer.run(main)
