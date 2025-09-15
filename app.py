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

# LUAバージョンの質問
questions = [
    "ねぇねぇ、ここ1週間で一番ワクワクした瞬間ってなに？🌟",
    "友達とか家族から『あなたって◯◯だよね』って言われること、ある？👀",
    "もし時間もお金もぜーんぶ気にしなくていいなら、今すぐやってみたいことってある？",
    "1年後のあなたが『最高！』って笑ってるとしたら、どんな姿だと思う？✨",
    "今日、ほんのちょっとだけ動くなら、どんなことから始めたい？"
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
    # Part1: 強みと課題
    prompt1 = f"""
ユーザーの回答は以下です：
{answers}

強みと課題をそれぞれ1〜2文で説明してください。
必ず回答を引用し、なぜそう思うのかを理由も添えてください。

出力形式：
✨ 強み: ...
🌙 課題: ...
"""

    try:
        res1 = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたは自己理解をサポートする優しいコーチです。日本語は自然で親しみやすくしてください。"},
                {"role": "user", "content": prompt1}
            ],
            reasoning_effort="minimal",
            verbosity="low",
            max_completion_tokens=100
        )
        part1 = res1.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI error part1:", e)
        part1 = "強み・課題を生成できませんでした。"

    # Part2: ヒント
    prompt2 = f"""
ユーザーの回答は以下です：
{answers}

自己実現につながる具体的なヒントを1〜2文で出してください。
必ず「なぜ有効か」を理由に含めてください。

出力形式：
💡 ヒント: ...
"""

    try:
        res2 = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたは自己理解をサポートする優しいコーチです。"},
                {"role": "user", "content": prompt2}
            ],
            reasoning_effort="minimal",
            verbosity="low",
            max_completion_tokens=100
        )
        part2 = res2.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI error part2:", e)
        part2 = "ヒントを生成できませんでした。"

    # 固定コメント
    comment = "🪞 内省コメント: どこが当たっていて、どこが違うと感じるかを考えてみるといいかも！その違和感も自己理解のヒントになりそう！"

    return "🚀 あなたは「◯◯タイプ」っぽいかも！（仮診断）\n\n" + part1 + "\n" + part2 + "\n\n" + comment


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
    print("LINE API response:", res.status_code, res.text)
