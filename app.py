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
    prompt = (
        "以下の回答を要約し、指定どおり4行だけ出力してください。\n"
        f"回答: {answers}\n\n"
        "出力形式（日本語・各1行・余分な文や装飾は出さない）:\n"
        "1. 強み: ...\n"
        "2. 課題: ...\n"
        "3. ヒント: ...\n"
        "4. 内省コメント: ..."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたは自己実現の簡易診断を行うアシスタントです。出力は簡潔に。"},
                {"role": "user", "content": prompt},
            ],
            # 重要: 推論を最小化＆短く出させる
            reasoning_effort="minimal",   # ← GPT-5系の新パラメータ
            verbosity="low",              # ← 返答を短めに
            max_completion_tokens=150,    # 120〜180の範囲で調整
            stop=None                     # 必要なら ["\n5."] などで強制終了も可
        )

        # ログで中身を観察
        print("OpenAI raw response:", response)

        content = response.choices[0].message.content if response.choices else ""
        content = (content or "").strip()

        if not content:
            return "⚠️ 診断結果をうまく生成できませんでした。少し時間をあけて、もう一度お試しください。"

        # 念のため4行に整形（行が多すぎる/少なすぎる時の補正）
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        want = ["1. 強み:", "2. 課題:", "3. ヒント:", "4. 内省コメント:"]
        # 足りない行をダミーで補う
        while len(lines) < 4:
            lines.append(want[len(lines)] + " （生成できませんでした）")
        # 余分な行は切る
        lines = lines[:4]
        return "\n".join(lines)

    except Exception as e:
        print("OpenAI error:", e)
        return "💦 診断中にエラーが起きました。もう一度試してみてください。"


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

    res = requests.post(url, headers=headers, json=payload)
    print("LINE API response:", res.status_code, res.text)  # ← レスポンスログ追加

