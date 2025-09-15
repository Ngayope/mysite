from flask import Flask, request, jsonify
import os
import requests
from openai import OpenAI

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ユーザーごとの状態を保存
user_states = {}
questions = [
    "最近ちょっと楽しかったことは？",
    "人から『あなたって◯◯な人だよね』と言われたことは？",
    "もし時間もお金も気にしなくていいなら、今すぐやってみたいことは？",
    "1年後に『こうなっていたら嬉しい』と思える状態は？",
    "やりたいことに向けて『今すぐ1歩』動くとしたら何をしますか？"
]

@app.route("/", methods=["GET"])
def home():
    return "LINE Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Webhook received:", data)

    if "events" not in data:
        return "ok"

    for event in data["events"]:
        if event["type"] == "message" and event["message"]["type"] == "text":
            user_id = event["source"]["userId"]
            user_text = event["message"]["text"]
            reply_token = event["replyToken"]

            reply_message = handle_message(user_id, user_text)
            reply_to_line(reply_token, reply_message)

    return "ok"

def handle_message(user_id, user_text):
    state = user_states.get(user_id, {"step": 0, "answers": [], "used": False})

    if state.get("used", False):
        return "診断は1回のみ無料です✨ 続きをご希望の場合は、詳細診断やコーチングをご利用ください！"

    if state["step"] < len(questions):
        if state["step"] > 0:
            state["answers"].append(user_text)

        question = questions[state["step"]]
        state["step"] += 1
        user_states[user_id] = state
        return question
    else:
        # 最後の回答を保存
        state["answers"].append(user_text)
        result = generate_ai_reply(state["answers"])
        state["used"] = True
        user_states[user_id] = state
        return result

def generate_ai_reply(answers):
    prompt = f"""
ユーザーの回答は以下です：
{answers}

これを参考に、自己実現の仮診断を作成してください。

出力フォーマット：
1. タイプ診断（🔥や🌱など絵文字付き）
   - 回答から推測されるタイプをキャッチーに名付ける（例：挑戦者タイプ）
2. 強み（回答の引用を交えて2行以内）
3. 課題（回答の引用を交えて2行以内）
4. 自己実現のヒント（行動につながるアドバイスを1行）
5. 内省を促すコメント
   - 例：「どこが当たっていて、どこが違うと感じたか考えてみると、新しい気づきが得られるかもしれません。」
6. 有料導線（詳細診断・伴走プラン・コーチングに誘導）

注意：
- 回答を必ず引用すること（例：「休日に◯◯したいと答えていましたね」）
- 診断は断定せず「仮診断」として提示すること
- 日本語で親しみやすく
"""

    response = client.chat.completions.create(
        model="gpt-5-nano",  # 今後はこちらを使用
        messages=[
            {"role": "system", "content": "あなたは自己実現支援を行う優秀なコーチです。"},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.8
    )

    return response.choices[0].message.content.strip()

def reply_to_line(reply_token, message):
    """LINEに返信"""
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }
    requests.post(url, headers=headers, json=payload)
