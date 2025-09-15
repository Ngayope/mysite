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

# 診断用の質問リスト
questions_self = [
    "ねぇねぇ、ここ1週間で一番ワクワクした瞬間ってなに？🌟",
    "友達とか家族から『あなたって◯◯だよね』って言われること、ある？👀",
    "もし時間もお金もぜーんぶ気にしなくていいなら、今すぐやってみたいことってある？",
    "1年後のあなたが『最高！』って笑ってるとしたら、どんな姿だと思う？✨",
    "今日、ほんのちょっとだけ動くなら、どんなことから始めたい？"
]

questions_want = [
    "これから1ヶ月だけ自由に時間があるとしたら、どんなことをやってみたい？🌟",
    "誰かの役に立てたとき、『やってよかった！』って思った瞬間ってある？👀",
    "もし明日から1つだけ新しいチャレンジを始めるなら、なにを選ぶ？✨",
    "10年後のあなたが『あの時やってよかった！』って言ってることってなんだと思う？💭"
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
    state = user_states.get(user_id)

    # 初回メッセージ → LUAの自己紹介と診断選択
    if not state:
        intro = (
            "やっほー！LUAだよ🌙✨\n\n"
            "わたしは『Link Up with AI』の診断アシスタント。"
            "いまは成長中で、出力がちょっと不安定なときもあるけどごめんね🙏\n"
            "これからいっぱい勉強して、もっと頼れる相棒になっていくから楽しみにしててね！\n\n"
            "診断は2種類あるよ！\n"
            "1️⃣ 自己理解診断（自分の強みや課題を知りたい人向け）\n"
            "2️⃣ やりたいこと診断（夢や目標を見つけたい人向け）\n\n"
            "やりたい診断の名前を送ってね！（例：『自己理解』 or 『やりたいこと』）"
        )
        user_states[user_id] = {"mode": None, "step": 0, "answers": [], "used": False}
        return intro

    state = user_states[user_id]

    # まだ診断モードが決まっていないとき
    if state["mode"] is None:
        if "やりたい" in user_text:
            mode = "want"
            questions = questions_want
            first_msg = "やりたいこと診断、はじめてみよっか！🌟"
        else:
            mode = "self"
            questions = questions_self
            first_msg = "自己理解診断、はじめてみよっか！🌟"

        state.update({"mode": mode, "step": 0, "answers": [], "used": False})
        user_states[user_id] = state
        return first_msg + "\n" + questions[0]

    mode = state["mode"]
    questions = questions_self if mode == "self" else questions_want

    if state.get("used", False):
        return "診断は1回のみ無料だよ✨ 続きをご希望の方は、詳細診断やコーチングプランを見てみてね！"

    if state["step"] < len(questions):
        if state["step"] > 0:
            state["answers"].append(user_text)

        question = questions[state["step"]]
        state["step"] += 1
        user_states[user_id] = state
        return question
    else:
        state["answers"].append(user_text)
        result = generate_ai_reply(state["answers"], mode)
        state["used"] = True
        user_states[user_id] = state
        return result


def generate_ai_reply(answers, mode):
    if mode == "self":
        return generate_self_reply(answers)
    else:
        return generate_want_reply(answers)


def generate_self_reply(answers):
    # 自己理解診断（タイプ＋強み・課題＋ヒント）
    # ... ← ここはすでに実装済みのコードを利用（あなたのバージョンでOK）
    return "（自己理解診断の結果をここで返す）"


def generate_want_reply(answers):
    # やりたいこと診断（テーマ＋ポイント＋一歩目）
    prompt = f"""
ユーザーの回答は以下です：
{answers}

この人が「やりたいこと」を見つけるサポートをしてください。

⚠️ルール
・テーマを1つまとめること
・ポイント（回答から見えた共通点）を1〜2文で示すこと
・「最初の一歩」を1文で具体的に示すこと
・LUAらしいフレンドリーなトーンで！

出力形式：
🚀 あなたがやりたいことのテーマは「◯◯」かもしれないね！
✨ ポイント: ...
💡 最初の一歩: ...
"""

    try:
        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたはLUAというフレンドリーで親しみやすいAIキャラクターです。"},
                {"role": "user", "content": prompt}
            ],
            reasoning_effort="minimal",
            verbosity="low",
            max_completion_tokens=150
        )
        output = res.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI error want:", e)
        output = "🚀 あなたがやりたいことのテーマは「自由を楽しむこと」かもね！\n✨ ポイント: 自分らしく動ける瞬間を大事にしてる気がするよ！\n💡 最初の一歩: 小さな挑戦から始めてみよう！"

    comment = "🪞 内省コメント: 本当にやりたいことか、自分の心に聞いてみると新しい気づきがあるかもしれないよ！"
    return output + "\n\n" + comment


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
