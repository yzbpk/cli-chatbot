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

> 快速开始与配置说明随功能开发补充。
