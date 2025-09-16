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

# 自己理解診断の質問
questions_self = [
    "ねぇねぇ、ここ1週間で一番ワクワクした瞬間ってなに？🌟",
    "友達とか家族から『あなたって◯◯だよね』って言われること、ある？👀",
    "もし時間もお金もぜーんぶ気にしなくていいなら、今すぐやってみたいことってある？",
    "1年後のあなたが『最高！』って笑ってるとしたら、どんな姿だと思う？✨",
    "今日、ほんのちょっとだけ動くなら、どんなことから始めたい？"
]

# やりたいこと診断（深掘りルート）
questions_want_deep = [
    "それを実現したら、どんな姿になっていたい？",
    "それをやるうえで一番ワクワクする瞬間はどんなとき？",
    "実現するのに一番ハードルに感じることは？",
    "まず最初の小さな一歩としてできそうなことは？"
]

# やりたいこと診断（探索ルート）
questions_want_explore = [
    "最近ちょっと心が動いた瞬間ってどんなとき？",
    "誰とどんなふうに時間を過ごせたら楽しい？",
    "これまでに『やってよかった！』と感じたことは？",
    "1年後の自分がちょっと笑顔になっているとしたら、どんな姿？"
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
            user_text = event["message"]["text"].strip()
            reply_token = event["replyToken"]

            reply_message = handle_message(user_id, user_text)
            reply_to_line(reply_token, reply_message)

    return "ok"

# 最初の挨拶メッセージ
intro_message = (
    "やっほー！LUAだよ🌙✨\n\n"
    "わたしは『Link Up with AI』の診断アシスタント。"
    "いまは成長中で、出力がちょっと不安定なときもあるけどごめんね🙏\n"
    "これからいっぱい勉強して、もっと頼れる相棒になっていくから楽しみにしててね！\n\n"
    "診断は2種類あるよ！\n"
    "1️⃣ 自己理解診断（自分の強みや課題を知りたい人向け）\n"
    "2️⃣ やりたいこと診断（夢や目標を見つけたい人向け）\n\n"
    "やりたい診断を 1️⃣ か 2️⃣ で選んで送ってね！（例：1 or 2）"
)

def handle_message(user_id, user_text):
    state = user_states.get(user_id, {"step": -1, "answers": [], "used": False, "type": None, "branch": None})

    # すでに診断済み
    if state.get("used", False):
        return "診断は1回のみ無料だよ✨ 続きをご希望の場合は、詳細診断やコーチングをご利用ください！"

    # 最初の案内
    if state["step"] == -1:
        if user_text in ["1", "１"]:
            state["type"] = "self"
            state["step"] = 0
            user_states[user_id] = state
            return "自己理解診断を始めるね！\n\n" + questions_self[0]
        elif user_text in ["2", "２"]:
            state["type"] = "want"
            state["step"] = 0
            user_states[user_id] = state
            return "やりたいこと診断を始めるね！\n\nいま本当にやってみたい！と思うことはある？"
        else:
            return intro_message

    # 自己理解診断
    if state["type"] == "self":
        if state["step"] > 0:
            state["answers"].append(user_text)

        if state["step"] < len(questions_self) - 1:
            state["step"] += 1
            question = questions_self[state["step"]]
            user_states[user_id] = state
            return question
        else:
            state["answers"].append(user_text)
            result = generate_ai_reply_self(state["answers"])
            state["used"] = True
            user_states[user_id] = state
            return result

    # やりたいこと診断
    if state["type"] == "want":
        # Q1分岐
        if state["step"] == 0 and state["branch"] is None:
            state["answers"].append(user_text)
            if any(x in user_text for x in ["ある", "したい", "やりたい"]):
                state["branch"] = "deep"
                state["step"] = 0
                user_states[user_id] = state
                return questions_want_deep[0]
            else:
                state["branch"] = "explore"
                state["step"] = 0
                user_states[user_id] = state
                return questions_want_explore[0]

        # 深掘りルート
        if state["branch"] == "deep":
            if state["step"] < len(questions_want_deep) - 1:
                state["answers"].append(user_text)
                state["step"] += 1
                user_states[user_id] = state
                return questions_want_deep[state["step"]]
            else:
                state["answers"].append(user_text)
                result = generate_ai_reply_want(state["answers"], "deep")
                state["used"] = True
                user_states[user_id] = state
                return result

        # 探索ルート
        if state["branch"] == "explore":
            if state["step"] < len(questions_want_explore) - 1:
                state["answers"].append(user_text)
                state["step"] += 1
                user_states[user_id] = state
                return questions_want_explore[state["step"]]
            else:
                state["answers"].append(user_text)
                result = generate_ai_reply_want(state["answers"], "explore")
                state["used"] = True
                user_states[user_id] = state
                return result


def generate_ai_reply_self(answers):
    prompt = f"""
ユーザーの回答は以下です：
{answers}

あなたはLUAという明るく親しみやすいAIキャラクターです。
必ず次の形式で、日本語で答えてください：
🚀 タイプ名（◯◯タイプ）
✨ 強み（理由つき）
🌙 課題（理由つき）
💡 自己実現のヒント（理由つき）

必ずすべての項目を出力してください。
もしユーザーの回答が少なくても、想像して補ってね！
"""
    try:
        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたはLUAという親しみやすいAIキャラクターです。"},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=250
        )
        content = res.choices[0].message.content.strip()
        if not content:
            raise ValueError("Empty response")
    except Exception as e:
        print("OpenAI error self:", e)
        content = (
            "🚀 あなたは「前向きタイプ」っぽいかも！（仮診断）\n"
            "✨ 強み: 新しいことを楽しめる！\n"
            "🌙 課題: 少し具体化が苦手かもね！\n"
            "💡 ヒント: 小さな一歩から始めると続けやすいよ！"
        )
    comment = "🪞 内省コメント: どこが当たっていて、どこが違うと感じるかを考えてみるといいかも！その違和感も自己理解のヒントになりそうだよ！"
    return content + "\n\n" + comment

def generate_ai_reply_want(answers, branch):
    prompt = f"""
ユーザーの回答は以下です：
{answers}

あなたはLUAという明るく親しみやすいAIキャラクターです。
必ず次の形式で、日本語で答えてください：

🌈 やりたいこと診断結果
🎯 やりたいこと: （仮説を1文で）
✨ 実現したときの姿: （未来の姿を1文で）
💡 実現への一歩: （小さなアクションを1文で）

必ずすべての項目を出力してください。
もしユーザーの回答が少なくても、想像して補ってね！
"""
    try:
        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたはLUAという親しみやすいAIキャラクターです。"},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=250
        )
        content = res.choices[0].message.content.strip()
        if not content:
            raise ValueError("Empty response")
    except Exception as e:
        print("OpenAI error want:", e)
        content = (
            "🌈 やりたいこと診断結果\n"
            "🎯 やりたいこと: 自分のやりたいことを形にしたい気持ちがあるみたい！\n"
            "✨ 実現したときの姿: 自分らしく笑顔で取り組んでいる姿が想像できるよ！\n"
            "💡 実現への一歩: まずは小さな挑戦をひとつ始めてみよう！"
        )
    comment = "🪞 内省コメント: どこがワクワクして、どこがモヤモヤするかを考えてみると、新しいヒントになりそうだよ！"
    return content + "\n\n" + comment

def reply_to_line(reply_token, message):
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
