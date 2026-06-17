from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .config import AppConfig, DEFAULT_CONFIG
from .errors import DeepSeekUnavailableError
from .init import InitContent


@dataclass(frozen=True)
class DeepSeekClient:
    api_key: str
    config: AppConfig = DEFAULT_CONFIG
    chat_model_factory: Callable[[], Any] | None = None

    @classmethod
    def from_environment(cls, config: AppConfig = DEFAULT_CONFIG) -> "DeepSeekClient":
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise DeepSeekUnavailableError("DEEPSEEK_API_KEY is not set")
        return cls(api_key=api_key, config=config)

    def generate_init_content(self, name: str, description: str) -> InitContent:
        prompt = _build_init_prompt(name, description)
        model = self._chat_model()
        try:
            response = model.invoke(
                [
                    SystemMessage(content="你是本地 Markdown LLM Wiki 初始化助手。只输出 JSON。"),
                    HumanMessage(content=prompt),
                ]
            )
        except Exception as exc:
            raise DeepSeekUnavailableError(f"DeepSeek init generation failed: {exc}") from exc

        return _parse_init_content(str(response.content))

    def generate_ingest_summary(self, request: Any) -> str:
        prompt = _build_ingest_summary_prompt(request)
        model = self._chat_model()
        try:
            response = model.invoke(
                [
                    SystemMessage(content="你是本地 Markdown LLM Wiki 的资料摄入助手。只输出 Markdown 摘要正文。"),
                    HumanMessage(content=prompt),
                ]
            )
        except Exception as exc:
            raise DeepSeekUnavailableError(f"DeepSeek ingest summary failed: {exc}") from exc

        return str(response.content).strip()

    def generate_ingest_extraction(self, request: Any) -> Any:
        prompt = _build_ingest_extraction_prompt(request)
        model = self._chat_model()
        try:
            response = model.invoke(
                [
                    SystemMessage(content="你是本地 Markdown LLM Wiki 的知识结构提取助手。只输出 JSON。"),
                    HumanMessage(content=prompt),
                ]
            )
        except Exception as exc:
            raise DeepSeekUnavailableError(f"DeepSeek ingest extraction failed: {exc}") from exc

        return _parse_ingest_extraction(str(response.content))

    def generate_ingest_overview(self, request: Any) -> str:
        prompt = _build_ingest_overview_prompt(request)
        model = self._chat_model()
        try:
            response = model.invoke(
                [
                    SystemMessage(content="你是本地 Markdown LLM Wiki 的项目概览撰写助手。只输出中文正文段落。"),
                    HumanMessage(content=prompt),
                ]
            )
        except Exception as exc:
            raise DeepSeekUnavailableError(f"DeepSeek ingest overview failed: {exc}") from exc

        return str(response.content).strip()

    def generate_query_answer(self, request: Any) -> str:
        prompt = _build_query_prompt(request)
        model = self._chat_model()
        try:
            response = model.invoke(
                [
                    SystemMessage(content="你是本地 Markdown LLM Wiki 的问答助手。必须基于给定上下文回答，并给出引用。"),
                    HumanMessage(content=prompt),
                ]
            )
        except Exception as exc:
            raise DeepSeekUnavailableError(f"DeepSeek query failed: {exc}") from exc

        return str(response.content).strip()

    def generate_query_answer_stream(self, request: Any, on_token: Callable[[str], None]) -> str:
        prompt = _build_query_prompt(request)
        model = self._chat_model()
        messages = [
            SystemMessage(content="你是本地 Markdown LLM Wiki 的问答助手。必须基于给定上下文回答，并给出引用。"),
            HumanMessage(content=prompt),
        ]
        chunks: list[str] = []
        try:
            for chunk in model.stream(messages):
                token = _content_to_text(getattr(chunk, "content", ""))
                if not token:
                    continue
                on_token(token)
                chunks.append(token)
        except Exception as exc:
            raise DeepSeekUnavailableError(f"DeepSeek query failed: {exc}") from exc

        return "".join(chunks).strip()

    def generate_proposal_writes(self, request: Any) -> Any:
        prompt = _build_proposal_prompt(request)
        model = self._chat_model()
        try:
            response = model.invoke(
                [
                    SystemMessage(content="你是本地 Markdown LLM Wiki 的知识沉淀助手。只输出 JSON。"),
                    HumanMessage(content=prompt),
                ]
            )
        except Exception as exc:
            raise DeepSeekUnavailableError(f"DeepSeek add generation failed: {exc}") from exc

        from .proposal import proposal_writes_from_json

        return proposal_writes_from_json(str(response.content))

    def merge_page_body(self, request: Any) -> str:
        prompt = _build_page_body_merge_prompt(request)
        model = self._chat_model()
        try:
            response = model.invoke(
                [
                    SystemMessage(content="你是本地 Markdown LLM Wiki 的页面合并助手。只输出合并后的 Markdown 正文。"),
                    HumanMessage(content=prompt),
                ]
            )
        except Exception as exc:
            raise DeepSeekUnavailableError(f"DeepSeek page merge failed: {exc}") from exc

        return str(response.content).strip()

    def _chat_model(self) -> Any:
        if self.chat_model_factory is not None:
            return self.chat_model_factory()
        return ChatOpenAI(
            api_key=self.api_key,
            base_url=self.config.llm.base_url,
            model=self.config.llm.model,
            temperature=self.config.llm.temperature,
            max_completion_tokens=self.config.llm.max_tokens,
        )


