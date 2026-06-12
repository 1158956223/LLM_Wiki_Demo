from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .init import initialize_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm_wiki")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize an LLM Wiki project")
    init_parser.add_argument("--name")
    init_parser.add_argument("--path", type=Path)
    init_parser.add_argument("--description")
    init_parser.add_argument("--no-llm", action="store_true")
    init_parser.add_argument("--force", action="store_true")

    return parser


def main(argv: Sequence[str] | None = None, *, cwd: Path | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = cwd or Path.cwd()

    if args.command == "init":
        target_root = args.path or root
        name = args.name or target_root.name
        result = initialize_project(
            target_root,
            name=name,
            description=args.description,
            use_llm=not args.no_llm,
            force=args.force,
        )
        print(f"init completed: created={len(result.created)} skipped={len(result.skipped)}")
        for warning in result.warnings:
            print(f"warning: {warning}")
        return 0

    return 0
