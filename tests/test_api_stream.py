"""流式接口测试：stream=True、逐块内容与完整回复落库。"""


def test_stream_request_uses_stream_true(api, fake_client):
    fake_client.pieces = ["你", "好", "呀"]

    response = api.post("/chat/stream", json={"session_id": "s1", "message": "打个招呼"})

    assert response.status_code == 200
    assert response.text == "你好呀"
    assert fake_client.calls[-1]["stream"] is True


def test_stream_reply_saved_to_history(api, fake_client):
    fake_client.pieces = ["模型", "回复"]

    api.post("/chat/stream", json={"session_id": "s2", "message": "记住我"})

    history = api.get("/sessions/s2/messages").json()["messages"]
    assert history == [
        {"role": "user", "content": "记住我"},
        {"role": "assistant", "content": "模型回复"},
    ]


def test_stream_empty_message_rejected(api):
    response = api.post("/chat/stream", json={"session_id": "s3", "message": "  "})
    assert response.status_code == 400
