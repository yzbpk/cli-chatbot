"""会话管理接口测试：列表、消息记录、清空与 404。"""


def test_list_sessions_and_messages(api):
    api.post("/chat", json={"session_id": "u1", "message": "第一条"})
    api.post("/chat", json={"session_id": "u2", "message": "另一会话"})

    sessions = api.get("/sessions").json()["sessions"]
    assert sessions == ["u1", "u2"]

    record = api.get("/sessions/u1/messages").json()
    assert record["session_id"] == "u1"
    assert [item["role"] for item in record["messages"]] == ["user", "assistant"]
    assert record["messages"][0]["content"] == "第一条"


def test_delete_session_clears_history(api):
    api.post("/chat", json={"session_id": "u1", "message": "待清空"})

    assert api.delete("/sessions/u1").status_code == 204
    assert api.get("/sessions").json()["sessions"] == []
    assert api.get("/sessions/u1/messages").status_code == 404


def test_unknown_session_returns_404(api):
    assert api.get("/sessions/not-exist/messages").status_code == 404
    assert api.delete("/sessions/not-exist").status_code == 404
