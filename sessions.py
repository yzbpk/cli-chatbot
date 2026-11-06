"""会话存储模块。

本次作业要求会话先保存在内存中，且所有读写集中在一个模块，
以后换成数据库时只需要替换这里的实现，接口层不用改动。
"""

from threading import Lock

Message = dict[str, str]


class InMemorySessionStore:
    """线程安全的内存会话存储，键为 session_id，值为按顺序排列的消息列表。"""

    def __init__(self) -> None:
        self._sessions: dict[str, list[Message]] = {}
        self._lock = Lock()

    def append(self, session_id: str, role: str, content: str) -> None:
        """追加一条消息；会话不存在时自动创建。"""
        with self._lock:
            self._sessions.setdefault(session_id, []).append(
                {"role": role, "content": content}
            )

    def get_messages(self, session_id: str) -> list[Message]:
        """返回会话消息的副本，避免调用方改动存储内部状态。"""
        with self._lock:
            return [dict(message) for message in self._sessions.get(session_id, [])]

    def list_session_ids(self) -> list[str]:
        """按创建顺序返回全部会话 ID。"""
        with self._lock:
            return list(self._sessions)

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    def clear(self, session_id: str) -> bool:
        """删除整个会话；返回是否真的存在过该会话。"""
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def trim(self, session_id: str, limit: int) -> None:
        """限制单会话保留的消息条数，防止上下文无限增长。"""
        with self._lock:
            messages = self._sessions.get(session_id)
            if messages is not None and len(messages) > limit:
                del messages[: len(messages) - limit]

    def clear_all(self) -> None:
        """清空全部会话，供测试在用例之间重置状态。"""
        with self._lock:
            self._sessions.clear()


store = InMemorySessionStore()
