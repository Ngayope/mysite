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

この回答をもとに、自己理解の仮診断を作成してください。

出力フォーマット：
🚀 あなたは「◯◯タイプ」っぽいかも！（仮診断）

✨ 強み
- 2文以内。ユーザーの回答を引用しながら、どんな強みがあるかを説明する。
- 「なぜそう思ったのか」も必ず理由を入れる。

🌙 課題
- 2文以内。ユーザーの回答を引用しながら、改善するともっと良くなる点を説明する。
- 「なぜそう思ったのか」も必ず理由を入れる。

💡 ヒント
- 2文以内。行動につながる具体的なアドバイスを書く。
- 「なぜ有効なのか」を説明する。

---
🪞 内省コメント
どこが当たっていて、どこが違うと感じるかを考えてみるといいかも！その違和感も自己理解のヒントになりそう！
"""

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたは自己実現をサポートする優秀なコーチです。出力は親しみやすく、理由を必ず含めてください。"},
                {"role": "user", "content": prompt}
            ],
            reasoning_effort="minimal",
            verbosity="low",
            max_completion_tokens=200
        )

        print("OpenAI raw response:", response)

        content = response.choices[0].message.content if response.choices else ""
        return (content or "診断結果を生成できませんでした。").strip()

    except Exception as e:
        print("OpenAI error:", e)
        return "診断中にエラーが起きました。もう一度試してみてください！"



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

