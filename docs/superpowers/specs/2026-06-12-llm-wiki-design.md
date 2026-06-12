# LLM Wiki CLI 设计文档

## 目标

构建一个本地优先、Markdown 优先的 LLM Wiki。它遵守 Karpathy-style LLM Wiki 的核心思想：不要让每次 LLM 问答都停留在一次性消耗里，而是把高价值信息沉淀成可阅读、可编辑、可版本管理的长期知识。

第一版只做命令行工具。它支持导入 Markdown 原始资料，维护本地 wiki，用 DeepSeek API 回答问题，并且只通过人工确认的 proposal 把知识写回 wiki。

## 非目标

- 第一版不做网页界面。
- 第一版不允许 LLM 自动修改正式 wiki 页面。
- 第一版不支持 PDF、Word、图片、浏览器剪藏或网页爬取。
- 第一版不做知识图谱可视化。
- 第一版不强制引入向量数据库。
- 第一版不做 MCP Server 或后台常驻服务。

## 设计原则

1. Markdown 是长期知识的事实来源。
2. 原始资料必须保留，作为证据层存在。
3. 搜索索引和机器状态都是可重建的派生产物。
4. LLM 回答必须标注引用来源。
5. LLM 可以提出修改建议，但不能直接应用到正式 wiki。
6. 重要操作必须写入人类可读的日志。
7. 第一版优先选择小而透明的机制，避免过早引入重框架。

## 用户工作流

第一版跑通下面这条闭环：

```text
原始 Markdown
  -> ingest 摄入
  -> wiki 页面
  -> query 提问
  -> 带引用的回答
  -> proposal 修改建议
  -> 人工审阅
  -> apply 应用
  -> 更新后的 wiki
  -> 重建索引
```

示例命令：

```powershell
python -m llm_wiki init
python -m llm_wiki ingest raw/sources/example.md
python -m llm_wiki index
python -m llm_wiki search "LLM Wiki 和传统 RAG"
python -m llm_wiki query "LLM Wiki 和传统 RAG 有什么区别？"
python -m llm_wiki propose "把刚才的问题沉淀进 wiki"
python -m llm_wiki apply proposals/pending/2026-06-12-llm-wiki-vs-rag.md
python -m llm_wiki lint
```

## 项目目录

```text
LLM_Wiki_Demo/
  purpose.md
  schema.md

  raw/
    sources/

  wiki/
    index.md
    log.md
    overview.md
    sources/
    concepts/
    entities/
    synthesis/
    queries/

  proposals/
    pending/
    applied/
    rejected/

  .llm-wiki/
    config.toml
    state.json
    search_index.json

  src/
    llm_wiki/

  tests/
```

## 目录职责

### `purpose.md`

定义这个 wiki 为什么存在、关注什么问题、不关注什么问题。DeepSeek 的回答和写回建议都会读取这个文件，避免知识库变成没有方向的资料堆。

### `schema.md`

定义 wiki 的维护规则。它描述页面类型、命名规则、frontmatter 字段、引用格式、链接风格、proposal 格式等。DeepSeek 生成回答或 proposal 时要遵守这些规则。

### `raw/sources/`

存放原始 Markdown 输入。这里是证据层，LLM 操作不能修改这些文件。工具会在 `.llm-wiki/state.json` 中记录文件 hash，用来判断资料是否变化或过期。

### `wiki/`

存放长期知识层，也是人主要阅读和编辑的地方。

- `wiki/index.md`：导航入口，列出重要页面、摘要、页面类型和来源覆盖情况。
- `wiki/log.md`：追加式操作日志，记录 init、ingest、index、query、propose、apply、lint。
- `wiki/overview.md`：当前知识库的整体概览。
- `wiki/sources/`：由原始资料生成的资料摘要页。
- `wiki/concepts/`：概念页，例如 `RAG.md`、`Embedding.md`、`LLM Wiki.md`。
- `wiki/entities/`：实体页，例如人物、项目、工具、模型、公司或论文。
- `wiki/synthesis/`：跨来源综合分析页。
- `wiki/queries/`：值得长期保留的高价值问答。

### `proposals/`

存放人工可审阅的写回建议。

- `proposals/pending/`：等待审阅的 proposal。
- `proposals/applied/`：已经接受并应用的 proposal。
- `proposals/rejected/`：被拒绝或暂不采纳的 proposal。

### `.llm-wiki/`

存放程序状态和可重建的机器产物。

