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
    temp_img_url = data.get("img_url")  # ← ここで定義を先に！

    print("=== Received from GPT ===")
    print("text:", text)
    print("temp_img_url:", temp_img_url)
    print("=========================")

    # 画像をダウンロードして static に保存
    img_url = None
    if temp_img_url:
        try:
            r = requests.get(temp_img_url, stream=True)
            if r.status_code == 200:
                filename = f"diagnosis_{uuid.uuid4().hex}.png"
                filepath = os.path.join("static", filename)
                with open(filepath, "wb") as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
                # 永続URL
                img_url = f"https://line-yaritai-bot.onrender.com/static/{filename}"
                print("Saved image to:", img_url)
            else:
                print("Image download failed:", r.status_code)
        except Exception as e:
            print("Error saving image:", e)

    status, res_text = push_to_line(text, img_url)
    return jsonify({"status": status, "response": res_text, "text": text, "img_url": img_url})


@app.route("/")
def home():
    return "Flask bridge is running!"
