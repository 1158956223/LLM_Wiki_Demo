from __future__ import annotations

import argparse
import builtins
from pathlib import Path
from typing import Callable, Sequence

from .ingest import ExtractionGenerator, OverviewGenerator, SummaryGenerator, ingest_source
from .init import InitContent, initialize_project
from .proposal import ProposalPlanGenerator, propose_change
from .query import QueryAnswerGenerator, QueryAnswerStreamer, answer_query


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm_wiki")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="初始化 LLM Wiki 项目")
    init_parser.add_argument("--path", type=Path)

    ingest_parser = subparsers.add_parser("ingest", help="摄入项目外部的 Markdown 文件")
    ingest_parser.add_argument("--path", type=Path, help="已初始化的 LLM Wiki 项目目录")
    ingest_parser.add_argument("source", type=Path)

    query_parser = subparsers.add_parser("query", help="query wiki")
    query_parser.add_argument("--path", type=Path)
    query_parser.add_argument("question")

    add_parser = subparsers.add_parser("add", help="save the last query into the wiki")
    add_parser.add_argument("--path", type=Path)
    add_parser.add_argument("instruction")

    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    cwd: Path | None = None,
    input_func: Callable[[str], str] = input,
    init_content_generator: Callable[[str, str], InitContent] | None = None,
    ingest_summary_generator: SummaryGenerator | None = None,
    ingest_extraction_generator: ExtractionGenerator | None = None,
    ingest_overview_generator: OverviewGenerator | None = None,
    query_answer_generator: QueryAnswerGenerator | None = None,
    query_answer_streamer: QueryAnswerStreamer | None = None,
    proposal_plan_generator: ProposalPlanGenerator | None = None,
    print_func: Callable[..., None] | None = None,
) -> int:
    print_func = print_func or builtins.print
    parser = build_parser()
    args = parser.parse_args(argv)
    root = cwd or Path.cwd()

    if args.command == "init":
        target_root = args.path or root
        name = _prompt_required(input_func, "这个 Wiki 项目叫什么？")
        description = _prompt_required(input_func, "请描述这个项目：")
        generator = init_content_generator or _default_init_content_generator()
        result = initialize_project(
            target_root,
            name=name,
            description=description,
            init_content_generator=generator,
        )
        print_func(f"init completed: created={len(result.created)} skipped={len(result.skipped)}")
        for warning in result.warnings:
            print_func(f"warning: {warning}")
        return 0

    if args.command == "ingest":
        target_root = (root / args.path) if args.path else root
        result = ingest_source(
            target_root,
            args.source,
            summary_generator=ingest_summary_generator,
            extraction_generator=ingest_extraction_generator,
            overview_generator=ingest_overview_generator,
            confirm_name_conflict=lambda existing, incoming: _confirm_name_conflict(
                input_func, existing, incoming
            ),
            progress=print_func,
        )
        if result.skipped:
            print_func(f"该文件已存在！")
        else:
            print_func(f"ingest completed: {result.source_path} -> {result.wiki_page}")
        return 0

    if args.command == "query":
        target_root = (root / args.path) if args.path else root
        stream_tokens = query_answer_generator is None
        result = answer_query(
            target_root,
            args.question,
            answer_generator=query_answer_generator,
            answer_streamer=query_answer_streamer,
            on_token=(
                lambda token: print_func(token, end="", flush=True)
                if stream_tokens
                else None
            ),
        )
        if stream_tokens:
            print_func("")
        else:
            print_func(result.answer)
        return 0

    if args.command == "add":
        target_root = (root / args.path) if args.path else root
        result = propose_change(
            target_root,
            args.instruction,
            plan_generator=proposal_plan_generator,
        )
        print_func(f"add completed: {result.record_path}")
        for page in result.written_pages:
            print_func(f"- {page}")
        return 0

    return 0


def _prompt_required(input_func: Callable[[str], str], prompt: str) -> str:
    while True:
        value = input_func(f"{prompt} ").strip()
        if value:
            return value
        print("不能为空，请重新输入。")


def _default_init_content_generator() -> Callable[[str, str], InitContent]:
    from .deepseek import generate_init_content_with_deepseek

    return generate_init_content_with_deepseek


def _confirm_name_conflict(input_func: Callable[[str], str], existing: Path, incoming: Path) -> bool:
    prompt = (
        f"raw/sources 中已存在同名文件 {existing.name}，但内容不同。"
        f"是否覆盖并重新生成相关文件？[y/N]"
    )
    return input_func(f"{prompt} ").strip().lower() in {"y", "yes"}
