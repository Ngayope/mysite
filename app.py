from flask import Flask, request, jsonify
import os
import requests
from openai import OpenAI

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ユーザーごとの状態を保存
user_states = {}
questions = [
    "最近ちょっと楽しかったことは？",
    "休日にもっと時間があったら何してみたい？",
    "子どもの頃に好きだったことは？"
]

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Webhook received:", data)

    if "events" not in data:
        return "ok"

    for event in data["events"]:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_id = event["source"]["userId"]
            user_text = event["message"]["text"]
            reply_token = event["replyToken"]

            reply_message = handle_message(user_id, user_text)
            reply_to_line(reply_token, reply_message)

    return "ok"

def handle_message(user_id, user_text):
    state = user_states.get(user_id, {"step": 0, "answers": [], "used": False})

    # すでに診断済みの場合はブロック
    if state.get("used", False):
        return "診断は1回のみ無料です✨ もっと深掘りしたい場合は、詳細診断やコーチングプランをご利用ください！"

    if state["step"] < len(questions):
        if state["step"] > 0:  # 回答を保存
            state["answers"].append(user_text)

        # 次の質問を返す
        question = questions[state["step"]]
        state["step"] += 1
        user_states[user_id] = state
        return question
    else:
        # 最後の回答を保存
        state["answers"].append(user_text)
        result = generate_ai_reply(state["answers"])

        # 診断済みにマーク
        state["used"] = True
        user_states[user_id] = sta_]()_
