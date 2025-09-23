from flask import Flask, request, jsonify
import os, requests
from threading import Lock

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_secret_key")

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
FOLLOW_URL = "https://line.me/R/ti/p/@441alvdp"

# --- プロセス内の簡易ストア（無料） ---
PENDING_RESULTS = {}  # { user_id: text }
STORE_LOCK = Lock()

def store_result(user_id, text):
    with STORE_LOCK:
        PENDING_RESULTS[user_id] = text

def pop_result(user_id):
    with STORE_LOCK:
        return PENDING_RESULTS.pop(user_id, None)

# --- LINE API ラッパ ---
def push_to_line(user_id, text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {"to": user_id, "messages": [{"type": "text", "text": text}]}
    res = requests.post(url, headers=headers, json=payload, timeout=10)
    print("LINE API response:", res.status_code, res.text)
    return res.status_code, res.text

def get_profile(user_id):
    """フォロー確認：取得できたらフォロー済み、できなければ未フォロー"""
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    url = f"https://api.line.me/v2/bot/profile/{user_id}"
    res = requests.get(url, headers=headers, timeout=10)
    return res if res.status_code == 200 else None

# --- ChatGPT→Flask：診断結果の受け皿 ---
@app.route("/push", methods=["POST"])
def push():
    data = request.json or {}
    text = data.get("text", "診断結果（ダミー）")
    user_id = data.get("to")

    if not user_id:
        return jsonify({"error": "user_id (to) is required"}), 400

    # 未送信結果を保存（フォロー完了を待てるようにする）
    store_result(user_id, text)

    # フォロー確認
    profile = get_profile(user_id)
    if not profile:
        return jsonify({
            "error": "未フォロー",
            "message": "まずは公式アカウントを友だち追加してください",
            "follow_url": FOLLOW_URL,
            "to": user_id
        }), 400

    # フォロー済みなら即送信
    status, res_text = push_to_line(user_id, text)
    if status == 200:
        # 送れたら保留を消しておく（念のため）
        pop_result(user_id)
    return jsonify({"status": status, "response": res_text, "text": text, "to": user_id})

# --- LINE Webhook：フォロー検知で送信 ---
@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.json or {}
    for event in body.get("events", []):
        etype = event.get("type")
        if etype == "follow":
            user_id = event["source"]["userId"]
            text = pop_result(user_id)
            if text:
                push_to_line(user_id, text)
        # 必要なら他のイベントタイプもここで処理
    return "OK"

@app.route("/healthz")
def healthz():
    return "ok"

@app.route("/")
def home():
    return "Flask bridge for LINE text push is running!"
