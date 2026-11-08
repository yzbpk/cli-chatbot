"""FastAPI 服务入口：普通对话、流式对话、会话管理与学习功能。"""

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from chatbot.core.config import Settings, get_settings
from chatbot.models.schemas import (
    ChatRequest,
    ChatResponse,
    SessionList,
    SessionMessages,
    StudyWordRequest,
    StudyWordResponse,
)
from chatbot.repositories.session_store import SessionStore
from chatbot.services.llm import chat_reply, create_client, stream_reply, word_explain_messages

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="智能式AI对话机器人", version="0.4.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

SettingsDep = Annotated[Settings, Depends(get_settings)]


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """网页版聊天界面，前端调用与命令行相同的 /chat/stream 接口。"""
    return FileResponse(STATIC_DIR / "index.html")


def get_client(settings: SettingsDep) -> OpenAI:
    """按配置创建模型客户端，测试中通过 dependency_overrides 替换为假客户端。"""
    try:
        return create_client(settings)
    except ValidationError as exc:  # 缺少 CHATBOT_API_KEY 等必填配置
        raise HTTPException(
            status_code=503, detail="服务未配置模型密钥，请参考 .env.example 设置 CHATBOT_API_KEY。"
        ) from exc


ClientDep = Annotated[OpenAI, Depends(get_client)]


@lru_cache(maxsize=8)
def _store_for(db_path: str) -> SessionStore:
    """同一数据库路径复用同一个 store，避免每次请求重复建表。"""
    return SessionStore(db_path)


def get_store(settings: SettingsDep) -> SessionStore:
    """从配置解析数据库路径；测试通过 dependency_overrides 注入临时数据库。"""
    return _store_for(settings.db_path)


StoreDep = Annotated[SessionStore, Depends(get_store)]


def build_messages(
    settings: Settings, history: list[dict[str, str]], user_text: str
) -> list[dict[str, str]]:
    """拼装本轮请求：system 提示词 + 截断后的历史 + 当前用户消息。"""
    recent = history[-(settings.max_history_messages - 1) :]
    return [
        {"role": "system", "content": settings.system_prompt},
        *recent,
        {"role": "user", "content": user_text},
    ]


@app.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    settings: SettingsDep,
    client: ClientDep,
    store: StoreDep,
) -> ChatResponse:
    """普通对话接口：同一 session_id 自动延续历史，不同会话互不影响。"""
    text = payload.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="message 不能为空")

    history = store.get_messages(payload.session_id)
    messages = build_messages(settings, history, text)
    try:
        reply = chat_reply(client, messages, settings)
    except OpenAIError as exc:
        raise HTTPException(status_code=502, detail=f"模型调用失败：{exc}") from exc

    store.append(payload.session_id, "user", text)
    store.append(payload.session_id, "assistant", reply)
    store.trim(payload.session_id, settings.max_history_messages)
    return ChatResponse(session_id=payload.session_id, reply=reply)


@app.post("/chat/stream")
def chat_stream(
    payload: ChatRequest,
    settings: SettingsDep,
    client: ClientDep,
    store: StoreDep,
) -> StreamingResponse:
    """流式对话接口：边生成边返回，结束后把完整回复写入会话历史。"""
    text = payload.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="message 不能为空")

    history = store.get_messages(payload.session_id)
    messages = build_messages(settings, history, text)

    def generate() -> Iterator[str]:
        answer: list[str] = []
        try:
            for piece in stream_reply(client, messages, settings):
                answer.append(piece)
                yield piece
        except OpenAIError as exc:  # 已开始输出，无法再改状态码，直接把错误写进流
            yield f"\n[请求失败] {exc}"
            return

        # 流式输出结束后一次性落库，保证历史与页面显示一致
        store.append(payload.session_id, "user", text)
        store.append(payload.session_id, "assistant", "".join(answer))
        store.trim(payload.session_id, settings.max_history_messages)

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


@app.post("/study/word", response_model=StudyWordResponse)
def study_word(
    payload: StudyWordRequest,
    settings: SettingsDep,
    client: ClientDep,
) -> StudyWordResponse:
    """学习功能：讲解指定英文单词并给出例句。"""
    word = payload.word.strip()
    if not word:
        raise HTTPException(status_code=400, detail="word 不能为空")

    try:
        explanation = chat_reply(client, word_explain_messages(word), settings)
    except OpenAIError as exc:
        raise HTTPException(status_code=502, detail=f"模型调用失败：{exc}") from exc

    return StudyWordResponse(word=word, explanation=explanation)


@app.get("/sessions", response_model=SessionList)
def list_sessions(store: StoreDep) -> SessionList:
    """查看数据库中已有的会话 ID 列表。"""
    return SessionList(sessions=store.list_session_ids())


@app.get("/sessions/{session_id}/messages", response_model=SessionMessages)
def get_session_messages(session_id: str, store: StoreDep) -> SessionMessages:
    """按对话顺序返回指定会话的消息记录。"""
    if not store.exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return SessionMessages(session_id=session_id, messages=store.get_messages(session_id))


@app.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str, store: StoreDep) -> None:
    """清空指定会话；会话不存在时返回 404。"""
    if not store.clear(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
