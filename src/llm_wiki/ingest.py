from __future__ import annotations

import hashlib
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

from .config import IngestConfig, load_config
from .errors import DuplicateSourceError, ProjectNotInitializedError, UnsafePathError
from .log import append_log
from .paths import ProjectPaths
from .state import load_state, write_state


SummaryGenerator = Callable[["IngestSummaryRequest"], str]
ExtractionGenerator = Callable[["IngestExtractionRequest"], "IngestExtraction"]
OverviewGenerator = Callable[["IngestOverviewRequest"], str]
NameConflictConfirmFunc = Callable[[Path, Path], bool]
ProgressReporter = Callable[[str], None]


@dataclass(frozen=True)
class IngestSummaryRequest:
    source_text: str
    source_path: str
    document_kind: str
    target_summary_limit: int
    chunks: list[str]


@dataclass(frozen=True)
class IngestExtractionRequest:
    source_text: str
    source_path: str
    summary: str
    chunks: list[str]


@dataclass(frozen=True)
class IngestOverviewRequest:
    source_summaries: list[str]
    concepts: list[str]
    entities: list[str]


@dataclass(frozen=True)
class ExtractedConcept:
    title: str
    summary: str
    related: list[str]


@dataclass(frozen=True)
class ExtractedEntity:
    title: str
    category: str
    summary: str
    related: list[str]


@dataclass(frozen=True)
class IngestExtraction:
    concepts: list[ExtractedConcept]
    entities: list[ExtractedEntity]


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
    extraction_generator: ExtractionGenerator | None = None,
    overview_generator: OverviewGenerator | None = None,
    confirm_name_conflict: NameConflictConfirmFunc | None = None,
    progress: ProgressReporter | None = None,
) -> IngestResult:
    paths = ProjectPaths(Path(root))
    _ensure_initialized(paths)
    _report(progress, "[1/7] 校验来源文件")
    incoming_path, target_path, digest = _resolve_external_source(
        paths, source, confirm_name_conflict=confirm_name_conflict
    )
    source_rel = target_path.relative_to(paths.root).as_posix()
    source_text = incoming_path.read_text(encoding="utf-8")
    wiki_page = paths.wiki_dir / "sources" / target_path.name
    wiki_rel = wiki_page.relative_to(paths.root).as_posix()
    title = _title_from_source(incoming_path, source_text)
    config = load_config(paths.config).ingest
    request = _build_summary_request(source_text, source_rel, config)
    generator = summary_generator or _default_summary_generator()
    _report(progress, "[2/7] 生成 source 摘要")
    summary = generator(request)
    extractor = extraction_generator or _default_extraction_generator()
    _report(progress, "[3/7] 提取概念 / 实体 / 关联")
    extraction = extractor(
        IngestExtractionRequest(
            source_text=source_text,
            source_path=source_rel,
            summary=summary,
            chunks=request.chunks,
        )
    )
    overview = (overview_generator or _default_overview_generator())(
        IngestOverviewRequest(
            source_summaries=[
                *_source_summaries(paths, exclude=wiki_page),
                summary,
            ],
            concepts=_existing_titles(paths.wiki_dir / "concepts") + [concept.title for concept in extraction.concepts],
            entities=_existing_titles(paths.wiki_dir / "entities") + [entity.title for entity in extraction.entities],
        )
    )

    _report(progress, "[4/7] 写入 raw 和 wiki 页面")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(incoming_path, target_path)
    wiki_page.parent.mkdir(parents=True, exist_ok=True)
    wiki_page.write_text(_source_page(title, source_rel, summary, extraction), encoding="utf-8")
    concept_pages = _write_concept_pages(paths, extraction.concepts, source_rel)
    entity_pages = _write_entity_pages(paths, extraction.entities, source_rel)

    state = load_state(paths.state)
    state.setdefault("sources", {})[source_rel] = {
        "sha256": digest,
        "ingested_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "wiki_page": wiki_rel,
        "concepts": [page.relative_to(paths.root).as_posix() for page in concept_pages],
        "entities": [page.relative_to(paths.root).as_posix() for page in entity_pages],
    }
    write_state(paths.state, state)
    _report(progress, "[5/7] 重建 wiki/index.md")
    _rebuild_wiki_index(paths)
    _report(progress, "[6/7] 更新 wiki/overview.md")
    _rebuild_overview(paths, overview)
    _report(progress, "[7/7] 刷新 search.sqlite")
    _rebuild_search_index(paths)
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


def _report(progress: ProgressReporter | None, message: str) -> None:
    if progress is not None:
        progress(message)


def _ensure_initialized(paths: ProjectPaths) -> None:
    required = [paths.purpose, paths.schema, paths.wiki_index, paths.state]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise ProjectNotInitializedError(f"project is not initialized: missing {missing[0]}")


