from flask import Flask, request, abort
import os
import requests

app = Flask(__name__)

# 環境変数からLINEの情報を取得
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Webhook received:", data)  # Renderログで確認用

    # イベントがあるか確認
    if "events" not in data:
        return "ok"

    for event in data["events"]:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_text = event["message"]["text"]
            reply_token = event["replyToken"]

            # オウム返しのメッセージ
            reply_message = f"あなたは「{user_text}」と言いましたね！"

            reply_to_line(reply_token, reply_message)

    return "ok"

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
    print("LINE API response:", res.status_code, res.text)  # ← ここ追加


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
