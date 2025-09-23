import base64
import uuid
from flask import Flask, request, jsonify, send_from_directory
import os, requests

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

# Renderの公開URLをデフォルトに設定
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://line-yaritai-bot.onrender.com/")

def push_to_line(text, img_url=None):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    messages = [{"type": "text", "text": text}]
    if img_url:
        messages.append({
            "type": "image",
            "originalContentUrl": img_url,
            "previewImageUrl": img_url
        })
    payload = {"to": LINE_USER_ID, "messages": messages}
    res = requests.post(url, headers=headers, json=payload)
    print("LINE API response:", res.status_code, res.text)
    return res.status_code, res.text

@app.route("/push", methods=["POST"])
def push():
    data = request.json or {}
    text = data.get("text", "診断結果（ダミー）")
    img_url_from_gpt = data.get("img_url")

    img_url = None
    if img_url_from_gpt:
        try:
            # 画像をダウンロード
            res = requests.get(img_url_from_gpt)
            res.raise_for_status()
            filename = f"diagnosis_{uuid.uuid4().hex}.png"
            static_dir = os.path.join(os.getcwd(), "static")
            os.makedirs(static_dir, exist_ok=True)
            filepath = os.path.join(static_dir, filename)
            with open(filepath, "wb") as f:
                f.write(res.content)

            # 公開URLに変換
            img_url = f"{PUBLIC_BASE_URL}static/{filename}"
            print("Saved image to:", img_url)

        except Exception as e:
            print("Error downloading image:", e)

    status, res_text = push_to_line(text, img_url)
    return jsonify({"status": status, "response": res_text, "text": text, "img_url": img_url})

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

@app.route("/")
def home():
    return "Flask bridge with base64 image is running!"
