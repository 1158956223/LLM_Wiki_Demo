from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable


LIST_FIELDS = {"sources", "tags", "related"}
LOCKED_FIELDS = {"type", "title", "created_at"}
PageBodyMergeGenerator = Callable[["PageBodyMergeRequest"], str]


@dataclass(frozen=True)
class PageBodyMergeRequest:
    title: str
    page_type: str
    existing_body: str
    incoming_body: str


def merge_page_content(
    existing: str,
    incoming: str,
    *,
    body_merge_generator: PageBodyMergeGenerator | None = None,
) -> str:
    # 页面合并分成两层：frontmatter 用确定性规则合并，正文交给可插拔的 LLM 合并器。
    existing_frontmatter, existing_body = _split_frontmatter(existing)
    incoming_frontmatter, incoming_body = _split_frontmatter(incoming)
    merged_frontmatter = _merge_frontmatter(existing_frontmatter, incoming_frontmatter)
    merged_body = _merge_body(
        existing_frontmatter,
        existing_body,
        incoming_body,
        body_merge_generator=body_merge_generator,
    )
    return _render_page(merged_frontmatter, merged_body)


# 给已有页面补充 frontmatter 里的列表字段
def merge_frontmatter_lists(markdown: str, additions: dict[str, list[str]]) -> str:
    frontmatter, body = _split_frontmatter(markdown)
    incoming = {key: values for key, values in additions.items() if key in LIST_FIELDS}
    merged_frontmatter = _merge_frontmatter(frontmatter, incoming)
    return _render_page(merged_frontmatter, body)


# 把 Markdown 拆成元数据和正文
def _split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text.strip() + "\n"
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text.strip() + "\n"
    frontmatter_text = text[4:end].strip("\n")
    body = text[end + len("\n---"):].lstrip("\n")
    return _parse_frontmatter(frontmatter_text), body.strip() + "\n"


# 把元数据解析成字典
def _parse_frontmatter(text: str) -> dict[str, object]:
    data: dict[str, object] = {}
    current_key: str | None = None
    for line in text.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key:
            value = line[4:].strip().strip('"')
            current = data.setdefault(current_key, [])
            if isinstance(current, list):
                current.append(value)
            continue
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value == "[]":
            data[key] = []
            current_key = key
        elif value:
            data[key] = value.strip('"')
            current_key = None
        else:
            data[key] = []
            current_key = key
    return data


# 合并元数据
def _merge_frontmatter(existing: dict[str, object], incoming: dict[str, object]) -> dict[str, object]:
    merged = dict(existing)
    for key, value in incoming.items():
        # 来源、标签、关联页都是累积型字段，重复导入时只补新增项。
        if key in LIST_FIELDS:
            merged[key] = _unique_values(_as_list(existing.get(key)) + _as_list(value))
        # 这些字段定义了页面身份，已有页面的身份不被后续导入覆盖。
        elif key in LOCKED_FIELDS and key in existing:
            continue
        elif key == "updated_at":
            merged[key] = value or date.today().isoformat()
        elif key not in merged:
            merged[key] = value
    return merged


def _merge_body(
    existing_frontmatter: dict[str, object],
    existing_body: str,
    incoming_body: str,
    *,
    body_merge_generator: PageBodyMergeGenerator | None,
) -> str:
    existing = existing_body.strip()
    incoming = _strip_duplicate_title(incoming_body, existing).strip()
    if not incoming or incoming in existing:
        return existing + "\n"
    if body_merge_generator is not None:
        # 这里不直接拼接正文；调用方可以注入 DeepSeek 或测试替身来做语义合并。
        title = str(existing_frontmatter.get("title") or _first_title(existing_body) or "")
        page_type = str(existing_frontmatter.get("type") or "unknown")
        return body_merge_generator(
            PageBodyMergeRequest(
                title=title,
                page_type=page_type,
                existing_body=existing,
                incoming_body=incoming,
            )
        ).strip() + "\n"
    return f"{existing}\n\n{incoming}\n"


def _strip_duplicate_title(incoming_body: str, existing_body: str) -> str:
    existing_title = _first_title(existing_body)
    lines = incoming_body.strip().splitlines()
    if lines and existing_title and lines[0].strip() == f"# {existing_title}":
        return "\n".join(lines[1:]).strip()
    return incoming_body


def _first_title(body: str) -> str | None:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _render_page(frontmatter: dict[str, object], body: str) -> str:
    return f"---\n{_render_frontmatter(frontmatter)}---\n\n{body.strip()}\n"


def _render_frontmatter(frontmatter: dict[str, object]) -> str:
    lines: list[str] = []
    for key, value in frontmatter.items():
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                lines.extend(f"  - {item}" for item in value)
            else:
                lines.append(f"{key}: []")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value in (None, ""):
        return []
    return [str(value)]


def _unique_values(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
