from __future__ import annotations

import json
from pathlib import Path
from typing import Any


INITIAL_STATE: dict[str, Any] = {"version": 1, "sources": {}, "last_query": None}


def write_initial_state(path: Path) -> None:
    path.write_text(json.dumps(INITIAL_STATE, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return dict(INITIAL_STATE)
    return json.loads(path.read_text(encoding="utf-8"))
