# 后端（FastAPI + SQLAlchemy）

## 启动

```bash
uv run uvicorn chatbot.api.app:app --port 8000
```

打开 http://127.0.0.1:8000 或 http://127.0.0.1:8000/docs。

## 测试

```bash
uv run pytest
```

## 配置

复制 `.env.example` 为 `.env`，填入你的 API key：

```bash
cp .env.example .env
```

**必须在 `backend/` 目录下执行以上命令。**
