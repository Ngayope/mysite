from flask import Flask, request, jsonify
import os
import requests
from openai import OpenAI
import random

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

# 相槌のバリエーション
aizuchi_list = ["うんうん！", "なるほど〜", "いいね！", "へぇ、面白い！", "確かに！", "すごいね！"]

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

            reply_messages = handle_message(user_id, user_text)
            reply_to_line(reply_token, reply_messages)

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
        return [{"type": "text", "text": "診断は1回のみ無料だよ✨ 続きをご希望の場合は、詳細診断やコーチングをご利用ください！"}]

    # 最初の案内
    if state["step"] == -1:
        if user_text in ["1", "１"]:
            state["type"] = "self"
            state["step"] = 0
            user_states[user_id] = state
            return [{"type": "text", "text": "自己理解診断を始めるね！\n\n" + questions_self[0]}]
        elif user_text in ["2", "２"]:
            state["type"] = "want"
            state["step"] = 0
            user_states[user_id] = state
            return [{"type": "text", "text": "やりたいこと診断を始めるね！\n\nやりたいことはある？"}]
        else:
            return [{"type": "text", "text": intro_message}]

    # 自己理解診断
    if state["type"] == "self":
        if state["step"] > 0:
            state["answers"].append(user_text)

        if state["step"] < len(questions_self) - 1:
            state["step"] += 1
            question = questions_self[state["step"]]
            user_states[user_id] = state
            return [{"type": "text", "text": random.choice(aizuchi_list) + "\n" + question}]
        else:
            state["answers"].append(user_text)
            result = generate_ai_reply_self(state["answers"])
            img_url = generate_summary_image("自己理解診断", state["answers"], result)
            state["used"] = True
            user_states[user_id] = state
            return [{"type": "text", "text": result}, {"type": "image", "originalContentUrl": img_url, "previewImageUrl": img_url}]

    # やりたいこと診断
    if state["type"] == "want":
        # Q1分岐
        if state["step"] == 0 and state["branch"] is None:
            state["answers"].append(user_text)
            if any(x in user_text for x in ["ある", "したい", "やりたい"]):
                state["branch"] = "deep"
                state["step"] = 0
                user_states[user_id] = state
                return [{"type": "text", "text": questions_want_deep[0]}]
            else:
                state["branch"] = "explore"
                state["step"] = 0
                user_states[user_id] = state
                return [{"type": "text", "text": questions_want_explore[0]}]

        # 深掘りルート
        if state["branch"] == "deep":
            if state["step"] < len(questions_want_deep) - 1:
                state["answers"].append(user_text)
                state["step"] += 1
                user_states[user_id] = state
                return [{"type": "text", "text": random.choice(aizuchi_list) + "\n" + questions_want_deep[state["step"]]}]
            else:
                state["answers"].append(user_text)
                result = generate_ai_reply_want(state["answers"])
                img_url = generate_summary_image("やりたいこと診断", state["answers"], result)
                state["used"] = True
                user_states[user_id] = state
                return [{"type": "text", "text": result}, {"type": "image", "originalContentUrl": img_url, "previewImageUrl": img_url}]

        # 探索ルート
        if state["branch"] == "explore":
            if state["step"] < len(questions_want_explore) - 1:
                state["answers"].append(user_text)
                state["step"] += 1
                user_states[user_id] = state
                return [{"type": "text", "text": random.choice(aizuchi_list) + "\n" + questions_want_explore[state["step"]]}]
            else:
                state["answers"].append(user_text)
                result = generate_ai_reply_want(state["answers"])
                img_url = generate_summary_image("やりたいこと診断", state["answers"], result)
                state["used"] = True
                user_states[user_id] = state
                return [{"type": "text", "text": result}, {"type": "image", "originalContentUrl": img_url, "previewImageUrl": img_url}]


def generate_ai_reply_self(answers):
    # フォールバック前提のAI呼び出し
    try:
        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたはLUAという明るく親しみやすいAIキャラクターです。"},
                {"role": "user", "content": f"ユーザーの回答: {answers}\n自己理解診断の結果をまとめて。"}
            ],
            max_completion_tokens=400
        )
        raw = res.choices[0].message.content.strip()
        if not raw:
            raise ValueError("Empty AI response")
        return raw
    except Exception as e:
        print("AI error self:", e)
        return "🚀 あなたは「前向きタイプ」かも！✨ 新しいことを楽しめる一方、具体化は少し苦手かも。💡 小さな一歩から始めると続けやすいよ！"

def generate_ai_reply_want(answers):
    try:
        res = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": "あなたはLUAという明るく親しみやすいAIキャラクターです。"},
                {"role": "user", "content": f"ユーザーの回答: {answers}\nやりたいこと診断の結果をまとめて。"}
            ],
            max_completion_tokens=400
        )
        raw = res.choices[0].message.content.strip()
        if not raw:
            raise ValueError("Empty AI response")
        return raw
    except Exception as e:
        print("AI error want:", e)
        return "🌈 やりたいこと診断結果\n🎯 やりたいこと: 自分のやりたいことを形にしたい！\n✨ 実現したときの姿: 自分らしく笑顔で取り組む未来！\n💡 実現への一歩: まずは小さな挑戦から！"

def generate_summary_image(title, answers, result_text):
    try:
        # ユーザーの回答からイメージを作成
        prompt = (
            f"カードデザイン風で、ポップで温かい雰囲気。"
            f"character.png のキャラクター（性別不詳の回答者）が『{title}』の診断に取り組んでいる様子。"
            f"隣に LUA.png の女の子キャラ（LUA）が励ましている。"
            f"ユーザーの回答内容に基づいて、未来像やシーンをわくわく感のある形で描いてください。"
            f"背景や状況は以下を参考に: {answers} / {result_text}。"
            f"キャラの表情やポーズも内容に合わせて変化させる。"
            f"テキストは含めず。"
        )

        with open("static/character.png", "rb") as char_img, open("static/lua.png", "rb") as lua_img:
            res = client.images.edit(
                model="gpt-image-1",
                prompt=prompt,
                images=[char_img, lua_img],
                size="1024x1024"
            )

        return res.data[0].url

    except Exception as e:
        print("Image generation error:", e)
        return "https://placekitten.com/512/512"

def reply_to_line(reply_token, messages):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": messages
    }
    res = requests.post(url, headers=headers, json=payload)
    print("LINE API response:", res.status_code, res.text)
