"""对话接口测试：多轮上下文、会话隔离、学习功能与空消息校验。"""


def test_same_session_continues_history(api, fake_client):
    api.post("/chat", json={"session_id": "u1", "message": "你好"})
    fake_client.reply = "第二轮回复"
    api.post("/chat", json={"session_id": "u1", "message": "刚才我说了什么"})

    messages = fake_client.calls[-1]["messages"]
    assert [item["role"] for item in messages] == ["system", "user", "assistant", "user"]
    assert messages[1]["content"] == "你好"
    assert messages[2]["content"] == "模型回复"

    history = api.get("/sessions/u1/messages").json()["messages"]
    assert [item["content"] for item in history] == [
        "你好",
        "模型回复",
        "刚才我说了什么",
        "第二轮回复",
    ]


def test_different_sessions_do_not_mix(api, fake_client):
    api.post("/chat", json={"session_id": "u1", "message": "苹果"})
    api.post("/chat", json={"session_id": "u2", "message": "香蕉"})

    second_request = fake_client.calls[-1]["messages"]
    assert all("苹果" not in item["content"] for item in second_request)
    assert second_request[-1]["content"] == "香蕉"

    assert api.get("/sessions/u1/messages").json()["messages"][0]["content"] == "苹果"
    assert api.get("/sessions/u2/messages").json()["messages"][0]["content"] == "香蕉"


def test_study_word_api(api):
    response = api.post("/study/word", json={"word": "apple"})

    assert response.status_code == 200
    data = response.json()
    assert data["word"] == "apple"
    assert data["explanation"] == "模型回复"


def test_empty_message_rejected(api):
    assert api.post("/chat", json={"session_id": "u1", "message": "   "}).status_code == 400
    assert api.post("/chat", json={"session_id": "u1", "message": ""}).status_code == 400
    assert api.post("/study/word", json={"word": " "}).status_code == 400
