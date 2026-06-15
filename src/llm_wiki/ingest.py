from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from .errors import DuplicateSourceError, ProjectNotInitializedError, UnsafePathError
from .log import append_log
from .paths import ProjectPaths
from .state import load_state, write_state


SummaryGenerator = Callable[[str, str], str]
NameConflictConfirmFunc = Callable[[Path, Path], bool]


@dataclass(frozen=True)
class IngestResult:
    source_path: str
    wiki_page: str
    sha256: str


def ingest_source(
    root: str | Path,
    source: str | Path,
    *,
    summary_generator: SummaryGenerator | None = None,
    confirm_name_conflict: NameConflictConfirmFunc | None = None,
) -> IngestResult:
    paths = ProjectPaths(Path(root))
    _ensure_initialized(paths)
    source_path = _import_external_source(paths, source, confirm_name_conflict=confirm_name_conflict)
    source_rel = source_path.relative_to(paths.root).as_posix()
    source_text = source_path.read_text(encoding="utf-8")
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    wiki_page = paths.wiki_dir / "sources" / source_path.name
    wiki_rel = wiki_page.relative_to(paths.root).as_posix()
    title = _title_from_source(source_path, source_text)
    summary = summary_generator(source_text, source_rel) if summary_generator else _default_summary(source_text)

    wiki_page.parent.mkdir(parents=True, exist_ok=True)
    wiki_page.write_text(_source_page(title, source_rel, summary), encoding="utf-8")

    state = load_state(paths.state)
    state.setdefault("sources", {})[source_rel] = {
        "sha256": digest,
        "ingested_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "wiki_page": wiki_rel,
    }
    write_state(paths.state, state)
    _update_index(paths.wiki_index, title, source_path.name)
    append_log(
        paths.wiki_log,
        "ingest",
        {
            "source": source_rel,
            "wiki_page": wiki_rel,
            "sha256": digest,
        },
    )
    return IngestResult(source_path=source_rel, wiki_page=wiki_rel, sha256=digest)


def _ensure_initialized(paths: ProjectPaths) -> None:
    required = [paths.purpose, paths.schema, paths.wiki_index, paths.state]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise ProjectNotInitializedError(f"project is not initialized: missing {missing[0]}")


def _import_external_source(
    paths: ProjectPaths,
    source: str | Path,
    *,
    confirm_name_conflict: NameConflictConfirmFunc | None,
) -> Path:
    source_path = Path(source).expanduser().resolve()
    try:
        source_path.relative_to(paths.root)
    except ValueError:
        pass
    else:
        raise UnsafePathError(f"source must be outside the project root: {source}")
    if source_path.suffix.lower() != ".md":
        raise ValueError(f"source must be a Markdown file: {source}")
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    _ensure_not_duplicate(paths, digest)
    target_path = paths.raw_sources_dir / source_path.name
    if target_path.exists():
        target_digest = hashlib.sha256(target_path.read_bytes()).hexdigest()
        if target_digest == digest:
            raise DuplicateSourceError(f"source has already been ingested: {target_path}")
        if confirm_name_conflict is None or not confirm_name_conflict(target_path, source_path):
            raise FileExistsError(f"raw source already exists with different content: {target_path}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    return target_path


def _ensure_not_duplicate(paths: ProjectPaths, digest: str) -> None:
    state = load_state(paths.state)
    for source_rel, entry in state.get("sources", {}).items():
        if entry.get("sha256") == digest:
            raise DuplicateSourceError(f"source has already been ingested: {source_rel}")


def _title_from_source(source_path: Path, source_text: str) -> str:
    for line in source_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or source_path.stem
    return source_path.stem.replace("-", " ").replace("_", " ").title()


def _default_summary(source_text: str) -> str:
    text = " ".join(line.strip() for line in source_text.splitlines() if line.strip())
    return text[:500]


def _source_page(title: str, source_rel: str, summary: str) -> str:
    today = date.today().isoformat()
    return f"""---
type: source
title: {title}
created_at: {today}
updated_at: {today}
sources:
  - {source_rel}
tags: []
status: active
---

# {title}

## Summary

{summary}

## Key Points

## Concepts

## Entities

## Quotes

## Sources

- `{source_rel}`
"""


def _update_index(index_path: Path, title: str, source_filename: str) -> None:
    text = index_path.read_text(encoding="utf-8") if index_path.exists() else "# Wiki Index\n\n## 来源\n"
    entry = f"- [{title}](sources/{source_filename})"
    if entry in text:
        return
    marker = _find_source_marker(text)
    if marker not in text:
        text = text.rstrip() + f"\n\n{marker}\n"
    lines = text.splitlines()
    insert_at = len(lines)
    marker_index = lines.index(marker)
    for index in range(marker_index + 1, len(lines)):
        if lines[index].startswith("## "):
            insert_at = index
            break
    lines.insert(insert_at, entry)
    index_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _find_source_marker(text: str) -> str:
    for marker in ("## 来源", "## Sources"):
        if marker in text:
            return marker
    return "## 来源"
