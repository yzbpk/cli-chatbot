"""SQLite 会话存储单元测试：写入、隔离、截断、删除与重启后持久化。"""

from chatbot.repositories.session_store import SessionStore


def make_store(tmp_path, name="test.db") -> SessionStore:
    return SessionStore(tmp_path / name)


def test_append_and_read_in_order(tmp_path):
    store = make_store(tmp_path)
    store.append("s1", "user", "你好")
    store.append("s1", "assistant", "你好，有什么可以帮你？")

    messages = store.get_messages("s1")
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "你好"


def test_sessions_are_isolated(tmp_path):
    store = make_store(tmp_path)
    store.append("a", "user", "A 的问题")
    store.append("b", "user", "B 的问题")

    assert store.get_messages("a") == [{"role": "user", "content": "A 的问题"}]
    assert store.get_messages("b") == [{"role": "user", "content": "B 的问题"}]
    # 列表按创建顺序返回
    assert store.list_session_ids() == ["a", "b"]


def test_trim_keeps_latest_messages(tmp_path):
    store = make_store(tmp_path)
    for index in range(6):
        store.append("s1", "user", f"第 {index} 条")

    store.trim("s1", 2)

    assert [m["content"] for m in store.get_messages("s1")] == ["第 4 条", "第 5 条"]


def test_clear_removes_session_and_messages(tmp_path):
    store = make_store(tmp_path)
    store.append("s1", "user", "待删除")

    assert store.clear("s1") is True
    assert store.exists("s1") is False
    assert store.get_messages("s1") == []
    assert store.clear("s1") is False


def test_data_survives_new_instance(tmp_path):
    first = make_store(tmp_path)
    first.append("persist", "user", "重启前")
    first.append("persist", "assistant", "重启后仍在")

    second = SessionStore(tmp_path / "test.db")

    assert second.exists("persist") is True
    assert [m["content"] for m in second.get_messages("persist")] == ["重启前", "重启后仍在"]


def test_limit_returns_recent_messages(tmp_path):
    store = make_store(tmp_path)
    for index in range(4):
        store.append("s1", "user", f"m{index}")

    assert [m["content"] for m in store.get_messages("s1", limit=2)] == ["m2", "m3"]
