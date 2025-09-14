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
    # ユーザーの進行状況を確認
    state = user_states.get(user_id, {"step": 0, "answers": []})

    if state["step"] < len(questions):
        # 回答を保存
        if state["step"] > 0:  # 最初の入力はスキップして次の質問に進める
            state["answers"].append(user_text)

        # 次の質問を出す
        question = questions[state["step"]]
        state["step"] += 1
        user_states[user_id] = state
        return question
    else:
        # 全部答えたら診断を生成
        state["answers"].append(user_text)
        result = generate_ai_reply(state["answers"])
        # 状態をリセット
        user_states[user_id] = {"step": 0, "answers": []}
        return result

def generate_ai_reply(answers):
    prompt = f"""
    あなたは「やりたいこと診断AI」です。
    以下の回答を参考に、ユーザーが実現したいことをまとめてください。
    また「タイプ診断」と「次の一歩」も添えてください。

    回答: {answers}
    """
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": "あなたは診断AIです。結果を短くキャッチーにまとめてください。"},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def reply_to_line(reply_token, text):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + LINE_CHANNEL_ACCESS_TOKEN
    }
    body = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    res = requests.post(url, headers=headers, json=body)
    print("LINE API response:", res.status_code, res.text)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
