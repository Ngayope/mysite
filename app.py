from flask import Flask, request, jsonify, session
import os, requests

app = Flask(__name__)
app.secret_key = "your_secret_key"  # セッション用
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# ------------------------
# LINE API 呼び出し関数
# ------------------------
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

def get_profile(user_id):
    """ユーザーがフォロー済みかを確認"""
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    url = f"https://api.line.me/v2/bot/profile/{user_id}"
    res = requests.get(url, headers=headers)
    return res if res.status_code == 200 else None

# ------------------------
# ChatGPT → Flask 経由で診断結果を受け取る
# ------------------------
@app.route("/push", methods=["POST"])
def push():
    data = request.json or {}
    text = data.get("text", "診断結果（ダミー）")
    user_id = data.get("to")

    if not user_id:
        return jsonify({"error": "user_id (to) is required"}), 400

    # セッションにユーザーごとの結果を保存
    if "results" not in session:
        session["results"] = {}
    session["results"][user_id] = text

    # フォロー確認
    profile = get_profile(user_id)
    if not profile:
        add_friend_url = "https://line.me/R/ti/p/@YOUR_LINE_ID"
        return jsonify({
            "error": "未フォロー",
            "message": "まずは公式アカウントを友だち追加してください",
            "follow_url": add_friend_url,
            "to": user_id
        }), 400

    # フォロー済みなら即送信
    status, res_text = push_to_line(user_id, text)
    return jsonify({"status": status, "response": res_text, "text": text, "to": user_id})

# ------------------------
# Webhook でフォローイベントを受信
# ------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.json
    for event in body.get("events", []):
        if event["type"] == "follow":
            user_id = event["source"]["userId"]
            # セッションから診断結果を取得
            diagnosis = None
            if "results" in session:
                diagnosis = session["results"].get(user_id)

            if diagnosis:
                push_to_line(user_id, diagnosis)
    return "OK"

@app.route("/")
def home():
    return "Flask bridge for LINE text push is running!"
