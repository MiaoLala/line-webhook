import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from notion_client import Client
from datetime import datetime

app = Flask(__name__)

# LINE Bot 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# Notion 設定
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
notion = Client(auth=NOTION_TOKEN)

@app.route("/", methods=["GET"])
def home():
    return "LINE Webhook Running!"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip()
    print(f"✅ 收到來自 {user_id} 的訊息：{user_message}")

    if user_message.startswith("員編："):
        staff_id = user_message.replace("員編：", "").strip()

        # 1️⃣ 查詢是否已有相同 User ID
        try:
            user_check = notion.databases.query(
                database_id=NOTION_DATABASE_ID,
                filter={
                    "property": "User ID",
                    "rich_text": {
                        "equals": user_id
                    }
                }
            )
        except Exception as e:
            print(f"❌ 查詢 User ID 發生錯誤：{e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 查詢失敗，請稍後再試")
            )
            return

        if user_check.get("results"):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="你已經登記過囉，不需要重複填寫～")
            )
            return

        # 2️⃣ 查詢是否已有相同員編
        try:
            staff_check = notion.databases.query(
                database_id=NOTION_DATABASE_ID,
                filter={
                    "property": "Name",
                    "title": {
                        "equals": staff_id
                    }
                }
            )
        except Exception as e:
            print(f"❌ 查詢員編發生錯誤：{e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 查詢失敗，請稍後再試")
            )
            return

        if staff_check.get("results"):
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ 此員編已被使用，請確認後再填寫")
            )
            return

        # 3️⃣ 寫入 Notion
        try:
            notion.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties={
                    "Name": {
                        "title": [
                            {"text": {"content": staff_id}}
                        ]
                    },
                    "User ID": {
                        "rich_text": [
                            {"text": {"content": user_id}}
                        ]
                    },
                    "接收時間": {
                        "date": {
                            "start": datetime.now().isoformat()
                        }
                    }
                }
            )
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"✅ 已成功登記員編：{staff_id}")
            )
            print(f"✅ 已寫入 Notion，userId: {user_id}, 員編: {staff_id}")
        except Exception as e:
            print(f"❌ 寫入 Notion 發生錯誤：{e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 寫入 Notion 發生錯誤，請稍後再試")
            )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入格式：員編：XXXX（例如：員編：7701）")
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
