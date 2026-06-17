from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LlmConfig:
    provider: str = "deepseek"
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-pro"
    temperature: float = 0.2
    max_tokens: int = 4096
    context_limit: int = 640000


@dataclass(frozen=True)
class SearchConfig:
    top_k: int = 5
    page_char_limit: int = 2000
    total_context_char_limit: int = 10000


@dataclass(frozen=True)
class IngestConfig:
    short_doc_limit: int = 3000
    medium_doc_limit: int = 15000
    short_summary_limit: int = 800
    medium_summary_limit: int = 1500
    long_summary_limit: int = 2500
    chunk_min_chars: int = 2000
    chunk_max_chars: int = 4000


@dataclass(frozen=True)
class LintConfig:
    long_page_char_limit: int = 12000


@dataclass(frozen=True)
class LanguageConfig:
    default: str = "zh-CN"


@dataclass(frozen=True)
class AppConfig:
    llm: LlmConfig = LlmConfig()
    search: SearchConfig = SearchConfig()
    ingest: IngestConfig = IngestConfig()
    lint: LintConfig = LintConfig()
    language: LanguageConfig = LanguageConfig()


DEFAULT_CONFIG = AppConfig()


DEFAULT_CONFIG_TEXT = """[llm]
provider = "deepseek"
base_url = "https://api.deepseek.com"
model = "deepseek-v4-pro"
temperature = 0.2
max_tokens = 4096
context_limit = 10000

[search]
top_k = 5
page_char_limit = 2000
total_context_char_limit = 10000

[ingest]
short_doc_limit = 3000
medium_doc_limit = 15000
short_summary_limit = 800
medium_summary_limit = 1500
long_summary_limit = 2500
chunk_min_chars = 2000
chunk_max_chars = 4000

[lint]
long_page_char_limit = 12000

[language]
default = "zh-CN"
"""


def write_default_config(path: Path) -> None:
    path.write_text(DEFAULT_CONFIG_TEXT, encoding="utf-8")


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        return DEFAULT_CONFIG

    data = _parse_simple_toml(path.read_text(encoding="utf-8"))
    lint_data = dict(data.get("lint", {}))
    lint_data.pop("pending_proposal_days", None)
    return AppConfig(
        llm=LlmConfig(**data.get("llm", {})),
        search=SearchConfig(**data.get("search", {})),
        ingest=IngestConfig(**data.get("ingest", {})),
        lint=LintConfig(**lint_data),
        language=LanguageConfig(**data.get("language", {})),
    )


def _parse_simple_toml(text: str) -> dict[str, dict[str, object]]:
    data: dict[str, dict[str, object]] = {}
    current: dict[str, object] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = data.setdefault(line[1:-1], {})
            continue
        if current is None or "=" not in line:
            continue
        key, raw_value = [part.strip() for part in line.split("=", 1)]
        current[key] = _parse_value(raw_value)
    return data


def _parse_value(value: str) -> object:
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if "." in value:
        try:
            return float(value)
        except ValueError:
            return value
    try:
        return int(value)
    except ValueError:
        return value
