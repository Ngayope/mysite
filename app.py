from flask import Flask, request, jsonify
import os, requests

app = Flask(__name__)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

# === ここで static フォルダを指定 ===
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


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
    img_url = data.get("img_url")

    # ここで受け取った内容をログに出す
    print("=== Received from GPT ===")
    print("text:", text)
    print("img_url:", img_url)
    print("=========================")

    status, res_text = push_to_line(text, img_url)
    return jsonify({"status": status, "response": res_text, "text": text, "img_url": img_url})

@app.route("/")
def home():
    return "Flask bridge is running!"
