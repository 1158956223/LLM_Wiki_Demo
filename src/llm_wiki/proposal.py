from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from .errors import DeepSeekUnavailableError, InvalidProposalError, ProjectNotInitializedError
from .ingest import _rebuild_wiki_index
from .log import append_log
from .page_merge import PageBodyMergeGenerator, merge_page_content
from .paths import ProjectPaths
from .search import rebuild_search_index
from .state import load_state, write_state


ProposalPlanGenerator = Callable[["ProposalRequest"], list["ProposalWrite"]]


# 候选页面，表示上一次回答参考的页面
@dataclass(frozen=True)
class CandidatePage:
    path: str
    title: str
    content: str


@dataclass(frozen=True)
class ProposalRequest:
    instruction: str
    question: str
    answer: str
    context_pages: list[str]
    citations: list[str]
    candidate_pages: list[CandidatePage]
    purpose: str
    schema: str


@dataclass(frozen=True)
class ProposalWrite:
    path: str
    page_type: str
    title: str
    content: str


@dataclass(frozen=True)
class ProposalResult:
    record_path: Path
    written_pages: list[str]


def propose_change(
    root: str | Path,
    instruction: str,
    *,
    plan_generator: ProposalPlanGenerator | None = None,
    body_merge_generator: PageBodyMergeGenerator | None = None,
) -> ProposalResult:
    paths = ProjectPaths(Path(root))
    _ensure_initialized(paths)
    state = load_state(paths.state)
    last_query = state.get("last_query")
    if not isinstance(last_query, dict):
        raise InvalidProposalError("no last_query found; run query before add")

    request = ProposalRequest(
        instruction=instruction,
        question=str(last_query.get("question", "")),
        answer=str(last_query.get("answer", "")),
        context_pages=[str(value) for value in last_query.get("context_pages", [])],
        citations=[str(value) for value in last_query.get("citations", [])],
        candidate_pages=_candidate_pages(paths, [str(value) for value in last_query.get("context_pages", [])]),
        purpose=paths.purpose.read_text(encoding="utf-8"),
        schema=paths.schema.read_text(encoding="utf-8"),
    )
    generator = plan_generator or _default_plan_generator()
    writes = generator(request)

    record_path = _write_query_record(paths, request)
    written_pages = [_write_page(paths, write, body_merge_generator=body_merge_generator) for write in writes]
    _rebuild_wiki_index(paths)
    rebuild_search_index(paths.root)

    state["last_add"] = {
        "instruction": instruction,
        "record_path": _relative_path(paths, record_path),
        "written_pages": written_pages,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    write_state(paths.state, state)
    append_log(
        paths.wiki_log,
        "add",
        {
            "instruction": instruction,
            "record": _relative_path(paths, record_path),
            "written_pages": written_pages,
        },
    )
    return ProposalResult(record_path=record_path, written_pages=written_pages)


def _ensure_initialized(paths: ProjectPaths) -> None:
    required = [paths.purpose, paths.schema, paths.wiki_index, paths.state]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise ProjectNotInitializedError(f"project is not initialized: missing {missing[0]}")


# 从上一次问答引用过的页面里，挑出可以作为候选的 Wiki 页面
def _candidate_pages(paths: ProjectPaths, context_pages: list[str]) -> list[CandidatePage]:
    candidates: list[CandidatePage] = []
    seen: set[str] = set()

    # 只有这三个目录下的页面可以作为候选页面
    allowed_prefixes = ("wiki/concepts/", "wiki/entities/", "wiki/synthesis/")
    for context_page in context_pages:
        rel = context_page.split("#", 1)[0].strip()
        if not rel.startswith(allowed_prefixes) or rel in seen:
            continue
        path = paths.safe_relative(rel)
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        candidates.append(
            CandidatePage(
                path=rel,
                title=_page_title(text, path),
                content=text[:12000],  # 只取前 12000 字符，防止上下文过长
            )
        )
        seen.add(rel)
    return candidates


def _page_title(text: str, path: Path) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("title:"):
            return stripped.split(":", 1)[1].strip().strip('"')
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return path.stem


def _write_page(
    paths: ProjectPaths,
    write: ProposalWrite,
    *,
    body_merge_generator: PageBodyMergeGenerator | None,
) -> str:
    if write.page_type not in {"concept", "entity", "synthesis"}:
        raise InvalidProposalError(f"unsupported add page type: {write.page_type}")
    expected_dirs = {
        "concept": "concepts",
        "entity": "entities",
        "synthesis": "synthesis",
    }
    path = paths.safe_relative(write.path)
    rel_path = _relative_path(paths, path)
    expected_prefix = f"wiki/{expected_dirs[write.page_type]}/"
    if not rel_path.startswith(expected_prefix) or path.suffix.lower() != ".md":
        raise InvalidProposalError(f"add path does not match page type: {write.path}")

    # 补上元数据
    text = _with_frontmatter(write)
    path.parent.mkdir(parents=True, exist_ok=True)

    # 如果原wiki已经存在，则合并
    if path.exists():
        # add/save 与 ingest 共用页面合并规则，避免同一页面在两条写入路径里出现不同格式。
        merger = body_merge_generator or _default_body_merge_generator()
        text = merge_page_content(path.read_text(encoding="utf-8"), text, body_merge_generator=merger)
    path.write_text(text, encoding="utf-8")
    return rel_path


def _with_frontmatter(write: ProposalWrite) -> str:
    content = write.content.strip()

    # 如果已经有元数据则直接返回
    if content.startswith("---\n"):
        return content.rstrip() + "\n"
    today = datetime.now().astimezone().date().isoformat()
    title = write.title.strip() or Path(write.path).stem
    body = content
    if not body.startswith("# "):
        body = f"# {title}\n\n{body}"
    return f"""---
type: {write.page_type}
title: {title}
created_at: {today}
updated_at: {today}
sources: []
tags: []
status: active
---

{body.rstrip()}
"""


# 写入queries
def _write_query_record(paths: ProjectPaths, request: ProposalRequest) -> Path:
    query_dir = paths.wiki_dir / "queries"
    query_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    filename = _unique_record_path(query_dir, request.question)
    title = request.question.strip() or "Query"
    filename.write_text(
        f"""---
type: query
title: {title}
created_at: {timestamp}
source: last_query
status: written
---

# 用户问题

{request.question.strip()}

# 大模型回答

{request.answer.strip()}
""",
        encoding="utf-8",
    )
    return filename


# 生成唯一query文件名
def _unique_record_path(directory: Path, question: str) -> Path:
    date_prefix = datetime.now().astimezone().date().isoformat()
    slug = _slug(question)[:80] or "query"
    candidate = directory / f"{date_prefix}-{slug}.md"
    index = 2
    while candidate.exists():
        candidate = directory / f"{date_prefix}-{slug}-{index}.md"
        index += 1
    return candidate


def _slug(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]', "", title.strip())
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = cleaned.strip(".-")
    return cleaned or "query"


def _relative_path(paths: ProjectPaths, path: Path) -> str:
    return path.resolve().relative_to(paths.root).as_posix()


def _default_plan_generator() -> ProposalPlanGenerator:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise DeepSeekUnavailableError("DEEPSEEK_API_KEY is not set")
    from .deepseek import generate_proposal_writes_with_deepseek

    return generate_proposal_writes_with_deepseek


def _default_body_merge_generator() -> PageBodyMergeGenerator:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise DeepSeekUnavailableError("DEEPSEEK_API_KEY is not set")
    from .deepseek import merge_page_body_with_deepseek

    return merge_page_body_with_deepseek


def proposal_writes_from_json(content: str) -> list[ProposalWrite]:
    text = content.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
        return [
            ProposalWrite(
                path=str(item["path"]),
                page_type=str(item["page_type"]),
                title=str(item.get("title", "")),
                content=str(item["content"]),
            )
            for item in data.get("writes", [])
        ]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise DeepSeekUnavailableError("DeepSeek returned invalid add writes") from exc
