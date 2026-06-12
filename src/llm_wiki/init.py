from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .config import write_default_config
from .log import append_log
from .paths import ProjectPaths
from .state import write_initial_state
from .templates import (
    INDEX_MARKER,
    OVERVIEW_MARKER,
    PURPOSE_MARKER,
    SCHEMA_MARKER,
    index_template,
    overview_template,
    purpose_template,
    schema_template,
)


@dataclass
class InitResult:
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def initialize_project(
    root: str | Path,
    *,
    name: str,
    description: str | None,
    use_llm: bool,
    force: bool,
) -> InitResult:
    paths = ProjectPaths(Path(root))
    result = InitResult()

    _create_directories(paths, result)
    _write_template(paths.purpose, purpose_template(name, description), PURPOSE_MARKER, force, result)
    _write_template(paths.schema, schema_template(name), SCHEMA_MARKER, force, result)
    _write_template(paths.wiki_index, index_template(name), INDEX_MARKER, force, result)
    _write_template(paths.wiki_overview, overview_template(name, description), OVERVIEW_MARKER, force, result)
    _write_generated_file(paths.config, write_default_config, force=False, result=result)
    _write_generated_file(paths.state, write_initial_state, force=False, result=result)
    _touch_file(paths.search_index, result)

    append_log(
        paths.wiki_log,
        "init",
        {
            "name": name,
            "llm": "disabled" if not use_llm else "not_implemented",
            "status": "completed",
        },
    )
    return result


def _create_directories(paths: ProjectPaths, result: InitResult) -> None:
    directories = [
        paths.raw_sources_dir,
        paths.wiki_dir / "sources",
        paths.wiki_dir / "concepts",
        paths.wiki_dir / "entities",
        paths.wiki_dir / "synthesis",
        paths.wiki_dir / "queries",
        paths.proposals_dir / "pending",
        paths.proposals_dir / "applied",
        paths.proposals_dir / "rejected",
        paths.tool_dir,
    ]
    for directory in directories:
        if directory.exists():
            result.skipped.append(_display_path(paths.root, directory))
        else:
            directory.mkdir(parents=True)
            result.created.append(_display_path(paths.root, directory))


def _write_template(path: Path, content: str, marker: str, force: bool, result: InitResult) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        result.created.append(_display_path(path.parent.parent if path.parent.name == "wiki" else path.parent, path))
        return

    existing = path.read_text(encoding="utf-8")
    if force and marker in existing:
        path.write_text(content, encoding="utf-8")
        result.created.append(str(path))
        return

    result.skipped.append(str(path))
    if marker not in existing:
        result.warnings.append(f"skip non-template file: {path}")


def _write_generated_file(path: Path, writer, *, force: bool, result: InitResult) -> None:
    if path.exists() and not force:
        result.skipped.append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    writer(path)
    result.created.append(str(path))


def _touch_file(path: Path, result: InitResult) -> None:
    if path.exists():
        result.skipped.append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    result.created.append(str(path))


def _display_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)
