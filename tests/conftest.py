"""测试公共夹具：假模型客户端与已替换依赖的 TestClient。"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from chatbot.api.app import app, get_client
from chatbot.core.config import get_settings
from chatbot.repositories.session_store import store


class FakeChatClient:
    """替代真实 OpenAI 客户端，记录每次请求参数并返回预设内容。"""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.reply = "模型回复"
        self.pieces = ["模型", "回复"]
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs.get("stream"):
            return iter(
                [
                    SimpleNamespace(
                        choices=[SimpleNamespace(delta=SimpleNamespace(content=piece))]
                    )
                    for piece in self.pieces
                ]
            )
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply))]
        )


@pytest.fixture(autouse=True)
def offline_env(monkeypatch, tmp_path):
    """为每个用例提供假密钥，避免读取真实 .env 或联网。"""
    monkeypatch.setenv("CHATBOT_API_KEY", "test-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_client() -> FakeChatClient:
    return FakeChatClient()


@pytest.fixture
def api(fake_client: FakeChatClient):
    """替换模型客户端依赖，并在用例前后清空内存会话，保证互不影响。"""
    app.dependency_overrides[get_client] = lambda: fake_client
    store.clear_all()
    with TestClient(app) as client:
        yield client
    store.clear_all()
    app.dependency_overrides.clear()
