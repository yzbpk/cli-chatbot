# CLI 对话机器人

用 Python 编写的命令行聊天机器人，支持连续多轮对话与流式输出。

配置统一由 `config.py` + `pydantic-settings` 管理，所有可变参数均可通过 `.env` 覆盖，代码中不硬编码任何密钥。

## 目录结构

```
cli-chatbot/
├── config.py            # 配置模型与 get_settings()
├── llm.py               # 大模型调用封装
├── chat.py              # 命令行入口
├── tests/               # pytest 单元测试（离线运行）
├── .env.example         # 环境变量示例
├── requirements.txt     # 运行依赖
└── requirements-dev.txt # 开发与测试依赖
```

## 配置说明

所有可变参数都定义在 `config.py` 的 `Settings` 里，运行时通过 `CHATBOT_*` 环境变量或 `.env` 覆盖，代码中不硬编码。

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `CHATBOT_API_KEY` | 无（必填） | 大模型服务 API Key，使用 `SecretStr` 接收，打印配置时自动脱敏 |
| `CHATBOT_BASE_URL` | `https://api.openai.com/v1` | OpenAI 兼容接口地址 |
| `CHATBOT_MODEL` | `gpt-4o-mini` | 模型名称 |
| `CHATBOT_TEMPERATURE` | `0.7` | 采样温度，超出 0~2 抛 `ValidationError` |
| `CHATBOT_SYSTEM_PROMPT` | `你是一个乐于助人的中文助手。` | 系统提示词 |
| `CHATBOT_MAX_HISTORY_MESSAGES` | `20` | 最多保留的历史消息条数（含 system） |

```bash
cp .env.example .env   # Windows: copy .env.example .env
# 编辑 .env，填入 CHATBOT_API_KEY
```