def generate_init_content_with_deepseek(name: str, description: str) -> InitContent:
    return DeepSeekClient.from_environment().generate_init_content(name, description)


def generate_ingest_summary_with_deepseek(request: Any) -> str:
    return DeepSeekClient.from_environment().generate_ingest_summary(request)


def generate_ingest_extraction_with_deepseek(request: Any) -> Any:
    return DeepSeekClient.from_environment().generate_ingest_extraction(request)


def generate_ingest_overview_with_deepseek(request: Any) -> str:
    return DeepSeekClient.from_environment().generate_ingest_overview(request)


def generate_query_answer_with_deepseek(request: Any) -> str:
    return DeepSeekClient.from_environment().generate_query_answer(request)


def generate_query_answer_stream_with_deepseek(request: Any, on_token: Callable[[str], None]) -> str:
    return DeepSeekClient.from_environment().generate_query_answer_stream(request, on_token)


def generate_proposal_writes_with_deepseek(request: Any) -> Any:
    return DeepSeekClient.from_environment().generate_proposal_writes(request)


def merge_page_body_with_deepseek(request: Any) -> str:
    return DeepSeekClient.from_environment().merge_page_body(request)


def _build_init_prompt(name: str, description: str) -> str:
    return f"""请为一个本地优先、Markdown 优先的 LLM Wiki 项目生成初始化 purpose.md。

项目名称：{name}
项目描述：{description}

请只输出 JSON，格式如下：
{{
  "purpose": "完整 purpose.md Markdown 内容"
}}

要求：
- 使用中文。
- 内容应简洁、可读、适合长期维护。
- purpose.md 应描述项目目标、关键问题、范围、非范围和当前工作假设。
- 不要输出 Markdown 代码围栏。
"""


def _build_ingest_summary_prompt(request: Any) -> str:
    if request.document_kind == "long":
        content = "\n\n".join(
            f"### Chunk {index}\n\n{chunk}" for index, chunk in enumerate(request.chunks, start=1)
        )
        mode_instruction = "这是一篇长 Markdown。请先综合所有 chunk，再生成最终 source summary。"
    else:
        content = request.source_text
        mode_instruction = "这是一篇短/中等长度 Markdown。请直接基于全文生成 source summary。"

    return f"""请为 LLM Wiki 的 source 页面生成中文摘要。

来源路径：`{request.source_path}`
文档类型：{request.document_kind}
目标长度：不超过约 {request.target_summary_limit} 个中文字符

要求：
- 保留事实，不要编造来源中没有的信息。
- 使用 Markdown。
- 摘要应该适合放入 `wiki/sources/` 页面。
- 可以包含简短的关键点列表。
- 不要输出代码围栏。

{mode_instruction}

Markdown 内容：

{content}
"""


