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
    # Part0: タイプ名（LUA風）
    prompt0 = f"""
ユーザーの回答は以下です：
{answers}

この人を一言で表す「タイプ名」を提案してください。
・必ず「◯◯タイプ」という形式にしてください。
・LUAがしゃべるように、明るく親しみやすいトーンにしてください。
・2文に分けて、1文目でタイプ名、2文目でその特徴をやさしく説明してください。
・説明はポジティブで、「〜だと思うよ！」「〜かもしれないね！」のような口調にしてください。

出力形式：
🚀 あなたは「◯◯タイプ」っぽいかも！（仮診断）
✨ 特徴: ...
"""

    try:
        res0 = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたはLUAというフレンドリーで元気なAIキャラクターです。"},
                {"role": "user", "content": prompt0}
            ],
            reasoning_effort="minimal",
            verbosity="low",
            max_completion_tokens=120
        )
        part0 = res0.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI error part0:", e)
        part0 = "🚀 あなたは「元気いっぱいタイプ」っぽいかも！（仮診断）\n✨ 特徴: やりたいことにワクワクして進める人だと思うよ！"

       # Part1: 強みと課題
    prompt1 = f"""
ユーザーの回答は以下です：
{answers}

あなたの役割は、この人の「強み」と「課題」を両方とも見つけることです。

⚠️ ルール
・必ず ✨強み と 🌙課題 の両方を出してください。
・どちらか一方だけでは不正解です。
・それぞれ1〜2文で説明してください。
・必ず回答を引用して、「なぜそう思うのか」の理由も添えてください。
・日本語は自然で、LUAらしく親しみやすいトーンにしてください。
・「〜だと思うよ！」「〜かもしれないね！」などの口調を使ってください。

出力形式（例）：
✨ 強み: 「もし時間もお金も〜」という答えから、新しい挑戦を楽しめる前向きさがあると思うよ！
🌙 課題: 「1年後に〜」という答えを見ると、未来像がちょっとあいまいかもしれないね。もう少し具体化すると動きやすいよ！
"""

    try:
        res1 = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたはLUAという明るく親しみやすいAIキャラクターです。"},
                {"role": "user", "content": prompt1}
            ],
            reasoning_effort="minimal",
            verbosity="low",
            max_completion_tokens=150
        )
        part1 = res1.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI error part1:", e)
        part1 = "✨ 強み: 自分らしさを大事にできるところ！\n🌙 課題: 少しだけ計画を立てるのが苦手かもね！"

    # Part2: ヒント
    prompt2 = f"""
ユーザーの回答は以下です：
{answers}

自己実現につながる具体的なヒントを必ず1つ出してください。
・1〜2文で書くこと。
・「なぜ有効か」を必ず含めること。
・最後に「応援してるよ！」など、LUAらしい励ましを入れてください。

出力形式：
💡 ヒント: ...
"""

    try:
        res2 = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたはLUAという明るくかわいらしいAIキャラクターです。"},
                {"role": "user", "content": prompt2}
            ],
            reasoning_effort="minimal",
            verbosity="low",
            max_completion_tokens=120
        )
        part2 = res2.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI error part2:", e)
        part2 = "💡 ヒント: 小さな一歩から始めると、続けやすいと思うよ！応援してるね！"

    # 固定コメント（LUA風）
    comment = "🪞 内省コメント: どこが当たっていて、どこが違うと感じるかを考えてみるといいかも！その違和感も自己理解のヒントになりそうだよ！"

    return part0 + "\n\n" + part1 + "\n" + part2 + "\n\n" + comment


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