- `config.toml`：非敏感配置，例如模型名、base URL、温度、路径设置。
- `state.json`：已摄入文件 hash、源文件到 wiki 页面的映射、最近一次 query 元数据。
- `search_index.json`：由 Markdown 文件生成的本地搜索索引。

API Key 不能写入 `.llm-wiki/`。DeepSeek API Key 只通过环境变量 `DEEPSEEK_API_KEY` 读取。

## Wiki 页面模型

所有正式 wiki 页面统一使用 YAML frontmatter。这样页面仍然是普通 Markdown，人可以直接阅读和编辑；同时程序可以稳定读取页面类型、标题、来源、标签和状态。

基础 frontmatter：

```yaml
---
type: concept
title: LLM Wiki
created_at: 2026-06-12
updated_at: 2026-06-12
sources:
  - wiki/sources/karpathy-llm-wiki.md
tags:
  - llm
  - knowledge-management
status: active
---
```

字段含义：

- `type`：页面类型。第一版支持 `source`、`concept`、`entity`、`synthesis`、`query`。
- `title`：页面标题，应该和一级标题保持一致。
- `created_at`：页面创建日期。
- `updated_at`：页面最近更新时间。
- `sources`：支撑这个页面的来源路径。
- `tags`：主题标签，用于搜索、索引和组织。
- `status`：页面状态。第一版支持 `active`、`draft`、`deprecated`。

第一版不加入 `confidence`、`owner`、`reviewed_at`、`aliases` 等字段，避免过早把 wiki 页面变成复杂数据库记录。

## 页面类型与模板

第一版支持五种页面类型。它们使用统一 frontmatter，但正文模板不同。

### `source`

位置：`wiki/sources/`

职责：对应一个原始 Markdown 文件，记录它讲了什么、有哪些重要观点、可提炼出哪些概念或实体。

模板：

```markdown
---
type: source
title: Karpathy LLM Wiki
created_at: 2026-06-12
updated_at: 2026-06-12
sources:
  - raw/sources/karpathy-llm-wiki.md
tags:
  - llm-wiki
status: active
---

# Karpathy LLM Wiki

## 摘要

## 关键观点

## 可沉淀概念

## 涉及实体

## 引用片段

## 来源

- `raw/sources/karpathy-llm-wiki.md`
```

### `concept`

位置：`wiki/concepts/`

职责：长期维护一个概念，例如 RAG、LLM Wiki、Embedding、人工确认写回。

模板：

```markdown
---
type: concept
title: LLM Wiki
created_at: 2026-06-12
updated_at: 2026-06-12
sources:
  - wiki/sources/karpathy-llm-wiki.md
tags:
  - llm
status: active
---

# LLM Wiki

## 定义

## 核心原则

## 适用场景

## 与相关概念的区别

## 来源

- `wiki/sources/karpathy-llm-wiki.md#关键观点`
```

### `entity`

位置：`wiki/entities/`

职责：记录人物、项目、工具、模型、公司、论文等实体。

模板：

```markdown
---
type: entity
title: DeepSeek
created_at: 2026-06-12
updated_at: 2026-06-12
sources:
  - wiki/sources/deepseek-api-notes.md
tags:
  - model-provider
status: active
---

# DeepSeek

## 简介

## 与本 wiki 的关系

## 关键事实

## 相关概念

## 来源

- `wiki/sources/deepseek-api-notes.md`
```

### `synthesis`

位置：`wiki/synthesis/`

职责：跨多个来源形成分析，不对应单一资料。比如“LLM Wiki 与传统 RAG 的区别”。

模板：

```markdown
---
type: synthesis
title: LLM Wiki 与传统 RAG 的区别
created_at: 2026-06-12
updated_at: 2026-06-12
sources:
  - wiki/sources/karpathy-llm-wiki.md
  - wiki/concepts/RAG.md
tags:
  - rag
  - llm-wiki
status: active
---

# LLM Wiki 与传统 RAG 的区别

## 结论

## 对比

## 适用边界

## 仍待验证的问题

## 来源

- `wiki/sources/karpathy-llm-wiki.md#关键观点`
- `wiki/concepts/RAG.md#定义`
```

### `query`

位置：`wiki/queries/`

职责：沉淀值得复用的问题和答案。它不是聊天记录，而是经过整理后的知识条目。

模板：

```markdown
---
type: query
title: LLM Wiki 和传统 RAG 有什么区别
created_at: 2026-06-12
updated_at: 2026-06-12
sources:
  - wiki/sources/karpathy-llm-wiki.md
  - wiki/concepts/RAG.md
