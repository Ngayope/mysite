from flask import Flask, request, jsonify
import os
import requests
from openai import OpenAI

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

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
            user_text = event["message"]["text"]
            reply_token = event["replyToken"]

            reply_message = generate_ai_reply(user_text)
            reply_to_line(reply_token, reply_message)

    return "ok"

def generate_ai_reply(user_text):
    prompt = f"""
    あなたは「やりたいこと診断AI」です。
    ユーザーの入力から、その人が実現したいことをやさしく言語化してください。
    また「タイプ診断」と「次の一歩」も添えてください。

    ユーザーの入力: {user_text}
    """
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": prompt}
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
