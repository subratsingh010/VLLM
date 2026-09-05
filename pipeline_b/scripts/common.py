from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PIPELINE = ROOT / "pipeline_b"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def read_json(path: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return value


def base_config() -> dict[str, Any]:
    return read_json(PIPELINE / "config" / "base_model.json")


def variant_config(name: str) -> dict[str, Any]:
    variants = read_json(PIPELINE / "config" / "variants.json")["variants"]
    if name not in variants:
        raise ValueError(f"unsupported variant {name!r}; choose one of: {', '.join(variants)}")
    result: dict[str, Any] = variants[name]
    return result


def validate_run_id(run_id: str) -> None:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run-id must contain only letters, numbers, dot, underscore, or hyphen")


def run_dir(variant: str, run_id: str) -> Path:
    validate_run_id(run_id)
    return PIPELINE / "results" / variant / run_id


def converted_model_dir(variant: str, run_id: str) -> Path:
    validate_run_id(run_id)
    return PIPELINE / "converted_models" / variant / run_id


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_sha256(path: Path) -> str:
    value = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def model_path(variant: str, run_id: str) -> Path:
    config = variant_config(variant)
    if config["conversion"] == "mlx_lm":
        return converted_model_dir(variant, run_id)
    return ROOT / str(config["source"])


def ensure_prepared(variant: str, run_id: str) -> Path:
    destination = run_dir(variant, run_id)
    if not (destination / "RUN_STATUS.json").is_file():
        raise ValueError(f"run is not prepared: {destination}")
    return destination
