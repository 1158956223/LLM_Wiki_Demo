from __future__ import annotations


PURPOSE_MARKER = "<!-- llm-wiki:template=purpose:v1 -->"
SCHEMA_MARKER = "<!-- llm-wiki:template=schema:v1 -->"
OVERVIEW_MARKER = "<!-- llm-wiki:template=overview:v1 -->"
INDEX_MARKER = "<!-- llm-wiki:template=index:v1 -->"


def purpose_template(name: str, description: str | None) -> str:
    goal = description or "维护一个本地优先、Markdown 优先的长期知识库。"
    return f"""{PURPOSE_MARKER}
# {name} 的目的

## 为什么存在

{goal}

## 关注范围

- 需要长期保留、可追溯、可复用的知识。
- 来自原始 Markdown 资料并带有明确来源的内容。
- 经过人工审阅后可以沉淀进 wiki 的高价值问答。

## 非关注范围

- 没有来源支撑的一次性回答。
- 未经人工确认的自动写回。
- 和本 wiki 目标无关的资料堆积。
"""


def schema_template(name: str) -> str:
    return f"""{SCHEMA_MARKER}
# {name} 维护规则

## 页面类型

第一版支持 `source`、`concept`、`entity`、`synthesis` 和 `query`。

## 基础 frontmatter

```yaml
---
type: concept
title: 页面标题
created_at: 2026-06-12
updated_at: 2026-06-12
sources: []
tags: []
status: active
---
```

## 引用规则

每个正式 wiki 页面都必须包含 `## 来源`，并列出支撑该页面的原始资料或 wiki 页面。

## 写回规则

LLM 只能生成 proposal。正式 wiki 页面只能通过人工审阅后的 `apply` 更新。
"""


def overview_template(name: str, description: str | None) -> str:
    summary = description or "当前 wiki 尚未摄入资料。"
    return f"""{OVERVIEW_MARKER}
# {name} 概览

## 当前状态

{summary}

## 下一步

- 将 Markdown 原始资料放入 `raw/sources/`。
- 运行 `python -m llm_wiki ingest raw/sources/example.md` 摄入资料。
- 运行 `python -m llm_wiki index` 构建本地索引。
"""


def index_template(name: str) -> str:
    return f"""{INDEX_MARKER}
# {name} 索引

## 重要页面

- `wiki/overview.md`

## 页面类型

- Sources: `wiki/sources/`
- Concepts: `wiki/concepts/`
- Entities: `wiki/entities/`
- Synthesis: `wiki/synthesis/`
- Queries: `wiki/queries/`

## 来源覆盖

当前尚未摄入原始资料。
"""
