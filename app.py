from flask import Flask, request, jsonify, session
import os, requests

app = Flask(__name__)
app.secret_key = "your_secret_key"
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

def push_to_line(user_id, text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {"to": user_id, "messages": [{"type": "text", "text": text}]}
    res = requests.post(url, headers=headers, json=payload)
    print("LINE API response:", res.status_code, res.text)
    return res.status_code, res.text

def get_profile(user_id):
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    url = f"https://api.line.me/v2/bot/profile/{user_id}"
    res = requests.get(url, headers=headers)
    return res if res.status_code == 200 else None

@app.route("/push", methods=["POST"])
def push():
    data = request.json or {}
    text = data.get("text", "診断結果（ダミー）")
    user_id = data.get("to")

    if not user_id:
        return jsonify({"error": "user_id (to) is required"}), 400

    # 診断結果をセッションに保存
    if "results" not in session:
