"""大模型调用封装。

把「请求参数如何构造」和「如何调用客户端」收拢在这一层，
命令行入口只关心业务流程，替换模型服务或调整流式细节时改动集中在此。
"""

from collections.abc import Iterator
from typing import Any

from openai import OpenAI

from chatbot.core.config import Settings


def create_client(settings: Settings) -> OpenAI:
    """按配置创建 OpenAI 兼容客户端（DeepSeek、ModelScope 等同源接口均可直接使用）。"""
    return OpenAI(
        api_key=settings.api_key.get_secret_value(),
        base_url=settings.base_url,
    )


def build_request_params(
    messages: list[dict[str, str]], settings: Settings, stream: bool = True
) -> dict[str, Any]:
    """构造 chat.completions 请求参数，模型名、温度与是否流式全部来自约定。"""
    return {
        "model": settings.model,
        "temperature": settings.temperature,
        "messages": messages,
        "stream": stream,
    }


def chat_reply(
    client: OpenAI, messages: list[dict[str, str]], settings: Settings
) -> str:
    """发起非流式请求，一次性取回完整回复。"""
    response = client.chat.completions.create(
        **build_request_params(messages, settings, stream=False)
    )
    return response.choices[0].message.content or ""


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


WORD_EXPLAIN_PROMPT = (
    "你是一位英语老师。请用中文讲解用户给出的英语单词："
    "先给出词性与中文释义，再用该单词造一个英文例句并附中文翻译。回答控制在 5 行以内。"
)


def word_explain_messages(word: str) -> list[dict[str, str]]:
    """构造「单词讲解」学习功能的请求消息。"""
    return [
        {"role": "system", "content": WORD_EXPLAIN_PROMPT},
        {"role": "user", "content": f"请讲解这个单词：{word}"},
    ]

