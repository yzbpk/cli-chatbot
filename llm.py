"""大模型调用封装。

把「请求参数如何构造」和「如何调用客户端」收拢在这一层，
命令行入口只关心业务流程，替换模型服务或调整流式细节时改动集中在此。
"""

from collections.abc import Iterator
from typing import Any

from openai import OpenAI

from config import Settings


def create_client(settings: Settings) -> OpenAI:
    """按配置创建 OpenAI 兼容客户端（DeepSeek、ModelScope 等同源接口均可直接使用）。"""
    return OpenAI(
        api_key=settings.api_key.get_secret_value(),
        base_url=settings.base_url,
    )


def build_request_params(messages: list[dict[str, str]], settings: Settings) -> dict[str, Any]:
    """构造 chat.completions 请求参数，模型名、温度与是否流式全部来自约定。"""
    return {
        "model": settings.model,
        "temperature": settings.temperature,
        "messages": messages,
        "stream": True,
    }


def stream_reply(
    client: OpenAI, messages: list[dict[str, str]], settings: Settings
) -> Iterator[str]:
    """发起流式请求，按到达顺序逐段产出增量文本。"""
    stream = client.chat.completions.create(**build_request_params(messages, settings))
    for chunk in stream:
        if not chunk.choices:  # 部分服务会发只带 usage 的空 chunk
            continue
        content = chunk.choices[0].delta.content
        if content:
            yield content
