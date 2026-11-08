"""会话存储（SQLite 实现）。

第四次作业把会话从内存迁移到 SQLite：进程重启后历史仍然存在。
所有 SQL 只出现在本模块，接口层通过 SessionStore 的方法读写，不直接接触数据库。

表结构（详见 README 的 ER 图）：

- sessions：一个会话一行，主键为调用方传入的 session_id
- messages：一条消息一行，通过 session_id 外键关联会话，按插入顺序返回
"""

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

Message = dict[str, str]

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
"""


def _now() -> str:
    """统一使用 UTC 的 ISO 时间串，便于跨时区展示与排序。"""
    return datetime.now(UTC).isoformat(timespec="seconds")


class SessionStore:
    """基于 SQLite 的会话存储，读写方法与之前的版本保持一致。"""

    def __init__(self, db_path: str | Path = "chat.db") -> None:
        self.db_path = str(db_path)
        self._lock = Lock()
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """每次操作打开一个短连接，避免多线程共享连接带来的问题。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """启动时建表，重复执行不会报错（IF NOT EXISTS）。"""
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def ensure(self, session_id: str) -> None:
        """会话不存在时创建，存在时刷新 updated_at。"""
        timestamp = _now()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (id, created_at, updated_at) VALUES (?, ?, ?)",
                (session_id, timestamp, timestamp),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?", (timestamp, session_id)
            )

    def append(self, session_id: str, role: str, content: str) -> None:
        """追加一条消息；会话不存在时自动创建。"""
        self.ensure(session_id)
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, _now()),
            )

    def get_messages(self, session_id: str, limit: int | None = None) -> list[Message]:
        """按时间顺序返回消息；传 limit 时只取最近 limit 条。"""
        sql = "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id"
        params: Sequence[object] = (session_id,)
        if limit is not None:
            # 先按倒序取最近 N 条，再翻转成对话顺序
            sql = (
                "SELECT role, content FROM ("
                "  SELECT role, content, id FROM messages"
                "  WHERE session_id = ? ORDER BY id DESC LIMIT ?"
                ") ORDER BY id"
            )
            params = (session_id, limit)
        with self._lock, self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def list_session_ids(self) -> list[str]:
        """按创建顺序返回全部会话 ID（rowid 保证插入顺序稳定）。"""
        with self._lock, self._connect() as conn:
            rows = conn.execute("SELECT id FROM sessions ORDER BY rowid").fetchall()
        return [row["id"] for row in rows]

    def exists(self, session_id: str) -> bool:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return row is not None

    def clear(self, session_id: str) -> bool:
        """删除整个会话（消息由外键级联删除）；返回是否真的存在过。"""
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cursor.rowcount > 0

    def trim(self, session_id: str, limit: int) -> None:
        """只保留最近 limit 条消息，防止上下文无限增长。"""
        with self._lock, self._connect() as conn:
            conn.execute(
                "DELETE FROM messages WHERE session_id = ? AND id NOT IN ("
                "  SELECT id FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?"
                ")",
                (session_id, session_id, limit),
            )

    def clear_all(self) -> None:
        """清空全部会话，主要用于测试或维护。"""
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM sessions")
