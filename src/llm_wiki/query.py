from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from .config import SearchConfig, load_config
from .errors import DeepSeekUnavailableError, ProjectNotInitializedError
from .log import append_log
from .paths import ProjectPaths
from .search import SearchResult, search_pages
from .state import load_state, write_state


QueryAnswerGenerator = Callable[["QueryRequest"], str]
QueryAnswerStreamer = Callable[["QueryRequest", Callable[[str], None]], str]


@dataclass(frozen=True)
class QueryContextPage:
    path: str
    title: str
    content: str


@dataclass(frozen=True)
class QueryRequest:
    question: str
    context_pages: list[QueryContextPage]
    purpose: str
    schema: str


@dataclass(frozen=True)
class QueryResult:
    question: str
    answer: str
    context_pages: list[str]
    citations: list[str]


def answer_query(
    root: str | Path,
    question: str,
    *,
    answer_generator: QueryAnswerGenerator | None = None,
    answer_streamer: QueryAnswerStreamer | None = None,
    on_token: Callable[[str], None] | None = None,
) -> QueryResult:
    paths = ProjectPaths(Path(root))
    _ensure_initialized(paths)

    config = load_config(paths.config).search
    hits = search_pages(paths.root, question, top_k=config.top_k)
    if not hits:
        raise ValueError("no wiki context matched the query")

    context_pages = _load_context_pages(paths, hits, config)
    request = QueryRequest(
        question=question,
        context_pages=context_pages,
        purpose=paths.purpose.read_text(encoding="utf-8"),
        schema=paths.schema.read_text(encoding="utf-8"),
    )
    if answer_generator is not None:
        answer = answer_generator(request)
    elif on_token is not None:
        streamer = answer_streamer or _default_answer_streamer()
        answer = streamer(request, on_token)
    else:
        generator = _default_answer_generator()
        answer = generator(request)
    citations = _extract_citations(answer, context_pages)
    result = QueryResult(
        question=question,
        answer=answer,
        context_pages=[page.path for page in context_pages],
        citations=citations,
    )
    _write_last_query(paths, result)
    append_log(
        paths.wiki_log,
        "query",
        {
            "question": question,
            "context_pages": result.context_pages,
            "citations": result.citations,
        },
    )
    return result


def _ensure_initialized(paths: ProjectPaths) -> None:
    required = [paths.purpose, paths.schema, paths.wiki_index, paths.state]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise ProjectNotInitializedError(f"project is not initialized: missing {missing[0]}")


def _load_context_pages(
    paths: ProjectPaths,
    hits: list[SearchResult],
    config: SearchConfig,
) -> list[QueryContextPage]:
    pages: list[QueryContextPage] = []
    remaining = config.total_context_char_limit
    for hit in hits:
        if remaining <= 0:
            break
        page_path = paths.safe_relative(hit.path)
        text = page_path.read_text(encoding="utf-8")
        limit = min(config.page_char_limit, remaining)
        content = text[:limit]
        pages.append(QueryContextPage(path=hit.path, title=hit.title, content=content))
        remaining -= len(content)
    return pages


def _extract_citations(answer: str, context_pages: list[QueryContextPage]) -> list[str]:
    valid_paths = {page.path for page in context_pages}
    citations: list[str] = []
    for match in re.finditer(r"`([^`]+)`", answer):
        citation = match.group(1).strip()
        path = citation.split("#", 1)[0]
        if path in valid_paths and citation not in citations:
            citations.append(citation)
    return citations


def _write_last_query(paths: ProjectPaths, result: QueryResult) -> None:
    state = load_state(paths.state)
    state["last_query"] = {
        "question": result.question,
        "answered_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "context_pages": result.context_pages,
        "answer": result.answer,
        "citations": result.citations,
    }
    write_state(paths.state, state)


def _default_answer_generator() -> QueryAnswerGenerator:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise DeepSeekUnavailableError("DEEPSEEK_API_KEY is not set")
    from .deepseek import generate_query_answer_with_deepseek

    return generate_query_answer_with_deepseek


def _default_answer_streamer() -> QueryAnswerStreamer:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise DeepSeekUnavailableError("DEEPSEEK_API_KEY is not set")
    from .deepseek import generate_query_answer_stream_with_deepseek

    return generate_query_answer_stream_with_deepseek
