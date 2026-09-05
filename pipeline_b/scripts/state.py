from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TRANSITIONS: dict[str, set[str]] = {
    "configured": {"conversion_planned", "artifacts_verified"},
    "conversion_planned": {"converted"},
    "converted": {"artifacts_verified"},
    "artifacts_verified": {"serving_started"},
    "serving_started": {"serving_stopped", "benchmarked"},
    "serving_stopped": {"serving_started", "benchmarked"},
    "benchmarked": {"analyzed"},
    "analyzed": {"complete"},
    "complete": set(),
}


def load_status(run: Path) -> dict[str, Any]:
    path = run / "RUN_STATUS.json"
    status: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if status.get("status") not in TRANSITIONS:
        raise ValueError(f"unknown run state: {status.get('status')!r}")
    return status


def require_state(run: Path, allowed: set[str]) -> dict[str, Any]:
    status = load_status(run)
    if status["status"] not in allowed:
        raise ValueError(
            f"run state is {status['status']!r}; expected one of: {', '.join(sorted(allowed))}"
        )
    return status


def transition(run: Path, target: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    status = load_status(run)
    current = str(status["status"])
    if target not in TRANSITIONS[current]:
        raise ValueError(f"invalid run-state transition: {current} -> {target}")
    timestamp = datetime.now(UTC).isoformat()
    history = status.setdefault("history", [])
    history.append({"from": current, "to": target, "at": timestamp, "details": details or {}})
    status["status"] = target
    status["updated_at"] = timestamp
    _atomic_write(run / "RUN_STATUS.json", status)
    return status


def _atomic_write(path: Path, value: dict[str, Any]) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
