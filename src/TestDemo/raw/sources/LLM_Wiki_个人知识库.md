# 卡帕西个人知识库

## 1. 背景

指 Andrej Karpathy 提到的一种 **LLM Wiki / LLM Knowledge Base** 思路。

它的核心不是简单地把文档放进向量数据库，然后让大模型去检索，而是让大模型参与到知识库的长期建设中：

- 阅读原始资料
- 提炼核心内容
- 整理成结构化 Wiki
- 维护页面之间的链接
- 发现重复、冲突、过时内容
- 将新的问答结果继续沉淀回知识库

因此，它更像是一个 **由 LLM 辅助维护的长期知识管理系统**，而不仅仅是一个普通的问答系统。

------

## 2. 传统 RAG 是什么

RAG，全称是 Retrieval-Augmented Generation，即“检索增强生成”。

它的一般流程如下：

```text
原始文档
   ↓
文档切分 Chunk
   ↓
向量化 Embedding
   ↓
存入向量数据库
   ↓
用户提问
   ↓
检索相关 Chunk
   ↓
把 Chunk 放入上下文
   ↓
LLM 生成答案
```

简单来说，RAG 的核心是：

> 用户提出问题后，系统从知识库中检索相关文档片段，再交给大模型生成答案。

例如用户问：

```text
LangGraph 中什么时候需要使用 checkpoint？
```

传统 RAG 可能会从文档中检索出几个相关片段：

```text
chunk_01：checkpoint 可以保存图状态
chunk_02：thread_id 用于恢复对话
chunk_03：durable execution 依赖持久化机制
```

然后大模型基于这些片段临时组织回答。

------

## 3. LLM Wiki 是什么

LLM Wiki 可以理解为一种由大模型辅助维护的结构化知识库。

它不是直接把原始文档切块后检索，而是先让 LLM 对原始资料进行整理，生成长期可维护的 Wiki 页面。

它的流程可以理解为：

```text
原始资料
   ↓
LLM 阅读、总结、归纳
   ↓
生成结构化 Wiki 页面
   ↓
维护目录、链接、概念关系
   ↓
用户提问
   ↓
检索相关 Wiki 页面
   ↓
LLM 基于 Wiki 生成答案
   ↓
重要结论继续写回 Wiki
```

例如，LLM Wiki 可能会提前整理出这样的页面：

```text
wiki/
├── index.md
├── langgraph-overview.md
├── checkpoint.md
├── durable-execution.md
├── human-in-the-loop.md
└── ai-customer-service.md
```

当用户再问：

```text
AI 客服项目中什么时候需要 checkpoint？
```

系统检索到的就不再是零散的原始文档 chunk，而是已经整理好的知识页面，例如：

```markdown
# LangGraph Checkpoint

## 是什么

Checkpoint 是 LangGraph 中用于保存工作流状态的机制。

## 什么时候需要

1. 多轮对话需要保存上下文
2. human-in-the-loop 需要中断后恢复
3. 工作流失败后需要重试
4. 用户确认、审批、支付等关键节点需要保存状态

## 在 AI 客服中的应用

AI 客服系统中，以下场景建议使用 checkpoint：

- 用户咨询过程需要跨轮记忆
- 人工客服介入后需要恢复上下文
- 邮件分类、审批、回复草稿需要可追踪
- 工单流程中断后需要继续执行
```

------

## 4. LLM Wiki 的三层结构

卡帕西式知识库通常可以理解为三层结构：

```text
Raw Sources 原始资料层
        ↓
Wiki 结构化知识层
        ↓
Schema 规则约束层
```

这三层分别解决不同问题：

- Raw Sources 负责保存原始事实
- Wiki 负责沉淀结构化知识
- Schema 负责约束 LLM 如何维护知识库

------

### 4.1 Raw Sources：原始资料层

Raw Sources 是知识库的最底层，保存所有未经整理的原始资料。

这些资料可以包括：

```text
论文
网页
官方文档
项目文档
会议记录
课程笔记
代码说明
报错截图
聊天记录
PDF 文件
```

这一层的作用是提供事实来源，也就是知识库的 source of truth。

一般来说，Raw Sources 只读不改。
LLM 可以读取这些资料，但不应该随意修改原始资料。

例如：

