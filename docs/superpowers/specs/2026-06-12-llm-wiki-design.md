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
    search.sqlite

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
- `search.sqlite`：由 Markdown 文件生成的本地 SQLite FTS5 搜索索引。

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

## `search.sqlite` 结构

`search.sqlite` 是本地搜索索引，用来支持 `search` 和 `query`。第一版不依赖向量库，而是使用 SQLite FTS5 + trigram tokenizer 做可解释的本地全文检索。

SQLite FTS5 是 SQLite 的全文检索扩展，支持 `MATCH` 查询、BM25 排序、`snippet()` 摘要片段和 `highlight()` 高亮。trigram tokenizer 会把文本切成连续三字符片段，适合中文和中英混合内容的子串匹配。

第一版索引库位置：

```text
.llm-wiki/search.sqlite
```

核心 FTS 表：

```sql
CREATE VIRTUAL TABLE pages_fts USING fts5(
  path UNINDEXED,
  type UNINDEXED,
  title,
  headings,
  tags,
  wikilinks,
  sources,
  text,
  tokenize = 'trigram'
);
```

每个 wiki 页面对应一条记录：

```json
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
```

规则：

- 索引保存完整页面纯文本，方便快速查询、snippet 生成和调试。
- `index` 命令从 `wiki/` 重新生成整个索引。
- `search` 只查询 SQLite FTS5 索引，不直接扫描所有 Markdown。
- 索引是派生产物，可以删除后重建。
- 实现时必须检测当前 Python 的 SQLite 是否支持 FTS5 和 trigram tokenizer。
- 如果 SQLite 不支持 FTS5 或 trigram，`index` 应该清晰失败，并提示用户当前 Python/SQLite 环境不满足要求。

第一版搜索查询示例：

```sql
SELECT
  path,
  type,
  title,
  snippet(pages_fts, -1, '[', ']', '...', 20) AS snippet,
  bm25(pages_fts, 8.0, 1.0, 5.0, 4.0, 2.0, 1.0, 1.0) AS score
FROM pages_fts
WHERE pages_fts MATCH ?
ORDER BY score
LIMIT 10;
```

字段权重：

- `title`：8.0
- `headings`：5.0
- `tags`：4.0
- `wikilinks`：2.0
- `sources`：1.0
- `text`：1.0

注意：SQLite FTS5 的 `bm25()` 返回值越小，匹配越好，所以结果按 `score ASC` 排序。

## CLI 命令设计

### `init`

初始化项目结构和基础文件。

职责：

- 创建 `purpose.md`、`schema.md`、`raw/sources/`、`wiki/`、`proposals/`、`.llm-wiki/`。
- 创建初始的 `wiki/index.md`、`wiki/log.md`、`wiki/overview.md`。
- 创建 `.llm-wiki/config.toml`、`.llm-wiki/state.json`、`.llm-wiki/search.sqlite`。
- 不覆盖用户已有内容。
- 向 `wiki/log.md` 追加 init 记录。

第一版 `init` 是智能初始化命令。它优先使用 DeepSeek 根据项目名和项目描述生成初始内容；如果没有 API Key 或 API 调用失败，则降级为内置默认模板，不中断初始化。

支持参数：

```powershell
python -m llm_wiki init --name "LLM_Wiki_Demo"
python -m llm_wiki init --name "LLM_Wiki_Demo" --description "本项目用于构建本地 LLM Wiki"
python -m llm_wiki init --no-llm
python -m llm_wiki init --force
```

参数含义：

- `--name`：项目名，用于生成 `purpose.md`、`schema.md` 和 `wiki/overview.md`。
- `--description`：用户提供的一句话目标，帮助 DeepSeek 生成更贴近项目的初始化内容。
- `--no-llm`：强制使用默认模板，不调用 DeepSeek。
- `--force`：允许刷新工具生成的默认模板文件。

DeepSeek 可用时，`init` 生成：

- 定制版 `purpose.md`。
- 定制版 `schema.md`。
- 定制版 `wiki/overview.md`。

DeepSeek 不可用时，`init` 降级生成：

- 默认模板 `purpose.md`。
- 默认模板 `schema.md`。
- 默认模板 `wiki/overview.md`。

