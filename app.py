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
    # 回答を整形して自然に渡す
    answers_text = "\n".join([f"Q{i+1}: {a}" for i, a in enumerate(answers)])

    prompt = f"""
ユーザーの回答は以下です：
{answers_text}

これを参考に、自己実現の仮診断を作成してください。

出力フォーマット：
🔥 あなたは「◯◯タイプ」っぽいです！（仮診断）

◆ 強み
- 回答を引用して、強みを具体的に2行以内で示す

◆ 課題
- 回答を引用して、課題や弱みを2行以内で示す

◆ 自己実現のヒント
- 行動につながるシンプルなアドバイスを1行

💡 内省コメント
- 「どこが当たっていて、どこが違うと感じるかを考えると新しい気づきが得られるかもしれません」など、
  自然に振り返りを促す一文

---

✨ 診断おつかれさまでした！ ✨
ここまでで「自分の強み」や「課題のヒント」を少し感じられたと思います。

ただし、今回の診断はあくまで“入口”の仮診断。
本当にやりたいことを実現するには、
小さな一歩を続ける「伴走」が必要です。

🚀 『自己実現 伴走プラン』
AIと仲間、そしてコーチが一緒に支える、世界にひとつの伴走サービスです。
- 🤖 AIが毎週進捗を確認し、次の一歩を提案
- 👥 仲間同士で成果や悩みをシェアして応援
- 🎤 必要に応じてコーチと1on1で深掘り

💡 今だけモニター限定価格：月額300円
（通常価格：月額3,000円）

👉 [伴走プランを詳しく見る]
"""

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたは自己実現支援を行う優秀なコーチです。"},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=500
        )

        print("OpenAI response:", response)  # デバッグログ
        result = response.choices[0].message.content if response.choices[0].message else None
        if not result:
            return "⚠️ AIから診断を生成できませんでした。もう一度試してください。"
        return result.strip()
    except Exception as e:
        print("OpenAI error:", e)
        return "⚠️ AI応答に失敗しました。時間をおいて再度お試しください。"


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

