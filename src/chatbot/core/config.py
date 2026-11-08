"""应用配置。

所有可变参数集中在 Settings 中，通过 CHATBOT_* 环境变量或 .env 文件覆盖，
代码中不出现任何硬编码的密钥或可变参数。
"""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从环境变量（前缀 CHATBOT_）与 .env 文件读取的运行配置。"""

    model_config = SettingsConfigDict(
        env_prefix="CHATBOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr = Field(description="大模型服务 API Key，仅在发起请求时解密使用")
    base_url: str = Field(default="https://api.openai.com/v1", description="OpenAI 兼容接口地址")
    model: str = Field(default="gpt-4o-mini", description="模型名称")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="采样温度，取值 0~2")
    system_prompt: str = Field(default="你是一个乐于助人的中文助手。", description="系统提示词")
    max_history_messages: int = Field(
        default=20, ge=2, description="最多保留的历史消息条数（含 system 消息）"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """返回进程内单例配置。

    测试中修改环境变量后需调用 ``get_settings.cache_clear()`` 再取配置，
    避免模块级缓存导致断言用到旧值。
    """
    return Settings()
