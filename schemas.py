"""HTTP 请求与响应模型。"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, description="调用方提供的会话 ID")
    message: str = Field(description="用户消息，空消息由接口返回 400")


class ChatResponse(BaseModel):
    session_id: str
    reply: str


class Message(BaseModel):
    role: str = Field(description="user 或 assistant")
    content: str


class SessionMessages(BaseModel):
    session_id: str
    messages: list[Message]


class SessionList(BaseModel):
    sessions: list[str]


class StudyWordRequest(BaseModel):
    word: str = Field(description="需要讲解的英文单词")


class StudyWordResponse(BaseModel):
    word: str
    explanation: str