降级不算失败，但必须写入 `wiki/log.md`：

```text
init completed with default templates because DeepSeek was unavailable
```

覆盖规则：

1. 文件不存在：创建。
2. 文件存在，并且包含工具模板 marker：`--force` 时可以覆盖。
3. 文件存在，但不包含工具模板 marker：不覆盖，输出 warning。
4. 没有 `--force` 时，任何已有文件都不覆盖。

工具生成的模板文件必须包含隐藏 marker：

```markdown
<!-- llm-wiki:template=purpose:v1 -->
```

不同文件使用不同 marker：

```text
purpose.md        -> <!-- llm-wiki:template=purpose:v1 -->
schema.md         -> <!-- llm-wiki:template=schema:v1 -->
wiki/overview.md  -> <!-- llm-wiki:template=overview:v1 -->
wiki/index.md     -> <!-- llm-wiki:template=index:v1 -->
```

如果用户手动编辑文件后希望保护内容，可以删除 marker。工具看到 marker 缺失时，即使传入 `--force`，也不会覆盖该文件。

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

第一版 `ingest` 只做 LLM 辅助摄入，不提供无 LLM 降级。进入 `wiki/` 的 source summary 必须经过 DeepSeek 加工。如果 DeepSeek 不可用，摄入失败。

支持命令：

```powershell
python -m llm_wiki ingest raw/sources/example.md
python -m llm_wiki ingest raw/sources/
python -m llm_wiki ingest raw/sources/example.md --force
```

规则：

1. 输入路径必须位于 `raw/sources/` 下。
2. 输入必须是 `.md` 文件，或包含 `.md` 文件的目录。
3. 缺少 `DEEPSEEK_API_KEY` 时失败。
4. DeepSeek API 调用失败时失败。
5. LLM 输出缺少 frontmatter 时失败。
6. LLM 输出缺少 `## 来源` 时失败。
7. LLM 输出的来源路径不是当前原始文件路径时失败。
8. 普通模式下，如果原始文件 hash 未变化，则跳过。
9. `--force` 会忽略 hash，重新调用 DeepSeek。

流程：

```text
接收 path
  -> 确认路径在 raw/sources/ 下
  -> 确认是 .md 文件或目录
  -> 计算 sha256
  -> 如果 hash 未变化且没有 --force，则跳过
  -> 读取原始 Markdown
  -> 按 Markdown 结构分块
  -> 调用 DeepSeek 生成 source summary
  -> 校验 source summary
  -> 写入新 source 页面，或为已有 source 页面生成 proposal
  -> 更新 state.json
  -> 更新 wiki/index.md
  -> 追加 wiki/log.md
  -> 重建 search.sqlite
```

写入规则：

- 如果目标 `wiki/sources/<source-file-name>.md` 不存在，摄入成功后直接创建。
- 如果目标 source 页面已存在，不直接覆盖，而是生成 `proposals/pending/` 下的更新 proposal。
- 用户确认 proposal 后，才通过 `apply` 修改已有 source 页面。

已存在 source 页面时，`state.json` 不应直接标记新 hash 为成功摄入，而是记录 pending proposal：

```json
{
  "sources": {
    "raw/sources/example.md": {
      "sha256": "oldhash",
      "ingested_at": "2026-06-12T10:00:00+08:00",
      "wiki_page": "wiki/sources/example.md",
      "pending_proposal": {
        "path": "proposals/pending/2026-06-12-update-source-example.md",
        "sha256": "newhash",
        "created_at": "2026-06-12T11:00:00+08:00"
      }
    }
  }
}
```

source summary 采用自适应摘要策略：

- 短文档：中文 3000 字以内，summary 最多约 800 字。
- 中等文档：中文 3000-15000 字，summary 最多约 1500 字。
- 长文档：中文 15000 字以上，先分块摘要，再合成总摘要；最终 source page 最多约 2500 字。

LLM 输出结构必须符合 source 页面模板：

```markdown
# Source Title

## 摘要

## 关键观点

## 可沉淀概念

## 涉及实体

## 引用片段

## 来源

- `raw/sources/example.md`
```