tags:
  - rag
  - llm-wiki
status: active
---

# LLM Wiki 和传统 RAG 有什么区别？

## 问题

## 回答

## 后续可沉淀页面

## 来源

- `wiki/sources/karpathy-llm-wiki.md#关键观点`
- `wiki/concepts/RAG.md#定义`
```

## 文件命名规则

文件名使用标题生成的 slug。第一版保留中文、英文和数字，空白转成短横线。

规则：

1. 去掉标题首尾空白。
2. 空白字符统一转成 `-`。
3. 移除 Windows 非法字符：`< > : " / \ | ? *`。
4. 连续多个 `-` 合并成一个。
5. 文件名最多 80 个字符，超出后截断。
6. 如果重名，在末尾追加 6 位短 hash。
7. 保留大小写，不强制小写。
8. 页面标题以 frontmatter `title` 和一级标题为准，文件名只是路径。

示例：

```text
LLM Wiki 与传统 RAG 的区别？
-> LLM-Wiki-与传统-RAG-的区别.md

LLM Wiki 与传统 RAG 的区别？
-> LLM-Wiki-与传统-RAG-的区别-a1b2c3.md
```

页面类型到目录的映射：

```text
source    -> wiki/sources/
concept   -> wiki/concepts/
entity    -> wiki/entities/
synthesis -> wiki/synthesis/
query     -> wiki/queries/
```

`source` 页面文件名来自原始文件名，而不是 LLM 总结出的标题。这样原始资料到 source 页面之间的映射更稳定：

```text
raw/sources/karpathy-llm-wiki.md
-> wiki/sources/karpathy-llm-wiki.md
```

## 引用格式

第一版使用页面末尾统一 `## 来源` 列表，不使用正文脚注。

格式：

```markdown
## 来源

- `wiki/sources/karpathy-llm-wiki.md#关键观点`
- `wiki/concepts/RAG.md#定义`
```

规则：

1. 每个正式 wiki 页面都应该包含 `## 来源`。
2. `source` 页面可以引用 `raw/sources/` 下的原始文件。
3. `concept`、`entity`、`synthesis`、`query` 页面引用 wiki 页面。
4. 引用格式是 `路径#标题`。
5. 如果没有具体 heading，可以只写路径。
6. `lint` 第一版检查 `## 来源` 是否存在、来源列表是否非空、路径是否存在。
7. 如果引用包含 `#heading`，第一版不强制检查 heading 是否存在，后续再增强。
8. DeepSeek 的 `query` 输出也必须包含引用列表。
9. `proposal` 必须包含 `## Citations` 或 `## 引用`，否则 `apply` 拒绝执行。

硬规则：没有来源的知识不能进入正式 wiki。如果来源不足，只能进入 query 草稿或 proposal，并标注“证据不足”。

## `state.json` 结构

`state.json` 是工具运行所需的短期状态，不是长期知识。它可以删除并重建，不应该承载重要知识。

第一版结构：

```json
{
  "version": 1,
  "sources": {
    "raw/sources/karpathy-llm-wiki.md": {
      "sha256": "abc123",
      "ingested_at": "2026-06-12T10:00:00+08:00",
      "wiki_page": "wiki/sources/karpathy-llm-wiki.md"
    }
  },
  "last_query": {
    "question": "LLM Wiki 和传统 RAG 有什么区别？",
    "answered_at": "2026-06-12T10:30:00+08:00",
    "context_pages": [
      "wiki/sources/karpathy-llm-wiki.md",
      "wiki/concepts/RAG.md"
    ],
    "answer": "DeepSeek 的完整回答文本",
    "citations": [
      "wiki/sources/karpathy-llm-wiki.md#关键观点",
      "wiki/concepts/RAG.md#定义"
    ]
  }
}
```

规则：

- `sources` 记录摄入状态。
- `last_query` 只保存最近一次 query，不保存完整历史。
- `last_query.answer` 保存完整回答，方便 `propose` 使用。
- 完整历史如果值得保留，必须通过 `propose -> apply` 进入 `wiki/queries/`。
- `propose` 默认读取 `last_query.question`、`last_query.answer`、`last_query.context_pages` 和 `last_query.citations`。

## `search_index.json` 结构

`search_index.json` 是本地搜索索引，用来支持 `search` 和 `query`。第一版不依赖向量库，所以索引必须简单、透明、可检查。

