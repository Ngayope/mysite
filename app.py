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
    # Part0: タイプ名
    prompt0 = f"""
ユーザーの回答は以下です：
{answers}

この人を一言で表す「タイプ名」を提案してください。
・必ず「◯◯タイプ」という形式にしてください。
・説明は2文。1文目でタイプ名、2文目で特徴をポジティブに説明してください。
・LUAらしく「〜だと思うよ！」「〜かもね！」の口調で。

出力形式：
🚀 あなたは「◯◯タイプ」っぽいかも！（仮診断）
✨ 特徴: ...
"""
    try:
        res0 = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたはLUAという明るく親しみやすいAIキャラクターです。"},
                {"role": "user", "content": prompt0}
            ],
            max_completion_tokens=120
        )
        part0 = res0.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI error part0:", e)
        part0 = "🚀 あなたは「ワクワク発見タイプ」っぽいかも！（仮診断）\n✨ 特徴: 新しいことを楽しんで挑戦する人だと思うよ！"

    # Part1: 強みと課題
    prompt1 = f"""
ユーザーの回答は以下です：
{answers}

強みと課題をそれぞれ1〜2文で出してください。
・必ず ✨強み と 🌙課題 の両方を書くこと
・回答を引用しながら「なぜそう思うか」も入れること
・LUAらしく親しみやすいトーンにすること

出力形式：
✨ 強み: ...
🌙 課題: ...
"""
    try:
        res1 = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたはLUAという元気でかわいらしいAIキャラクターです。"},
                {"role": "user", "content": prompt1}
            ],
            max_completion_tokens=150
        )
        part1 = res1.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI error part1:", e)
        part1 = "✨ 強み: 前向きに考えられるところ！\n🌙 課題: 計画を細かく立てるのはちょっと苦手かもね！"

    # Part2: ヒント
    prompt2 = f"""
ユーザーの回答は以下です：
{answers}

自己実現につながる具体的なヒントを1つください。
・1〜2文
・「なぜ有効か」を理由に含めること
・最後に「応援してるよ！」など励ましを入れること

出力形式：
💡 ヒント: ...
"""
    try:
        res2 = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたはLUAというフレンドリーで応援好きなAIキャラクターです。"},
                {"role": "user", "content": prompt2}
            ],
            max_completion_tokens=120
        )
        part2 = res2.choices[0].message.content.strip()
    except Exception as e:
        print("OpenAI error part2:", e)
        part2 = "💡 ヒント: 小さな一歩から始めると、続けやすいと思うよ！応援してるね！"

    # 固定コメント
    comment = "🪞 内省コメント: どこが当たっていて、どこが違うと感じるかを考えてみるといいかも！その違和感も自己理解のヒントになりそうだよ！"

    return part0 + "\n\n" + part1 + "\n" + part2 + "\n\n" + comment

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
