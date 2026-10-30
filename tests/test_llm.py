"""llm.py 离线单元测试：假客户端断言请求参数与流式拼接。"""

import os
from types import SimpleNamespace

import pytest

from config import get_settings
from llm import build_request_params, stream_reply


class FakeCompletions:
    """记录调用参数并原样返回预置的 chunk 序列。"""

    def __init__(self, chunks):
        self.chunks = chunks
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return iter(self.chunks)


class FakeClient:
    def __init__(self, chunks):
        self.chat = SimpleNamespace(completions=FakeCompletions(chunks))


def make_chunk(content):
    """构造与 OpenAI 流式响应同结构的最小 chunk。"""
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


@pytest.fixture(autouse=True)
def settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for key in list(os.environ):
        if key.startswith("CHATBOT_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def build_messages(settings):
    return [
        {"role": "system", "content": settings.system_prompt},
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，有什么可以帮你？"},
        {"role": "user", "content": "再讲个笑话"},
    ]


def test_request_params_follow_settings(settings):
    messages = build_messages(settings)
    params = build_request_params(messages, settings)

    assert params["model"] == settings.model
    assert params["temperature"] == settings.temperature
    assert params["stream"] is True
    assert params["messages"] == messages


def test_stream_reply_sends_model_temperature_and_history(settings):
    messages = build_messages(settings)
    client = FakeClient([make_chunk("好的")])

    list(stream_reply(client, messages, settings))

    kwargs = client.chat.completions.calls[0]
    assert kwargs["model"] == settings.model
    assert kwargs["temperature"] == settings.temperature
    assert kwargs["stream"] is True
    assert kwargs["messages"][0] == {"role": "system", "content": settings.system_prompt}
    assert kwargs["messages"][-1] == {"role": "user", "content": "再讲个笑话"}


def test_stream_reply_yields_incremental_text(settings):
    messages = build_messages(settings)
    client = FakeClient([make_chunk("你"), make_chunk("好"), make_chunk(None)])

    pieces = list(stream_reply(client, messages, settings))

    assert pieces == ["你", "好"]
    assert "".join(pieces) == "你好"