def _build_ingest_extraction_prompt(request: Any) -> str:
    content = "\n\n".join(
        f"### Chunk {index}\n\n{chunk}" for index, chunk in enumerate(request.chunks, start=1)
    )
    return f"""请从这份 Markdown 资料中提取适合进入 LLM Wiki 的知识结构。

来源路径：`{request.source_path}`

已有 source summary：
{request.summary}

项目目的：
{request.purpose}

Wiki 协议：
{request.schema}

已有 wiki/index.md：
{request.index}

已有 wiki/overview.md：
{request.overview}

请只输出 JSON，不要输出 Markdown 代码围栏。格式如下：
{{
  "concepts": [
    {{
      "title": "概念名",
      "summary": "概念的事实性说明",
      "key_points": ["概念的核心要点"],
      "usage_contexts": ["概念在来源中的使用场景"],
      "confusions": ["容易混淆或需要边界说明的点"],
      "related": ["相关概念或实体"]
    }}
  ],
  "entities": [
    {{
      "title": "实体名",
      "category": "person|organization|tool|model|project|paper|other",
      "summary": "实体的事实性说明",
      "role": "实体在来源中扮演的角色或类型",
      "facts": ["关于该实体的可支撑事实"],
      "wiki_relevance": "该实体与本 Wiki 主题的关系",
      "related": ["相关概念或实体"]
    }}
  ]
}}

要求：
- 只提取来源中明确出现或能直接支撑的内容。
- title 要短，适合成为 Markdown 页面标题。
- summary 使用中文，避免编造。
- 概念页面尽量提供 2-5 个 key_points、1-3 个 usage_contexts；只有来源中支持时才提供 confusions。
- 实体页面尽量提供 role、2-5 个 facts、wiki_relevance。
- related 使用标题文本，不要使用文件路径。
- 如果没有合适内容，返回空数组。

Markdown 内容：
{content}
"""


def _build_ingest_overview_prompt(request: Any) -> str:
    summaries = "\n\n".join(
        f"### Source Summary {index}\n{summary}" for index, summary in enumerate(request.source_summaries, start=1)
    )
    concepts = "\n".join(f"- {title}" for title in request.concepts) or "- 暂无"
    entities = "\n".join(f"- {title}" for title in request.entities) or "- 暂无"
    return f"""请基于已经生成好的 source summary，为 LLM Wiki 的 `wiki/overview.md` 写“项目概览”正文。

要求：
- 只介绍这个 Wiki 项目主要在研究、记录或沉淀什么。
- 不要复述来源数量、概念数量、实体数量等规模统计。
- 不要输出 Markdown 标题、列表、代码围栏或 frontmatter。
- 使用中文，保持事实性，不要编造 source summary 中没有的信息。
- 输出 1 到 2 个自然段。

已生成的 source summary：
{summaries}

已抽取的概念标题：
{concepts}

已抽取的实体标题：
{entities}
"""


def _build_query_prompt(request: Any) -> str:
    context = "\n\n".join(
        f"### {page.path}\nTitle: {page.title}\n\n{page.content}"
        for page in request.context_pages
    )
    return f"""请基于本地 LLM Wiki 上下文回答问题。

问题：
{request.question}

项目目的：
{request.purpose}

Wiki 协议：
{request.schema}

要求：
- 默认使用中文回答。
- 只能使用 Context 中出现的信息作为事实依据。
- 如果 Context 证据不足，请明确说明“当前 wiki 证据不足”。
- 不要编造不存在的文件路径、标题或引用。
- 回答末尾必须包含 `## Sources`，并列出引用路径。
- 引用路径只能来自 Context 标题中的路径，可以带 heading。

Context:
{context}
"""


