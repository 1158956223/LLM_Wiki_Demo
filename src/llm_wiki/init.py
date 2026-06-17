from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

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


@dataclass(frozen=True)
class InitContent:
    purpose: str


def initialize_project(
    root: str | Path,
    *,
    name: str,
    description: str | None,
    init_content_generator: Callable[[str, str], InitContent] | None = None,
) -> InitResult:
    paths = ProjectPaths(Path(root))
    result = InitResult()
    description_text = description or "维护一个本地优先、Markdown 优先的长期知识库。"
    init_content, content_source = _generate_init_content(name, description_text, init_content_generator, result)

    _create_directories(paths, result)
    _write_template(paths.purpose, init_content.purpose, PURPOSE_MARKER, result)
    _write_template(paths.schema, schema_template(), SCHEMA_MARKER, result)
    _write_template(paths.wiki_index, index_template(), INDEX_MARKER, result)
    _write_template(paths.wiki_overview, overview_template(), OVERVIEW_MARKER, result)
    _write_generated_file(paths.config, write_default_config, force=False, result=result)
    _write_generated_file(paths.state, write_initial_state, force=False, result=result)
    _touch_file(paths.search_index, result)

    append_log(
        paths.wiki_log,
        "init",
        {
            "name": name,
            "llm": content_source,
            "status": "completed",
        },
    )
    return result


def _generate_init_content(
    name: str,
    description: str,
    generator: Callable[[str, str], InitContent] | None,
    result: InitResult,
) -> tuple[InitContent, str]:
    if generator is not None:
        try:
            return generator(name, description), "deepseek"
        except Exception as exc:
            result.warnings.append(f"DeepSeek 初始化内容生成失败，已使用默认模板: {exc}")
    return (
        InitContent(
            purpose=purpose_template(name, description),
        ),
        "default_template",
    )


def _create_directories(paths: ProjectPaths, result: InitResult) -> None:
    directories = [
        paths.raw_sources_dir,
        paths.wiki_dir / "sources",
        paths.wiki_dir / "concepts",
        paths.wiki_dir / "entities",
        paths.wiki_dir / "synthesis",
        paths.wiki_dir / "queries",
        paths.tool_dir,
    ]
    for directory in directories:
        if directory.exists():
            result.skipped.append(_display_path(paths.root, directory))
        else:
            directory.mkdir(parents=True)
            result.created.append(_display_path(paths.root, directory))


def _write_template(path: Path, content: str, marker: str, result: InitResult) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        result.created.append(_display_path(path.parent.parent if path.parent.name == "wiki" else path.parent, path))
        return

    existing = path.read_text(encoding="utf-8")
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
