# 智能式AI对话机器人

用 Python 编写的大模型对话程序：既可以在命令行里聊天，也可以作为 FastAPI 服务提供 HTTP 接口，支持多轮会话管理与后续的流式输出。

配置统一由 `config.py` + `pydantic-settings` 管理，所有可变参数均可通过 `.env` 覆盖，代码中不硬编码任何密钥。

## 目录结构

```
cli-chatbot/
├── config.py            # 配置模型与 get_settings()
├── llm.py               # 大模型调用封装（普通请求与流式请求）
├── sessions.py          # 会话存储（内存实现，读写集中在此模块）
├── schemas.py           # 请求 / 响应模型
├── app.py               # FastAPI 服务入口
├── chat.py              # 命令行入口
├── static/index.html    # 网页版聊天界面
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

## 快速开始

```bash
py -m pip install -r requirements.txt
copy .env.example .env    # 填入 CHATBOT_API_KEY
py chat.py
```

对话示例：

```
命令行对话机器人（模型 gpt-4o-mini），输入 exit 退出。
你：你好，帮我写一个 Python 冒泡排序
AI：...
你：exit
再见。
```

回复边生成边打印（`stream=True`），结束后只补一个换行，不会出现空行堆积。

## HTTP 服务（FastAPI）

启动服务：

```bash
py -m uvicorn app:app --host 127.0.0.1 --port 8000
```

启动后：

- 打开 http://127.0.0.1:8000 是网页版聊天界面：左侧会话列表、流式输出、Enter 发送、可新建/切换/删除会话
- 打开 http://127.0.0.1:8000/docs 是自动生成的交互式接口文档

网页界面只是前端外壳，对话、历史、流式全部调用下面同一套 HTTP 接口。

### 普通对话 `POST /chat`

```bash
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"u1\",\"message\":\"你好\"}"
```

```json
{"session_id":"u1","reply":"模型的回复"}
```

`session_id` 由调用方提供；第一次使用该 ID 时创建会话，之后同一 ID 的请求会自动带上历史。
不同 `session_id` 的会话互不影响。空消息返回 `400`。

### 会话管理

| 接口 | 作用 |
| --- | --- |
| `GET /sessions` | 查看已有会话 ID 列表，返回 `{"sessions":["u1"]}` |
| `GET /sessions/{session_id}/messages` | 按对话顺序返回消息记录 `{"session_id":"u1","messages":[{"role":"user","content":"你好"}]}` |
| `DELETE /sessions/{session_id}` | 清空该会话，成功返回 `204` |

会话不存在时 `GET` / `DELETE` 返回 `404`。目前会话保存在内存中，读写集中在 `sessions.py`，后续可替换为数据库实现而不影响接口层。

### 流式对话 `POST /chat/stream`

请求体与 `/chat` 相同，响应为逐块返回的纯文本，调用模型时使用 `stream=True`：

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"session_id\":\"u1\",\"message\":\"用一句话介绍 Python\"}"
```

返回内容按生成顺序到达（`Content-Type: text/plain; charset=utf-8`）。流式输出结束后，完整的用户消息与助手回复会在同一会话里留存，之后用 `GET /sessions/u1/messages` 可以看到。

### 学习功能：单词讲解 `POST /study/word`

```bash
curl -X POST http://127.0.0.1:8000/study/word ^
  -H "Content-Type: application/json" ^
  -d "{\"word\":\"apple\"}"
```

```json
{
  "word": "apple",
  "explanation": "n. 苹果；例句：She ate an apple after lunch.（她午饭后吃了一个苹果。）"
}
```

接口会把单词交给模型，按「词性 + 中文释义 + 英文例句（含中文翻译）」的格式作答，适合前端做单词卡片或学习面板。

## 单元测试

测试使用 `pytest` + FastAPI `TestClient`，通过 `app.dependency_overrides` 注入假模型客户端，覆盖全部 HTTP 接口。

```bash
py -m pip install -r requirements-dev.txt
py -m pytest -q
py -m ruff check .
```

| 文件 | 覆盖内容 |
| --- | --- |
| `tests/test_config.py` | 默认值解析；`CHATBOT_TEMPERATURE=5` 抛 `ValidationError`；`SecretStr` 打印不出现明文 |
| `tests/test_llm.py` | 假客户端断言传给模型的 `model`、`temperature`、`messages` 结构与 `stream=True`；增量文本拼接 |
| `tests/test_api_chat.py` | 同一会话连续对话；不同会话历史互不混用；单词讲解可调用；空消息返回 400 |
| `tests/test_api_sessions.py` | 会话列表与消息记录；清空后不再返回原记录；不存在的会话返回 404 |
| `tests/test_api_stream.py` | 模型收到 `stream=True`；流式内容逐块返回；完整回复写入历史 |