```text
raw/
├── docs/
│   ├── langgraph_persistence.md
│   ├── langgraph_durable_execution.md
│   └── langgraph_event_streaming.md
├── papers/
├── notes/
└── screenshots/
```

它的核心作用是：

> 保存原始材料，保证知识库中的结论可以追溯到来源。

------

### 4.2 Wiki：结构化知识层

Wiki 是知识库的核心层。

这一层不是简单保存原始文档，而是由 LLM 或人工对原始资料进行总结、归纳、重组后形成的结构化知识页面。

例如：

```text
wiki/
├── index.md
├── langgraph-overview.md
├── checkpoint.md
├── durable-execution.md
├── human-in-the-loop.md
└── ai-customer-service.md
```

Wiki 页面通常包含：

```text
概念解释
核心结论
使用场景
实践经验
常见问题
相关页面链接
与其他概念的对比
```

例如，关于 checkpoint 的 Wiki 页面可能会整理成：

```markdown
# LangGraph Checkpoint

## 是什么

Checkpoint 是 LangGraph 中保存工作流状态的机制。

## 什么时候需要

1. 多轮对话需要保存上下文
2. human-in-the-loop 需要中断后恢复
3. 工作流失败后需要重试
4. 用户确认、审批、支付等关键节点需要保存状态

## 在 AI 客服中的应用

AI 客服系统中，以下场景建议使用 checkpoint：

- 用户咨询过程需要跨轮记忆
- 人工客服介入后需要恢复上下文
- 邮件分类、审批、回复草稿需要可追踪
- 工单流程中断后需要继续执行
```

这一层的核心作用是：

> 把原始资料从“零散文档”整理成“长期可复用的知识资产”。

------

### 4.3 Schema：规则约束层

Schema 是知识库的规则层，用来告诉 LLM 应该如何维护这个知识库。

它可以规定：

```text
目录如何组织
文件如何命名
每个页面应该包含哪些部分
新资料进入后如何处理
回答问题时如何检索 Wiki
什么时候需要更新 index.md
什么时候需要记录 log.md
什么时候需要标注冲突或过时信息
```

在实际项目中，Schema 可以写在类似下面的文件中：

```text
AGENTS.md
CLAUDE.md
README.md
kb_rules.md
```

例如：

```markdown
# Knowledge Base Rules

你是这个知识库的维护 Agent。

## 目录规则

- raw/ 存放原始资料，不允许修改。
- wiki/ 存放结构化知识页面。
- wiki/index.md 是总目录。
- wiki/log.md 记录每次知识库更新。

## Ingest 规则

当用户导入新资料时：

1. 阅读 raw/ 中的新文件。
2. 提炼核心观点。
3. 更新相关 Wiki 页面。
4. 如果发现和旧资料冲突，需要标注。
5. 更新 index.md。
6. 在 log.md 中记录本次变更。

## Query 规则

当用户提问时：

1. 先读取 wiki/index.md。
2. 找到相关 Wiki 页面。
3. 基于 Wiki 页面回答。
4. 如果产生新的稳定结论，可以写回 Wiki。

## Lint 规则

定期检查：

- 是否有孤立页面
- 是否有重复内容
- 是否有过时结论
- 是否有缺少来源的断言
- 是否有页面之间的矛盾
```

这一层的核心作用是：

> 让 LLM 不是随意整理知识，而是按照固定规则持续维护知识库。

------

## 5. LLM Wiki 的三类核心操作

LLM Wiki 不只是静态文档集合，它还包含三个核心操作：

```text
Ingest：导入和整理资料
Query：检索和回答问题
Lint：检查和维护知识库质量
```

这三个操作构成了 LLM Wiki 的基本工作流。

------

### 5.1 Ingest：导入资料

Ingest 指的是把新资料导入知识库，并让 LLM 对其进行整理和沉淀。

传统知识库可能只是把文档上传进去，而 LLM Wiki 的 Ingest 更强调“理解和整合”。

它通常包括以下步骤：

```text
读取新资料
提炼核心内容
生成摘要
识别关键概念
更新已有 Wiki 页面
创建新的 Wiki 页面
更新 index.md
记录 log.md
标注冲突或不确定信息
```

例如，用户新增了一篇关于 LangGraph checkpoint 的文档，LLM 可能会更新：

```text
wiki/checkpoint.md
wiki/persistence.md
wiki/durable-execution.md
wiki/human-in-the-loop.md
wiki/index.md
wiki/log.md
```

