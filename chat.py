"""命令行对话机器人入口：支持连续多轮对话。"""

import sys

from openai import OpenAIError
from pydantic import ValidationError

from config import Settings, get_settings
from llm import chat_reply, create_client

EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit"}


def load_settings() -> Settings:
    """加载配置；缺少必填项时给出可读提示并退出。"""
    try:
        return get_settings()
    except ValidationError as exc:
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"])
            if error["type"] == "missing":
                print(f"[配置缺失] 未设置 CHATBOT_{field.upper()}，请参考 .env.example 配置。")
            else:
                print(f"[配置错误] {field}: {error['msg']}")
        print("提示：复制 .env.example 为 .env 并填入 CHATBOT_API_KEY 后重新运行。")
        sys.exit(1)


def trim_history(messages: list, limit: int) -> list:
    """保留 system 消息与最近若干条对话，防止上下文无限增长。"""
    return [messages[0], *messages[1:][-(limit - 1) :]]


def run_chat() -> None:
    settings = load_settings()
    client = create_client(settings)
    messages = [{"role": "system", "content": settings.system_prompt}]

    print(f"命令行对话机器人（模型 {settings.model}），输入 exit 退出。")
    while True:
        try:
            user_input = input("你：")
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break

        text = user_input.strip()
        if not text:
            continue
        if text.lower() in EXIT_COMMANDS:
            print("再见。")
            break

        messages.append({"role": "user", "content": text})
        try:
            answer = chat_reply(client, messages, settings)
        except OpenAIError as exc:
            messages.pop()
            print(f"[请求失败] {exc}")
            continue

        print(f"AI：{answer}")
        messages.append({"role": "assistant", "content": answer})
        messages = trim_history(messages, settings.max_history_messages)


if __name__ == "__main__":
    run_chat()
