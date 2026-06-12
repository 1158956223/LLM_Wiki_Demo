from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable, Sequence

from .deepseek import generate_init_content_with_deepseek
from .init import InitContent
from .init import initialize_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm_wiki")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize an LLM Wiki project")
    init_parser.add_argument("--path", type=Path)

    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    cwd: Path | None = None,
    input_func: Callable[[str], str] = input,
    init_content_generator: Callable[[str, str], InitContent] | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = cwd or Path.cwd()

    if args.command == "init":
        target_root = args.path or root
        name = _prompt_required(input_func, "这个 Wiki 项目叫什么？")
        description = _prompt_required(input_func, "请用一句话描述这个项目：")
        generator = init_content_generator or generate_init_content_with_deepseek
        result = initialize_project(
            target_root,
            name=name,
            description=description,
            init_content_generator=generator,
        )
        print(f"init completed: created={len(result.created)} skipped={len(result.skipped)}")
        for warning in result.warnings:
            print(f"warning: {warning}")
        return 0

    return 0


def _prompt_required(input_func: Callable[[str], str], prompt: str) -> str:
    while True:
        value = input_func(f"{prompt} ").strip()
        if value:
            return value
        print("不能为空，请重新输入。")
