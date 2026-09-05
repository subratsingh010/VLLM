from __future__ import annotations

import json
from pathlib import Path

from benchmark.schemas.workload import BenchmarkProtocol, PromptRecord


def load_protocol(path: Path) -> BenchmarkProtocol:
    return BenchmarkProtocol.model_validate_json(path.read_text(encoding="utf-8"))


def load_prompts(paths: list[Path]) -> list[PromptRecord]:
    records: list[PromptRecord] = []
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                try:
                    records.append(PromptRecord.model_validate(json.loads(line)))
                except Exception as exc:
                    raise ValueError(f"invalid prompt at {path}:{line_number}") from exc
    ids = [record.id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("prompt IDs must be unique")
    return records


def expand_prompts(records: list[PromptRecord], expansion_path: Path) -> list[PromptRecord]:
    expansion: dict[str, dict[str, str | int]] = json.loads(
        expansion_path.read_text(encoding="utf-8")
    )
    output: list[PromptRecord] = []
    for record in records:
        rule = expansion.get(record.id)
        if rule is None:
            output.append(record)
            continue
        messages = [message.copy() for message in record.messages]
        messages[-1]["content"] += str(rule["repeat_text"]) * int(rule["repeat_count"])
        output.append(record.model_copy(update={"messages": messages}))
    return output
