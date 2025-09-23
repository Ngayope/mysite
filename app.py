from flask import Flask, request, jsonify
import os, requests

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

def push_to_line(user_id, text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    messages = [{"type": "text", "text": text}]
    payload = {"to": user_id, "messages": messages}
    res = requests.post(url, headers=headers, json=payload)
    print("LINE API response:", res.status_code, res.text)
    return res.status_code, res.text

@app.route("/push", methods=["POST"])
def push():
    data = request.json or {}
    text = data.get("text", "診断結果（ダミー）")
    user_id = data.get("to")

    if not user_id:
        return jsonify({"error": "user_id (to) is required"}), 400

    status, res_text = push_to_line(user_id, text)
    return jsonify({"status": status, "response": res_text, "text": text, "to": user_id})

@app.route("/")
def home():
    return "Flask bridge for LINE text push is running!"
