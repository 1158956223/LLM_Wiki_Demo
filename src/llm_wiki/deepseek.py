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

    def _chat_model(self) -> Any:
        if self.chat_model_factory is not None:
            return self.chat_model_factory()
        return ChatOpenAI(
            api_key=self.api_key,
            base_url=self.config.llm.base_url,
            model=self.config.llm.model,
            temperature=self.config.llm.temperature,
            max_completion_tokens=self.config.llm.max_tokens,
            timeout=30,
        )


def generate_init_content_with_deepseek(name: str, description: str) -> InitContent:
    return DeepSeekClient.from_environment().generate_init_content(name, description)


def generate_ingest_summary_with_deepseek(request: Any) -> str:
    return DeepSeekClient.from_environment().generate_ingest_summary(request)


def generate_ingest_extraction_with_deepseek(request: Any) -> Any:
    return DeepSeekClient.from_environment().generate_ingest_extraction(request)


def generate_ingest_overview_with_deepseek(request: Any) -> str:
    return DeepSeekClient.from_environment().generate_ingest_overview(request)


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

请只输出 JSON，不要输出 Markdown 代码围栏。格式如下：
{{
  "concepts": [
    {{
      "title": "概念名",
      "summary": "概念的事实性说明",
      "related": ["相关概念或实体"]
    }}
  ],
  "entities": [
    {{
      "title": "实体名",
      "category": "person|organization|tool|model|project|paper|other",
      "summary": "实体的事实性说明",
      "related": ["相关概念或实体"]
    }}
  ]
}}

要求：
- 只提取来源中明确出现或能直接支撑的内容。
- title 要短，适合成为 Markdown 页面标题。
- summary 使用中文，避免编造。
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
            )
            for item in data.get("concepts", [])
        ]
        entities = [
            ExtractedEntity(
                title=str(item["title"]),
                category=str(item.get("category", "other")),
                summary=str(item.get("summary", "")),
                related=[str(value) for value in item.get("related", [])],
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
