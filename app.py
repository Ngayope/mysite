from flask import Flask, request, jsonify
import os, requests
from openai import OpenAI

app = Flask(__name__)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

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
    # カスタムGPTから { "text": "...", "img_prompt": "..." } を受け取る想定
    data = request.json or {}
    text = data.get("text", "診断結果（ダミー）")
    img_prompt = data.get("img_prompt")

    img_url = None
    if img_prompt:
        try:
            res = client.images.generate(
                model="gpt-image-1",
                prompt=img_prompt,
                size="512x512"
            )
            img_url = res.data[0].url.strip()
        except Exception as e:
            print("Image generation error:", e)

    status, res_text = push_to_line(text, img_url)
    return jsonify({"status": status, "response": res_text, "text": text, "img_url": img_url})

@app.route("/")
def home():
    return "Flask bridge with GPT-image is running!"
