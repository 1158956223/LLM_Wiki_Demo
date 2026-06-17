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


def schema_template() -> str:
    return f"""{SCHEMA_MARKER}
# LLM Wiki 固定协议

## 核心原则

1. Markdown 文件是长期知识的事实来源。
2. `raw/` 保存原始证据，工具不自动改写。
3. `wiki/` 保存经过整理、可阅读、可引用的长期知识。
4. LLM 可以生成建议，但不能直接覆盖正式 wiki 页面。
5. 没有来源支撑的内容不能进入正式 wiki。

## 页面类型与目录

| type | 目录 | 说明 |
|------|------|------|
| source | `wiki/sources/` | 原始 Markdown 资料的摘要页，只由外部资料摄入流程创建或更新 |
| concept | `wiki/concepts/` | 可长期复用的概念、方法、机制或术语 |
| entity | `wiki/entities/` | 人物、组织、工具、模型、项目、论文等具名对象 |
| query | `wiki/queries/` | 值得保留的问题、回答和后续研究线索 |
| synthesis | `wiki/synthesis/` | 跨来源、跨页面形成的综合判断 |
| overview | `wiki/overview.md` | 当前 wiki 的高层概览，由资料摄入或知识写回流程更新 |

## Frontmatter 规范

正式 wiki 页面必须包含 YAML frontmatter。基础字段如下：

```yaml
---
type: source | concept | entity | query | synthesis | overview
title: 页面标题
created_at: YYYY-MM-DD
updated_at: YYYY-MM-DD
sources: []
tags: []
status: active
---
```

字段含义：

- `type` 必须和文件所在目录匹配。
- `title` 应该和页面一级标题一致。
- `sources` 保存支撑该页面的 raw 或 wiki 路径。
- `tags` 用于检索和组织。
- `status` 第一版使用 `active`、`draft`、`deprecated`。

## 命名规则

- 文件名由标题生成 slug。
- 空白统一转为 `-`。
- 移除 Windows 非法字符：`< > : " / \\ | ? *`。
- 同名文件追加短 hash。
- `source` 页文件名优先跟随原始 Markdown 文件名，保持 raw 到 wiki 的映射稳定。

## 页面正文规则

- 每个正式 wiki 页面必须有一级标题。
- 除 `overview` 外，每个正式 wiki 页面都应该包含 `## 来源`。
- `source` 页面引用 `raw/sources/` 下的原始文件。
- 非 `source` 页面引用已有 wiki 页面或 source 页面。
- 引用路径使用项目内相对路径，例如 `wiki/sources/example.md#关键观点`。

## 内部链接规则

- 页面之间优先使用 `[[page-slug]]` 记录知识关联。
- `concept`、`entity`、`synthesis` 应尽量链接相关页面。
- `query` 页面需要链接它依赖的来源、概念和仍待确认的问题。

## 索引与概览

- `wiki/index.md` 是导航入口，按页面类型列出已存在页面。
- `wiki/overview.md` 是项目概览，只总结已经进入 wiki 的内容。
- 初始化阶段只创建空壳；资料摄入或知识写回后再更新具体内容。

## 矛盾与不确定性

- 不同来源矛盾时，不要强行合并成确定结论。
- 在相关页面记录矛盾点和来源。
- 必要时创建或更新 `query` 页面追踪开放问题。
- 证据足够后，再用 `synthesis` 页面形成综合判断。

## 写回边界

- 当用户确认沉淀最近一次问答时，系统会保存原始问题和回答到 `wiki/queries/`。
- 如果问答包含新的长期知识，系统可以更新 `wiki/concepts/`、`wiki/entities/` 或 `wiki/synthesis/`。
- 如果问答与已有长期知识重复度过高，且没有新的概念、边界、例子、流程或结论，则只保留 `wiki/queries/` 记录，不更新长期知识页。
- 对话沉淀不写入 `wiki/sources/`；外部原始资料只能通过资料摄入流程进入。
"""


def overview_template() -> str:
    return f"""---
type: overview
title: 项目概览
tags: []
related: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

{OVERVIEW_MARKER}

# 项目概览

## 概览

<!-- 导入 Markdown 资料后，在这里生成或维护当前知识库的高层概览。 -->
"""


def index_template() -> str:
    return f"""{INDEX_MARKER}
# Wiki 索引

## 实体

## 概念

## 来源

## 问题

## 综合
"""
