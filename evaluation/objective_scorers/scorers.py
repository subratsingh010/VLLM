from __future__ import annotations

import json
import re
from typing import Any, cast


def score(kind: str, response: str, expected: Any) -> bool:
    stripped = response.strip()
    if kind == "exact":
        return stripped == cast(object, expected)
    if kind == "exact_normalized":
        return stripped.casefold() == str(expected).strip().casefold()
    if kind == "numeric":
        try:
            return float(stripped) == float(expected)
        except ValueError:
            return False
    if kind == "integer_set":
        return sorted(map(int, re.findall(r"-?\d+", stripped))) == sorted(expected)
    if kind == "json_exact":
        try:
            parsed: object = json.loads(stripped)
            return parsed == cast(object, expected)
        except json.JSONDecodeError:
            return False
    if kind == "contains_all":
        folded = stripped.casefold()
        return all(str(value).casefold() in folded for value in expected)
    raise ValueError(f"unsupported objective scorer: {kind}")
