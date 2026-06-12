from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import AppConfig, DEFAULT_CONFIG
from .errors import DeepSeekUnavailableError
from .init import InitContent


@dataclass(frozen=True)
class DeepSeekClient:
    api_key: str
    config: AppConfig = DEFAULT_CONFIG

    @classmethod
    def from_environment(cls, config: AppConfig = DEFAULT_CONFIG) -> "DeepSeekClient":
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise DeepSeekUnavailableError("DEEPSEEK_API_KEY is not set")
        return cls(api_key=api_key, config=config)

    def generate_init_content(self, name: str, description: str) -> InitContent:
        prompt = _build_init_prompt(name, description)
        payload = {
            "model": self.config.llm.model,
            "temperature": self.config.llm.temperature,
            "max_tokens": self.config.llm.max_tokens,
            "messages": [
                {"role": "system", "content": "你是本地 Markdown LLM Wiki 初始化助手。只输出 JSON。"},
                {"role": "user", "content": prompt},
            ],
        }
        request = urllib.request.Request(
            f"{self.config.llm.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise DeepSeekUnavailableError(f"DeepSeek init generation failed: {exc}") from exc

        content = data["choices"][0]["message"]["content"]
        return _parse_init_content(content)


def generate_init_content_with_deepseek(name: str, description: str) -> InitContent:
    return DeepSeekClient.from_environment().generate_init_content(name, description)


def _build_init_prompt(name: str, description: str) -> str:
    return f"""请为一个本地优先、Markdown 优先的 LLM Wiki 项目生成初始化文档。

项目名称：{name}
项目描述：{description}

请只输出 JSON，格式如下：
{{
  "purpose": "完整 purpose.md Markdown 内容",
  "schema": "完整 schema.md Markdown 内容",
  "overview": "完整 wiki/overview.md Markdown 内容"
}}

要求：
- 使用中文。
- 内容应简洁、可读、适合长期维护。
- 不要输出 Markdown 代码围栏。
"""


def _parse_init_content(content: str) -> InitContent:
    text = content.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
        return InitContent(
            purpose=str(data["purpose"]),
            schema=str(data["schema"]),
            overview=str(data["overview"]),
        )
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise DeepSeekUnavailableError("DeepSeek returned invalid init content") from exc
