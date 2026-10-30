"""config.py 离线单元测试：默认值、温度校验与 SecretStr 脱敏。"""

import os

import pytest
from pydantic import ValidationError

from config import get_settings


@pytest.fixture(autouse=True)
def clean_env(tmp_path, monkeypatch):
    """切到临时目录，避免本地 .env 干扰；用例前后清空 lru_cache。"""
    monkeypatch.chdir(tmp_path)
    for key in list(os.environ):
        if key.startswith("CHATBOT_"):
            monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults(monkeypatch):
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test")
    settings = get_settings()

    assert settings.base_url == "https://api.openai.com/v1"
    assert settings.model == "gpt-4o-mini"
    assert settings.temperature == 0.7
    assert settings.system_prompt == "你是一个乐于助人的中文助手。"
    assert settings.max_history_messages == 20


def test_temperature_out_of_range(monkeypatch):
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test")
    monkeypatch.setenv("CHATBOT_TEMPERATURE", "5")

    with pytest.raises(ValidationError) as exc_info:
        get_settings()

    assert "temperature" in str(exc_info.value)


def test_api_key_never_printed_in_plaintext(monkeypatch):
    monkeypatch.setenv("CHATBOT_API_KEY", "sk-test-secret")

    settings = get_settings()

    assert settings.api_key.get_secret_value() == "sk-test-secret"
    assert "sk-test-secret" not in str(settings)
    assert "sk-test-secret" not in repr(settings)
