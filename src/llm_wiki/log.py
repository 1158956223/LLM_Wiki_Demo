from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Mapping


def append_log(path: Path, action: str, fields: Mapping[str, object]) -> None:
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [f"- {timestamp} {action}"]
    for key, value in fields.items():
        lines.append(f"  - {key}: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