def _resolve_external_source(
    paths: ProjectPaths,
    source: str | Path,
    *,
    confirm_name_conflict: NameConflictConfirmFunc | None,
) -> tuple[Path, Path, str]:
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
    return source_path, target_path, digest


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


def _build_summary_request(source_text: str, source_rel: str, config: IngestConfig) -> IngestSummaryRequest:
    char_count = len(source_text)
    if char_count <= config.short_doc_limit:
        return IngestSummaryRequest(
            source_text=source_text,
            source_path=source_rel,
            document_kind="short",
            target_summary_limit=config.short_summary_limit,
            chunks=[source_text],
        )
    if char_count <= config.medium_doc_limit:
        return IngestSummaryRequest(
            source_text=source_text,
            source_path=source_rel,
            document_kind="medium",
            target_summary_limit=config.medium_summary_limit,
            chunks=[source_text],
        )
    return IngestSummaryRequest(
        source_text=source_text,
        source_path=source_rel,
        document_kind="long",
        target_summary_limit=config.long_summary_limit,
        chunks=_chunk_markdown(source_text, config),
    )


def _chunk_markdown(source_text: str, config: IngestConfig) -> list[str]:
    sections = _split_markdown_sections(source_text)
    chunks: list[str] = []
    current = ""
    for section in sections:
        if not current:
            current = section
            continue
        proposed = f"{current.rstrip()}\n\n{section.lstrip()}"
        if len(current) >= config.chunk_min_chars and len(proposed) > config.chunk_max_chars:
            chunks.append(current.rstrip() + "\n")
            current = section
        else:
            current = proposed
    if current:
        chunks.append(current.rstrip() + "\n")
    return chunks or [source_text]