Ingest 的核心价值是：

> 把新资料从“原始信息”转化成“可复用知识”。

------

### 5.2 Query：检索和回答问题

Query 指的是用户基于知识库进行提问，系统检索相关 Wiki 页面并生成答案。

流程可以理解为：

```text
用户提问
   ↓
读取 index.md
   ↓
定位相关 Wiki 页面
   ↓
检索相关内容
   ↓
LLM 生成答案
   ↓
必要时回查 Raw Sources
   ↓
重要结论写回 Wiki
```

例如用户问：

```text
AI 客服系统中什么时候需要使用 LangGraph checkpoint？
```

LLM 可以先检索：

```text
wiki/checkpoint.md
wiki/ai-customer-service.md
wiki/human-in-the-loop.md
```

然后综合生成答案。

Query 的核心价值是：

> 基于已经整理好的知识体系回答问题，而不是每次都从原始文档中临时拼接答案。

------

### 5.3 Lint：知识库质量检查

Lint 原本是代码开发中的概念，表示检查代码中是否存在潜在问题。

在 LLM Wiki 中，Lint 指的是对知识库进行质量检查和维护。

它可以检查：

```text
是否有重复页面
是否有孤立页面
是否有过时结论
是否有互相矛盾的内容
是否有缺少来源的断言
是否有页面命名不规范
是否有重要概念没有单独成页
是否有 index.md 没有及时更新
```

例如，知识库中可能同时存在：

```text
wiki/langgraph-checkpoint.md
wiki/checkpoint.md
wiki/persistence-checkpoint.md
```

Lint 操作就可以发现这些页面内容高度重复，并建议合并。

Lint 的核心价值是：

> 保证知识库长期保持清晰、一致、可维护，而不是越积累越混乱。

---

## 6. RAG 和 LLM Wiki 的共同点

RAG 和 LLM Wiki 都需要“检索”。

因为任何知识库想要回答问题，本质上都需要经历这个过程：

```text
用户问题
   ↓
找到相关知识
   ↓
放入上下文
   ↓
LLM 生成答案
```

所以从最高抽象层来看，它们都属于：

```text
Query → Retrieve Context → Generate Answer
```

也就是说，LLM Wiki 并不是不检索。
它同样需要根据用户问题找到相关知识，只不过它检索的对象和传统 RAG 不一样。

------

## 7. RAG 和 LLM Wiki 的核心区别

二者真正的区别不是“有没有检索”，而是：

> 检索的对象不同，知识的形态不同，知识的维护方式不同。

### 7.1 传统 RAG 检索的是原始文档切片

传统 RAG 通常检索的是：

```text
原始文档切分后的 chunk
```

这些 chunk 往往来自原始资料，例如官方文档、PDF、网页、代码注释等。

特点是：

- 粒度较细
- 上下文可能被切断
- 知识之间的关系较弱
- 更多依赖向量相似度
- 用户每次提问时临时检索和拼接答案

------

### 7.2 LLM Wiki 检索的是整理后的知识页面

LLM Wiki 检索的是：

```text
经过 LLM 或人工整理后的 Wiki 页面
```

这些页面通常已经包含：

- 主题总结
- 概念解释
- 使用场景
- 对比分析
- 实践经验
- 页面之间的链接
- 相关问题的沉淀

所以它的知识形态更加结构化。

------

## 8. 对比表格

| 对比维度         | 传统 RAG                 | LLM Wiki                           |
| ---------------- | ------------------------ | ---------------------------------- |
| 检索对象         | 原始文档切分后的 chunk   | 整理后的 Wiki 页面                 |
| 知识形态         | 碎片化片段               | 结构化知识                         |
| 处理时机         | 用户提问时临时检索       | 资料进入时先整理，提问时再检索     |
| 是否持续沉淀     | 通常不沉淀               | 可以持续更新 Wiki                  |
| 是否维护知识关系 | 较弱，主要靠向量相似度   | 较强，可以维护目录、链接、概念关系 |
| 适合场景         | 大规模文档问答、企业搜索 | 学习笔记、研究总结、项目知识沉淀   |
| 核心目标         | 找到相关文档片段         | 构建长期可维护的知识体系           |
| 系统性质         | 更像搜索系统             | 更像知识管理系统                   |

