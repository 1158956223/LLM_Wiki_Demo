from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import UnsafePathError


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.resolve())

    @property
    def purpose(self) -> Path:
        return self.root / "purpose.md"

    @property
    def schema(self) -> Path:
        return self.root / "schema.md"

    @property
    def raw_sources_dir(self) -> Path:
        return self.root / "raw" / "sources"

    @property
    def wiki_dir(self) -> Path:
        return self.root / "wiki"

    @property
    def wiki_index(self) -> Path:
        return self.wiki_dir / "index.md"

    @property
    def wiki_log(self) -> Path:
        return self.wiki_dir / "log.md"

    @property
    def wiki_overview(self) -> Path:
        return self.wiki_dir / "overview.md"

    @property
    def tool_dir(self) -> Path:
        return self.root / ".llm-wiki"

    @property
    def config(self) -> Path:
        return self.tool_dir / "config.toml"

    @property
    def state(self) -> Path:
        return self.tool_dir / "state.json"

    @property
    def search_index(self) -> Path:
        return self.tool_dir / "search.sqlite"

    def safe_relative(self, value: str | Path) -> Path:
        candidate = (self.root / value).resolve()
        if candidate == self.root or self.root in candidate.parents:
            return candidate
        raise UnsafePathError(f"path escapes project root: {value}")