def _build_proposal_prompt(request: Any) -> str:
    citations = "\n".join(f"- {citation}" for citation in request.citations) or "- none"
    context_pages = "\n".join(f"- {page}" for page in request.context_pages) or "- none"
    candidate_pages = "\n\n".join(
        f"### {page.path}\nTitle: {page.title}\n\n{page.content}" for page in request.candidate_pages
    ) or "暂无候选长期知识页面。"
    return f"""请把用户已经决定沉淀的上一次问答整理成 LLM Wiki 写入计划。

用户沉淀指令：
{request.instruction}

上一次用户问题：
{request.question}

上一次大模型回答：
{request.answer}

上一次回答引用：
{citations}

上一次上下文页面：
{context_pages}

候选已有长期知识页面：
{candidate_pages}

项目目的：
{request.purpose}

Wiki 协议：
{request.schema}

请只输出 JSON，不要输出 Markdown 代码围栏。格式如下：
{{
  "writes": [
    {{
      "path": "wiki/concepts/example.md",
      "page_type": "concept",
      "title": "页面标题",
      "content": "完整 Markdown 正文，可以包含 frontmatter；如果不含 frontmatter，程序会补齐"
    }}
  ]
}}

规则：
- 原始用户问题和大模型回答已经由程序保存到 `wiki/queries/`。
- 请先判断这次问答是否包含值得进入长期知识页的新信息。
- 如果有新信息，应优先补充或更新已有页面；只有现有页面无法自然承载时，才创建新页面。
- 如果与已有长期知识重复度过高，且没有新的概念、边界、例子、流程或结论，则不要写入长期知识页，返回空 writes：`{{"writes":[]}}`。
- 不要写入 `wiki/sources/`；对话沉淀不是外部原始资料。
- path 只能在 `wiki/concepts/`、`wiki/entities/`、`wiki/synthesis/` 下。
- 文件名要短、可读、适合长期维护。
- 内容必须基于上一次问答和引用，不要编造额外事实。
"""


def _build_page_body_merge_prompt(request: Any) -> str:
    # frontmatter 已由本地确定性逻辑合并，这里只让模型处理正文语义。
    return f"""请合并一个 LLM Wiki 页面正文。

页面标题：{request.title}
页面类型：{request.page_type}

已有正文：
{request.existing_body}

新增正文：
{request.incoming_body}

要求：
- 只输出合并后的 Markdown 正文，不要输出 YAML frontmatter。
- 保留已有正文中仍然有效的信息。
- 将新增正文自然融合进合适章节，不要机械追加重复段落。
- 如果两边有重复内容，只保留更清晰的一版。
- 不要编造已有正文和新增正文之外的事实。
- 保留一级标题。
"""


def _parse_ingest_extraction(content: str) -> Any:
    from .ingest import ExtractedConcept, ExtractedEntity, IngestExtraction

    text = content.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
        concepts = [
            ExtractedConcept(
                title=str(item["title"]),
                summary=str(item.get("summary", "")),
                related=[str(value) for value in item.get("related", [])],
                key_points=[str(value) for value in item.get("key_points", [])],
                usage_contexts=[str(value) for value in item.get("usage_contexts", [])],
                confusions=[str(value) for value in item.get("confusions", [])],
            )
            for item in data.get("concepts", [])
        ]
        entities = [
            ExtractedEntity(
                title=str(item["title"]),
                category=str(item.get("category", "other")),
                summary=str(item.get("summary", "")),
                related=[str(value) for value in item.get("related", [])],
                role=str(item.get("role", "")),
                facts=[str(value) for value in item.get("facts", [])],
                wiki_relevance=str(item.get("wiki_relevance", "")),
            )
            for item in data.get("entities", [])
        ]
        return IngestExtraction(concepts=concepts, entities=entities)
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise DeepSeekUnavailableError("DeepSeek returned invalid ingest extraction") from exc


def _parse_init_content(content: str) -> InitContent:
    text = content.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
        return InitContent(
            purpose=str(data["purpose"]),
        )
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise DeepSeekUnavailableError("DeepSeek returned invalid init content") from exc


def _content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text is not None:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)
