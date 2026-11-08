"""测试公共夹具：假模型客户端、临时数据库与已替换依赖的 TestClient。"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from chatbot.api.app import app, get_client, get_store
from chatbot.core.config import get_settings
from chatbot.repositories.session_store import SessionStore


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
    """为每个用例提供假密钥和独立数据库，避免读取真实 .env 或联网。"""
    monkeypatch.setenv("CHATBOT_API_KEY", "test-key")
    monkeypatch.setenv("CHATBOT_DB_PATH", str(tmp_path / "settings.db"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_client() -> FakeChatClient:
    return FakeChatClient()


@pytest.fixture
def store(tmp_path) -> SessionStore:
    """每个用例一份全新的数据库，用例之间互不影响。"""
    return SessionStore(tmp_path / "api.db")


@pytest.fixture
def api(fake_client: FakeChatClient, store: SessionStore):
    """替换模型客户端与会话存储依赖，返回可直接发请求的 TestClient。"""
    app.dependency_overrides[get_client] = lambda: fake_client
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