第一版结构：

```json
{
  "version": 1,
  "built_at": "2026-06-12T10:40:00+08:00",
  "pages": [
    {
      "path": "wiki/concepts/LLM-Wiki.md",
      "type": "concept",
      "title": "LLM Wiki",
      "headings": ["定义", "核心原则", "适用场景", "来源"],
      "tags": ["llm", "knowledge-management"],
      "wikilinks": ["RAG", "Embedding"],
      "sources": ["wiki/sources/karpathy-llm-wiki.md"],
      "text": "页面的纯文本内容..."
    }
  ]
}
```

规则：

- 索引保存完整页面纯文本，方便快速查询和调试。
- `index` 命令从 `wiki/` 重新生成整个索引。
- `search` 只读取索引，不直接扫描所有 Markdown。
- 索引是派生产物，可以删除后重建。

第一版搜索打分规则：

- 标题命中：高分。
- heading 命中：高分。
- tag 命中：中高分。
- wikilink 命中：中分。
- 正文命中：基础分。

## CLI 命令设计

### `init`

初始化项目结构和基础文件。

职责：

- 创建 `purpose.md`、`schema.md`、`raw/sources/`、`wiki/`、`proposals/`、`.llm-wiki/`。
- 创建初始的 `wiki/index.md`、`wiki/log.md`、`wiki/overview.md`。
- 创建 `.llm-wiki/config.toml`、`.llm-wiki/state.json`、`.llm-wiki/search_index.json`。
- 不覆盖用户已有内容。
- 向 `wiki/log.md` 追加 init 记录。

### `ingest <path>`

摄入一个 Markdown 文件，或摄入一个包含 Markdown 文件的目录。

职责：

- 读取 Markdown 文件。
- 计算内容 hash。
- 对未变化的文件跳过处理，除非用户强制刷新。
- 在 `wiki/sources/` 中生成或更新资料摘要页。
- 更新 `wiki/index.md`。
- 更新 `.llm-wiki/state.json`。
- 向 `wiki/log.md` 追加 ingest 记录。

### `index`

构建第一版本地搜索索引。

职责：

- 扫描 `wiki/` 下的 Markdown 页面。
- 提取标题、标题层级、wikilink、来源引用和正文片段。
- 写入 `.llm-wiki/search_index.json`。
- 向 `wiki/log.md` 追加 index 记录。

第一版使用确定性的本地搜索：标题匹配、heading 匹配、精确词匹配、简单 token 重叠和 wikilink 匹配。向量检索以后可以加入，但不作为第一版的核心依赖。

### `search <query>`

只搜索本地索引，不调用 DeepSeek。

职责：

- 读取 `.llm-wiki/search_index.json`。
- 返回匹配页面和片段。
- 展示文件路径和分数。

这个命令用于调试检索质量，避免一开始就把所有问题归因给 LLM。

### `query <question>`

使用本地 wiki 上下文和 DeepSeek API 回答问题。

职责：

- 读取 `purpose.md`、`schema.md` 和 `wiki/index.md`。
- 搜索相关 wiki 页面。
- 构造要求带引用回答的 prompt。
- 调用 DeepSeek API。
- 输出答案和引用来源。
- 将最近一次 query 的元数据写入 `.llm-wiki/state.json`。
- 向 `wiki/log.md` 追加 query 记录。

第一版的 `query` 不会自动写入 wiki。

### `propose <instruction>`

基于最近一次 query 或用户明确指令，生成待审阅的写回建议。

职责：

- 读取 `.llm-wiki/state.json` 中最近一次 query 元数据。
- 结合 `purpose.md` 和 `schema.md` 调用 DeepSeek 生成 proposal。
- 将 proposal 写入 `proposals/pending/`。
- proposal 必须包含目标页面、操作类型、建议内容、理由和引用。
- 向 `wiki/log.md` 追加 propose 记录。

### `apply <proposal-path>`

应用人工确认过的 proposal。

职责：

- 校验 proposal frontmatter 和必填章节。
- 只修改 proposal 中声明的目标 wiki 页面。
- 将 proposal 从 `pending` 移动到 `applied`。
- 更新 `wiki/index.md`。
- 重建 `.llm-wiki/search_index.json`。
- 向 `wiki/log.md` 追加 apply 记录。

如果 proposal 格式错误、目标路径在 `wiki/` 外部、缺少引用，命令必须安全失败，不能修改正式 wiki。

### `lint`

