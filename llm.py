"""大模型调用封装。

把「请求参数如何构造」和「如何调用客户端」收拢在这一层，
命令行入口只关心业务流程，后续替换模型服务或改为流式输出时改动集中在此。
"""

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
    """构造 chat.completions 请求参数，模型名与温度全部来自配置。"""
    return {
        "model": settings.model,
        "temperature": settings.temperature,
        "messages": messages,
        "stream": False,
    }


def chat_reply(client: OpenAI, messages: list[dict[str, str]], settings: Settings) -> str:
    """发送一次请求并返回完整回复文本。"""
    response = client.chat.completions.create(**build_request_params(messages, settings))
    return response.choices[0].message.content or ""
