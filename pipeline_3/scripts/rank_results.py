from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Annotated, Any

import typer


def load_runs(sweep_dir: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for path in sorted(sweep_dir.glob("**/run=*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        value["_source"] = str(path)
        runs.append(value)
    if not runs:
        raise ValueError("no official vLLM sweep run JSON files found")
    return runs


def rank(tuning_run: Path) -> list[dict[str, Any]]:
    objective = json.loads((tuning_run / "objective.json").read_text(encoding="utf-8"))
    constraints = objective["constraints"]
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for run in load_runs(tuning_run / "official_sweep" / "tuning"):
        key = (int(run["max_num_seqs"]), int(run["max_num_batched_tokens"]))
        grouped[key].append(run)
    rows: list[dict[str, Any]] = []
    for (sequences, batched), runs in grouped.items():
        ttft = mean(float(run["p95_ttft_ms"]) for run in runs)
        e2el = mean(float(run["p95_e2el_ms"]) for run in runs)
        failures = sum(int(run["failed"]) for run in runs)
        throughput = mean(float(run["output_throughput"]) for run in runs)
        eligible = (
            ttft <= float(constraints["p95_ttft_ms_max"])
            and e2el <= float(constraints["p95_e2el_ms_max"])
            and failures <= int(constraints["failed_max"])
        )
        rows.append(
            {
                "max_num_seqs": sequences,
                "max_num_batched_tokens": batched,
                "runs": len(runs),
                "mean_p95_ttft_ms": ttft,
                "mean_p95_e2el_ms": e2el,
                "failed": failures,
                "mean_output_throughput": throughput,
                "eligible": eligible,
            }
        )
    rows.sort(key=lambda row: (not row["eligible"], -row["mean_output_throughput"]))
    return rows


def write_outputs(tuning_run: Path, rows: list[dict[str, Any]]) -> None:
    output = tuning_run / "analysis"
    output.mkdir(exist_ok=True)
    with (output / "ranking.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    winner = next((row for row in rows if row["eligible"]), None)
    result = {
        "winner": winner,
        "candidate_count": len(rows),
        "source": "official vllm bench sweep serve saved JSON",
        "requires_three_run_confirmation": winner is not None,
        "requires_full_matrix_validation": winner is not None,
    }
    (output / "winner.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    report = [
        "# Pipeline 3 tuning report",
        "",
        "This ranking uses only saved official vLLM sweep outputs.",
        "",
        f"Eligible winner: `{winner}`" if winner else "No candidate satisfied every constraint.",
        "",
        "A winner is provisional until it passes three repeated runs and the full "
        "Pipeline A matrix.",
    ]
    (output / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def main(tuning_run: Annotated[Path, typer.Option(exists=True, file_okay=False)]) -> None:
    rows = rank(tuning_run)
    write_outputs(tuning_run, rows)
    typer.echo(tuning_run / "analysis" / "winner.json")


if __name__ == "__main__":
    typer.run(main)