检查 wiki 健康状态，不自动修改内容。

职责：

- 报告缺少一级标题的 wiki 页面。
- 报告缺少来源引用的 wiki 页面。
- 报告没有出现在 `wiki/index.md` 中的页面。
- 报告 hash 已变化但未重新 ingest 的 raw source。
- 报告没有入链的孤立页面。
- 报告长期 pending 的 proposal。
- 向 `wiki/log.md` 追加 lint 记录。

## Proposal 格式

proposal 是一个带 YAML frontmatter 的 Markdown 文件：

```markdown
---
type: writeback_proposal
status: pending
created_at: 2026-06-12T10:00:00+08:00
target: wiki/concepts/LLM Wiki.md
operation: append_section
sources:
  - wiki/sources/karpathy-llm-wiki.md
  - wiki/queries/llm-wiki-vs-rag.md
---

# Proposal

## Summary

本次建议修改的简短说明。

## Proposed Change

建议新增或写入的 Markdown 内容。

## Rationale

为什么这段内容值得沉淀进 wiki。

## Citations

- `wiki/sources/karpathy-llm-wiki.md`
- `wiki/queries/llm-wiki-vs-rag.md`
```

第一版只支持两种操作：

- `append_section`：向已有页面追加一个新章节。
- `create_page`：创建一个新的 wiki 页面。

替换式修改先不做，因为它需要更强的 diff 审阅机制。

## DeepSeek 集成

项目通过 OpenAI-compatible chat completion API 调用 DeepSeek。

配置来源：

- `DEEPSEEK_API_KEY`：必需环境变量。
- `.llm-wiki/config.toml`：模型名、base URL、温度、token 限制。

Prompt 输入：

- 用户问题或 proposal 指令。
- `purpose.md`。
- `schema.md` 中的相关规则。
- `wiki/index.md`。
- 检索到的 wiki 片段。

Prompt 要求：

- 默认用中文回答。
- 来自 wiki 上下文的事实性内容必须带引用。
- 如果 wiki 证据不足，要明确说明不足。
- 不能编造不存在的来源路径。
- 生成 proposal 时，只能修改声明的目标页面，并保持 Markdown 可读。

## 错误处理

- 缺少 `DEEPSEEK_API_KEY`：显示清晰错误并以非零状态退出。
- 缺少必要项目文件：提示用户运行 `init`。
- proposal 格式错误：报告校验错误，不修改任何文件。
- proposal 目标路径在 `wiki/` 外部：拒绝应用。
- 检索结果为空：说明当前 wiki 证据不足，可提示用户是否创建研究笔记。
- API 调用失败：显示简短错误，不把 query 标记为成功，并向日志写入失败记录。

## 测试策略

第一版优先测试确定性逻辑，不把测试重点放在 LLM 回答质量上。

测试范围：

- `init` 能创建预期结构，并且不覆盖已有文件。
- `ingest` 能记录 hash，并生成资料摘要页。
- `index` 能提取标题、heading、wikilink 和片段。
- `search` 能返回预期的本地匹配结果。
- `query` 使用 mock DeepSeek client 测试 prompt 和输出处理。
- `propose` 使用 mock LLM 输出生成合法 pending proposal。
- `apply` 会拒绝不安全路径和格式错误 proposal。
- `apply` 能接受合法的 `append_section` 和 `create_page` proposal。
- `lint` 能报告缺标题、缺 index、raw source 过期和孤立页面。

## 后续扩展

CLI 闭环稳定后，再考虑：

- 使用 Chroma、FAISS 或 LanceDB 增加向量检索。
- 增加 `links` 命令，自动建议 wikilink。
- 增加 `synthesize` 命令，生成跨页面主题综合。
- 增加 `review` 命令，检查冲突、过期和重复内容。
- 增加网页 UI。
- 增加 MCP Server。
- 增加 PDF、Word、图片、浏览器剪藏摄入。
- 导出和可视化知识图谱。

## 验收标准

第一版完成时应满足：

1. 用户可以在空仓库中初始化 wiki。
2. Markdown 原始资料可以被摄入到 `wiki/sources/`。
3. 本地索引可以被构建和搜索。
4. DeepSeek 支持的 query 可以返回带引用答案。
5. proposal 可以生成，但不会修改正式 wiki。
6. 人工审阅后的合法 proposal 可以被应用。
7. lint 可以报告基础 wiki 健康问题。
8. 测试覆盖确定性行为，并 mock 所有 DeepSeek 调用。
