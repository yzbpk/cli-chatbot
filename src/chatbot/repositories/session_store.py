"""会话存储（SQLAlchemy ORM 实现）。

第五次作业把手写 SQL 替换为 SQLAlchemy ORM，表结构与接口方法保持不变，
因此接口层（api/app.py、cli.py）和测试文件无需改动即可直接运行。

ORM 模型（定义在本模块底部）：

- Session ：一个会话一行，主键为调用方传入的 session_id
- Message ：一条消息一行，通过 session_id 外键关联会话，删除会话时级联删除
"""

from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    create_engine,
    delete,
    event,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.orm import (
    Session as _SaSession,
)


def _now() -> str:
    """统一使用 UTC 的 ISO 时间串，便于跨时区展示与排序。"""
    return datetime.now(UTC).isoformat(timespec="seconds")


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""


class Session(Base):
    """会话表：一个会话一行，主键 session_id 由调用方生成并传入。"""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    # 反向关联，删除会话时由 ORM 级联删除所有消息
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Message(Base):
    """消息表：每个会话下的每条消息。role 只能是 user 或 assistant。"""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    session: Mapped[Session] = relationship(back_populates="messages")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="messages_role_check"),
        Index("idx_messages_session", "session_id", "id"),
    )


class SessionStore:
    """基于 SQLAlchemy ORM 的会话存储，方法签名与原生 SQLite 版本保持一致。"""

    def __init__(self, db_path: str | Path = "chat.db") -> None:
        self.db_path = str(db_path)
        # sqlite 对同文件可以开多个连接，但要求每个连接在同一线程内使用
        # check_same_thread=False 让 SQLAlchemy 在 FastAPI 多线程场景下正常工作
        self._engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            future=True,
        )
        # SQLite 默认不执行外键约束，需要每次连接后显式开启，
        # 这样 ORM 级联删除的消息才能由数据库级的 ON DELETE CASCADE 清理掉。
        @event.listens_for(self._engine, "connect")
        def _enable_foreign_keys(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()

        self._SessionLocal = sessionmaker(bind=self._engine, expire_on_commit=False)
        self._lock = Lock()
        self._init_schema()

    def _session(self) -> _SaSession:
        """返回一个新的 ORM Session；用完调用方负责 close。"""
        return self._SessionLocal()

    def _init_schema(self) -> None:
        """启动时建表，重复执行不会报错。"""
        with self._engine.begin() as conn:
            Base.metadata.create_all(conn)

    # ---- 会话 ----

    def ensure(self, session_id: str) -> None:
        """会话不存在时创建，存在时刷新 updated_at。"""
        timestamp = _now()
        with self._lock, self._session() as sess:
            obj = sess.get(Session, session_id)
            if obj is None:
                sess.add(Session(id=session_id, created_at=timestamp, updated_at=timestamp))
            else:
                obj.updated_at = timestamp
            sess.commit()

    def exists(self, session_id: str) -> bool:
        with self._lock, self._session() as sess:
            return sess.get(Session, session_id) is not None

    def clear(self, session_id: str) -> bool:
        """删除整个会话（ORM 级联删除自动清理消息）；返回是否真的存在过。"""
        with self._lock, self._session() as sess:
            obj = sess.get(Session, session_id)
            if obj is None:
                return False
            sess.delete(obj)
            sess.commit()
            return True

    def list_session_ids(self) -> list[str]:
        """按创建顺序返回全部会话 ID（rowid 保证插入顺序稳定）。"""
        with self._lock, self._session() as sess:
            rows = sess.execute(select(Session.id).order_by(Session.id)).scalars().all()
        return list(rows)

    # ---- 消息 ----

    def append(self, session_id: str, role: str, content: str) -> None:
        """追加一条消息；会话不存在时自动创建。"""
        self.ensure(session_id)
        with self._lock, self._session() as sess:
            sess.add(
                Message(
                    session_id=session_id,
                    role=role,
                    content=content,
                    created_at=_now(),
                )
            )
            sess.commit()

    def get_messages(self, session_id: str, limit: int | None = None) -> list[Message]:
        """按时间顺序返回消息；传 limit 时只取最近 limit 条。"""
        with self._lock, self._session() as sess:
            stmt = select(Message.role, Message.content).where(
                Message.session_id == session_id
            )
            if limit is not None:
                # 先倒序取最近 N 条，再翻转成对话顺序
                rows = sess.execute(
                    stmt.order_by(Message.id.desc()).limit(limit)
                ).all()
                rows = list(reversed(rows))
            else:
                rows = sess.execute(stmt.order_by(Message.id)).all()
        return [{"role": role, "content": content} for role, content in rows]

    def trim(self, session_id: str, limit: int) -> None:
        """只保留最近 limit 条消息，防止上下文无限增长。"""
        with self._lock, self._session() as sess:
            # ORM 子查询取得要保留的最近 limit 条 id
            keep_ids = (
                select(Message.id)
                .where(Message.session_id == session_id)
                .order_by(Message.id.desc())
                .limit(limit)
            )
            sess.execute(
                delete(Message).where(
                    Message.session_id == session_id, Message.id.not_in(keep_ids)
                )
            )
            sess.commit()

    def clear_all(self) -> None:
        """清空全部会话，主要用于测试或维护。"""
        with self._lock, self._session() as sess:
            sess.execute(delete(Session))
            sess.commit()
