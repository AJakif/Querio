#!/usr/bin/env python3
"""Claude Code status line renderer.

Reads JSON from stdin and prints a concise, single-line status string.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def nested_get(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return value if value is not None else default


def parse_input() -> dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_status_line(payload: dict[str, Any]) -> str:
    project_dir = nested_get(payload, ["workspace", "project_dir"], "") or nested_get(
        payload, ["cwd"], ""
    )
    project_name = Path(project_dir).name if project_dir else "unknown-project"

    model = nested_get(payload, ["model", "display_name"], "") or nested_get(
        payload, ["model", "id"], "unknown-model"
    )

    total_cost = nested_get(payload, ["cost", "total_cost_usd"])
    added = int(nested_get(payload, ["cost", "total_lines_added"], 0) or 0)
    removed = int(nested_get(payload, ["cost", "total_lines_removed"], 0) or 0)

    parts = [project_name, str(model)]
    if isinstance(total_cost, (int, float)):
        parts.append(f"${total_cost:.4f}")
    if added or removed:
        parts.append(f"+{added}/-{removed}")
    return " | ".join(parts)


if __name__ == "__main__":
    data = parse_input()
    print(build_status_line(data))
