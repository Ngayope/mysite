from flask import Flask, request, jsonify, redirect
import os, requests, sqlite3

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_secret_key")

LINE_CHANNEL_ID = os.getenv("LINE_CHANNEL_ID")  # ログインチャネルID
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")  # ログインチャネルのシークレット
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")  # Messaging API用
FOLLOW_URL = "https://line.me/R/ti/p/@441alvdp"
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://line-yaritai-bot.onrender.com/")
DB_PATH = "diagnosis.db"

# --- DBユーティリティ ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS pending_results (
            user_id TEXT PRIMARY KEY,
            text TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()


def store_result(user_id, text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO pending_results (user_id, text) VALUES (?, ?)", (user_id, text))
    conn.commit()
    conn.close()

def pop_result(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT text FROM pending_results WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        c.execute("DELETE FROM pending_results WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return row[0]
    conn.close()
    return None

def save_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# --- LINE API ---
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
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"}
    url = f"https://api.line.me/v2/bot/profile/{user_id}"
    res = requests.get(url, headers=headers, timeout=10)
    return res if res.status_code == 200 else None

# --- LINEログイン ---
@app.route("/login")
def login():
    redirect_uri = f"{PUBLIC_BASE_URL}callback"
    url = (
        "https://access.line.me/oauth2/v2.1/authorize"
        f"?response_type=code&client_id={LINE_CHANNEL_ID}"
        f"&redirect_uri={redirect_uri}"
        "&state=xyz&scope=openid%20profile"
    )
    return redirect(url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    token_url = "https://api.line.me/oauth2/v2.1/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": f"{PUBLIC_BASE_URL}callback",
        "client_id": LINE_CHANNEL_ID,
        "client_secret": LINE_CHANNEL_SECRET,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_res = requests.post(token_url, data=data, headers=headers).json()
    access_token = token_res.get("access_token")

    # ユーザープロフィール取得
    profile_url = "https://api.line.me/v2/profile"
    profile_res = requests.get(profile_url, headers={"Authorization": f"Bearer {access_token}"}).json()
    print("Profile response:", profile_res)

    user_id = profile_res.get("userId")
    if not user_id:
        return f"ユーザーID取得失敗: {profile_res}"


    # DBに保存
    save_user(user_id)

    return f"ログイン完了！ userId={user_id}"

# --- ChatGPT→Flask ---
@app.route("/push", methods=["POST"])
def push():
    data = request.json or {}
    text = data.get("text", "診断結果（ダミー）")
    user_id = data.get("to")

    if not user_id:
        return jsonify({"error": "user_id (to) is required"}), 400

    # 保存
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
        pop_result(user_id)
    return jsonify({"status": status, "response": res_text, "text": text, "to": user_id})

# --- LINE Webhook ---
@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.json or {}
    for event in body.get("events", []):
        if event.get("type") == "follow":
            user_id = event["source"]["userId"]
            text = pop_result(user_id)
            if text:
                push_to_line(user_id, text)
    return "OK"

@app.route("/")
def home():
    return "Flask bridge with LINE login and push is running!"

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