def _split_markdown_sections(source_text: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    for line in source_text.splitlines(keepends=True):
        if line.startswith("## ") and current:
            sections.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("".join(current))
    return sections


def _default_summary_generator() -> SummaryGenerator:
    from .deepseek import generate_ingest_summary_with_deepseek

    return generate_ingest_summary_with_deepseek


def _default_extraction_generator() -> ExtractionGenerator:
    from .deepseek import generate_ingest_extraction_with_deepseek

    return generate_ingest_extraction_with_deepseek


def _default_overview_generator() -> OverviewGenerator:
    from .deepseek import generate_ingest_overview_with_deepseek

    return generate_ingest_overview_with_deepseek


def _source_page(title: str, source_rel: str, summary: str, extraction: IngestExtraction) -> str:
    today = date.today().isoformat()
    concept_lines = _link_lines([concept.title for concept in extraction.concepts])
    entity_lines = _link_lines([entity.title for entity in extraction.entities])
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
{concept_lines}

## Entities
{entity_lines}

## Quotes

## Sources

- `{source_rel}`
"""


def _write_concept_pages(paths: ProjectPaths, concepts: list[ExtractedConcept], source_rel: str) -> list[Path]:
    (paths.wiki_dir / "concepts").mkdir(parents=True, exist_ok=True)
    return [
        _upsert_knowledge_page(paths, "concepts", "concept", concept.title, concept.summary, concept.related, source_rel)
        for concept in concepts
    ]


def _write_entity_pages(paths: ProjectPaths, entities: list[ExtractedEntity], source_rel: str) -> list[Path]:
    (paths.wiki_dir / "entities").mkdir(parents=True, exist_ok=True)
    pages: list[Path] = []
    for entity in entities:
        pages.append(
            _upsert_knowledge_page(
                paths,
                "entities",
                "entity",
                entity.title,
                entity.summary,
                entity.related,
                source_rel,
                extra_frontmatter=f"category: {entity.category}\n",
            )
        )
    return pages


def _upsert_knowledge_page(
    paths: ProjectPaths,
    directory: str,
    page_type: str,
    title: str,
    summary: str,
    related: list[str],
    source_rel: str,
    *,
    extra_frontmatter: str = "",
) -> Path:
    page = paths.wiki_dir / directory / f"{_slug(title)}.md"
    today = date.today().isoformat()
    related_lines = _link_lines(related)
    addition = f"""## 来自 {source_rel} 的补充

{summary}

### 关联
{related_lines}

### 来源

- `{source_rel}`
"""
    if page.exists():
        text = page.read_text(encoding="utf-8")
        if f"- `{source_rel}`" in text:
            return page
        page.write_text(text.rstrip() + "\n\n" + addition, encoding="utf-8")
        return page

    page.write_text(
        f"""---
type: {page_type}
title: {title}
created_at: {today}
updated_at: {today}
sources:
  - {source_rel}
tags: []
status: active
{extra_frontmatter}---

# {title}

## 概述

{summary}

## 关联
{related_lines}

## 来源

- `{source_rel}`
""",
        encoding="utf-8",
    )
    return page


def _link_lines(titles: list[str]) -> str:
    if not titles:
        return "\n"
    return "".join(f"\n- [[{_slug(title)}]]" for title in titles) + "\n"


def _slug(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", title.strip())
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = cleaned.strip(".-")
    return cleaned or "untitled"


def _rebuild_wiki_index(paths: ProjectPaths) -> None:
    sections = [
        ("实体", paths.wiki_dir / "entities", "entities"),
        ("概念", paths.wiki_dir / "concepts", "concepts"),
        ("来源", paths.wiki_dir / "sources", "sources"),
        ("问题", paths.wiki_dir / "queries", "queries"),
        ("综合", paths.wiki_dir / "synthesis", "synthesis"),
    ]
    lines = ["<!-- llm-wiki:template=index:v1 -->", "# Wiki 索引", ""]
    for heading, directory, rel_dir in sections:
        lines.append(f"## {heading}")
        lines.extend(_index_entries(directory, rel_dir))
        lines.append("")
    paths.wiki_index.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _rebuild_overview(paths: ProjectPaths, overview: str) -> None:
    sources = _index_entries(paths.wiki_dir / "sources", "sources")
    concepts = _index_entries(paths.wiki_dir / "concepts", "concepts")
    entities = _index_entries(paths.wiki_dir / "entities", "entities")
    today = date.today().isoformat()
    paths.wiki_overview.write_text(
        f"""---
type: overview
title: 项目概览
tags: []
related: []
created_at: {today}
updated_at: {today}
---

<!-- llm-wiki:template=overview:v1 -->

# 项目概览

## 概览

{overview.strip()}

## 当前规模

- 来源资料：{len(sources)}
- 概念页面：{len(concepts)}
- 实体页面：{len(entities)}
""",
        encoding="utf-8",
    )


def _index_entries(directory: Path, rel_dir: str) -> list[str]:
    if not directory.exists():
        return []
    entries: list[str] = []
    for page in sorted(directory.glob("*.md"), key=lambda item: item.name.lower()):
        title = _title_from_wiki_page(page)
        entries.append(f"- [{title}]({rel_dir}/{page.name})")
    return entries


def _title_from_wiki_page(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^title:\s*(.+)$", text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip().strip('"')
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ")


def _existing_titles(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    return [_title_from_wiki_page(page) for page in sorted(directory.glob("*.md"), key=lambda item: item.name.lower())]


def _source_summaries(paths: ProjectPaths, *, exclude: Path | None = None) -> list[str]:
    directory = paths.wiki_dir / "sources"
    if not directory.exists():
        return []
    summaries: list[str] = []
    excluded = exclude.resolve() if exclude is not None else None
    for page in sorted(directory.glob("*.md"), key=lambda item: item.name.lower()):
        if excluded is not None and page.resolve() == excluded:
            continue
        summary = _source_summary(page.read_text(encoding="utf-8"))
        if summary:
            summaries.append(summary)
    return summaries


def _source_summary(text: str) -> str:
    match = re.search(r"^## Summary\s*\n(?P<body>.*?)(?=^## |\Z)", text, flags=re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    return match.group("body").strip()


def _rebuild_search_index(paths: ProjectPaths) -> None:
    paths.search_index.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(paths.search_index) as connection:
        connection.execute("DROP TABLE IF EXISTS pages_fts")
        connection.execute("DROP TABLE IF EXISTS pages")
        connection.execute(
            "CREATE TABLE pages (path TEXT PRIMARY KEY, title TEXT NOT NULL, type TEXT NOT NULL, content TEXT NOT NULL)"
        )
        _create_fts_table(connection)
        for page in sorted(paths.wiki_dir.rglob("*.md")):
            rel_path = page.relative_to(paths.root).as_posix()
            text = page.read_text(encoding="utf-8")
            title = _title_from_wiki_page(page)
            page_type = _frontmatter_value(text, "type") or "unknown"
            row = (rel_path, title, page_type, text)
            connection.execute("INSERT INTO pages(path, title, type, content) VALUES (?, ?, ?, ?)", row)
            connection.execute("INSERT INTO pages_fts(path, title, type, content) VALUES (?, ?, ?, ?)", row)


def _create_fts_table(connection: sqlite3.Connection) -> None:
    try:
        connection.execute(
            "CREATE VIRTUAL TABLE pages_fts USING fts5(path UNINDEXED, title, type UNINDEXED, content, tokenize='trigram')"
        )
    except sqlite3.OperationalError:
        connection.execute(
            "CREATE VIRTUAL TABLE pages_fts USING fts5(path UNINDEXED, title, type UNINDEXED, content)"
        )


def _frontmatter_value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, flags=re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"')
