"""HTTP 请求与响应模型。

约定：所有 Pydantic 模型只在本模块定义，接口层与命令行入口都从这里导入，
避免出现“同一个结构在多个文件里各写一份”的情况。
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """普通对话与流式对话共用的请求体。"""

    # 调用方自己维护的会话编号，同一个 ID 的对话会共享上下文
    session_id: str = Field(min_length=1, description="调用方提供的会话 ID")
    # 用户输入；空白内容由接口层校验后返回 400
    message: str = Field(description="用户消息，空消息由接口返回 400")


class ChatResponse(BaseModel):
    """普通对话的响应体：原样带回会话 ID，便于前端继续对话。"""

    session_id: str
    reply: str


class Message(BaseModel):
    """会话中的一条消息，role 只会是 user 或 assistant。"""

    role: str = Field(description="user 或 assistant")
    content: str


class SessionMessages(BaseModel):
    """某个会话的完整消息记录，按发生顺序排列。"""

    session_id: str
    messages: list[Message]


class SessionList(BaseModel):
    """当前存在会话的 ID 列表。"""

    sessions: list[str]


class StudyWordRequest(BaseModel):
    """单词讲解请求体。"""

    word: str = Field(description="需要讲解的英文单词")


class StudyWordResponse(BaseModel):
    """单词讲解结果：词性、释义与例句组成的文本。"""

    word: str
    explanation: str