长 Markdown 使用 Markdown-aware 分块策略：

1. 一级标题作为大边界。
2. 二级标题作为主要 chunk 边界。
3. 保持代码块完整，不从代码块中间切开。
4. 单块目标 2000-4000 中文字符。
5. 超长章节再按段落切分。
6. 每块保留 heading path，例如 `# LLM Wiki / ## 核心思想 / ### Writeback`。

### `index`

构建第一版本地搜索索引。

职责：

- 扫描 `wiki/` 下的 Markdown 页面。
- 提取标题、标题层级、wikilink、来源引用和正文片段。
- 写入 `.llm-wiki/search.sqlite`。
- 向 `wiki/log.md` 追加 index 记录。

第一版使用确定性的本地搜索：标题匹配、heading 匹配、精确词匹配、简单 token 重叠和 wikilink 匹配。向量检索以后可以加入，但不作为第一版的核心依赖。

### `search <query>`

只搜索本地索引，不调用 DeepSeek。

职责：

- 查询 `.llm-wiki/search.sqlite`。
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

详细流程：

```text
读取 purpose.md
  -> 读取 schema.md
  -> 读取 wiki/index.md
  -> 用 SQLite FTS5 搜索相关页面
  -> 取 top_k 页面片段
  -> 回读完整 Markdown 页面或相关 heading 段落
  -> 构造 DeepSeek prompt
  -> 要求回答必须基于给定上下文
  -> 输出答案和引用
  -> 写入 state.json.last_query
  -> 追加 wiki/log.md
```

上下文选择策略：

- 默认取 top 5 个相关页面。
- 每页最多取 2000 中文字符左右。
- 总上下文最多 8000-10000 中文字符左右。
- 如果页面太长，优先保留 frontmatter、一级标题、命中 heading 附近段落和 `## 来源`。
- 不能只把 SQLite `snippet()` 结果交给 DeepSeek；`snippet()` 用于定位命中位置，query 阶段仍要回读 Markdown 上下文。

Prompt 结构：

```text
System:
你是本地 LLM Wiki 的问答助手。只能根据给定 wiki context 回答。
如果证据不足，明确说证据不足。不能编造来源。

Purpose:
<purpose.md>

Schema Rules:
<schema.md 中和引用、页面规则有关的部分>

Wiki Context:
<检索到的页面片段，必须带 path>

User Question:
<用户问题>
```

DeepSeek 输出必须使用以下结构：

```markdown
## 回答

...

## 依据

- `wiki/sources/xxx.md#某标题`
- `wiki/concepts/yyy.md#某标题`

## 证据不足或待确认

无明显不足。
```

如果证据不足，`## 回答` 中应明确说明无法从当前 wiki 得出可靠结论，`## 证据不足或待确认` 中列出缺失信息。

`state.json.last_query` 写入规则：

- API 调用失败：不写成功的 `last_query`。
- 检索结果为空：不调用 DeepSeek，直接输出“wiki 中没有足够上下文”，追加 log，不写 `last_query`。
- DeepSeek 正常返回“证据不足”：写入 `last_query`，因为这是一次有效回答。
- 成功回答：写入完整 `question`、`answered_at`、`context_pages`、`answer` 和 `citations`。

### `propose <instruction>`

基于最近一次 query 或用户明确指令，生成待审阅的写回建议。

职责：

- 读取 `.llm-wiki/state.json` 中最近一次 query 元数据。
- 结合 `purpose.md` 和 `schema.md` 调用 DeepSeek 生成 proposal。
- 将 proposal 写入 `proposals/pending/`。
- proposal 必须包含目标页面、操作类型、建议内容、理由和引用。
- 向 `wiki/log.md` 追加 propose 记录。

proposal 来源：

- 来自最近一次 `query`：例如 `python -m llm_wiki propose "把刚才的问题沉淀进 wiki"`。
- 来自用户明确指令：例如 `python -m llm_wiki propose "基于 wiki/sources/xxx.md 创建一个 RAG 概念页"`。

生成规则：

- `propose` 只能写入 `proposals/pending/`。
- `propose` 不允许修改 `wiki/` 下的正式页面。
- proposal 必须声明 `operation`，第一版只允许 `append_section` 和 `create_page`。
- proposal 必须声明 `target`。
- proposal 必须声明 `sources`。
- proposal 必须写入 `proposal_sha256`，用于后续判断用户是否编辑过 proposal。
- `propose` 成功后向 `wiki/log.md` 记录 proposal 路径、target、operation 和 sources。

### `apply <proposal-path>`

应用人工确认过的 proposal。

职责：

- 校验 proposal frontmatter 和必填章节。
- 只修改 proposal 中声明的目标 wiki 页面。
- 将 proposal 从 `pending` 移动到 `applied`。
- 更新 `wiki/index.md`。
- 重建 `.llm-wiki/search.sqlite`。
- 向 `wiki/log.md` 追加 apply 记录。

如果 proposal 格式错误、目标路径在 `wiki/` 外部、缺少引用，命令必须安全失败，不能修改正式 wiki。

校验规则：

- proposal frontmatter 必须存在。
- `status` 必须是 `pending`。
- `operation` 必须合法。
- `target` 必须合法，不能逃逸出项目目录。
- `sources` 必须非空。
- `## Proposed Change` 或 `## 建议修改` 必须非空。
- `## Citations` 或 `## 引用` 必须非空。
- citations 中的路径必须存在。
- `append_section` 的目标页面必须存在，并且包含 `## 来源`。
- `create_page` 的目标页面不能已存在，并且 Proposed Change 必须是完整页面。

用户可以在 `propose` 后手动编辑 `proposals/pending/xxx.md`。`apply` 必须重新计算当前 proposal hash，并记录 `edited_after_generation`。

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
page_type: concept
sources:
  - wiki/sources/karpathy-llm-wiki.md
  - wiki/queries/llm-wiki-vs-rag.md
generated_by: deepseek
generated_at: 2026-06-12T10:00:00+08:00
proposal_sha256: abc123
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

`append_section` 规则：

- `apply` 将 `## Proposed Change` 或 `## 建议修改` 中的 Markdown 内容追加到目标页面的 `## 来源` 之前。
- 如果目标页面缺少 `## 来源`，`apply` 拒绝执行。
- `append_section` 不允许 LLM 指定任意插入位置。

`create_page` 规则：

- LLM 可以建议 `target`，但 `apply` 必须验证路径是否合法。
- `concept` 只能创建在 `wiki/concepts/`。
- `entity` 只能创建在 `wiki/entities/`。
- `synthesis` 只能创建在 `wiki/synthesis/`。
- `query` 只能创建在 `wiki/queries/`。
- `source` 页面不能由普通 proposal 创建，只能由 `ingest` 创建。
- `target` 文件已存在时，`apply` 拒绝执行。
- `## Proposed Change` 必须包含完整页面内容，包括 frontmatter、一级标题和 `## 来源`。
- Proposed Change 中 frontmatter 的 `type` 必须和 proposal 的 `page_type` 一致。

proposal 可以由用户手动编辑，这是人工确认写回流程的一部分。`apply` 必须基于当前 proposal 文件内容执行，而不是基于 LLM 原始输出执行。

为记录用户是否编辑过 proposal，`propose` 创建文件后必须写入 `proposal_sha256`。`apply` 前重新计算当前 proposal 内容 hash，并写入 `applied_sha256`。

如果 `applied_sha256 != proposal_sha256`，说明 proposal 在生成后被用户编辑过。`apply` 成功后，移动到 `proposals/applied/` 的 proposal frontmatter 必须更新：

```yaml
status: applied
applied_at: 2026-06-12T12:30:00+08:00
applied_sha256: def456
edited_after_generation: true
```

`wiki/log.md` 必须记录：

```markdown
- 2026-06-12T12:30:00+08:00 apply proposal
  - proposal: proposals/applied/2026-06-12-llm-wiki-vs-rag.md
  - target: wiki/concepts/LLM-Wiki.md
  - operation: append_section
  - edited_after_generation: true
  - proposal_sha256: abc123
  - applied_sha256: def456
```

如果用户没有编辑过 proposal，`edited_after_generation` 记录为 `false`。

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
