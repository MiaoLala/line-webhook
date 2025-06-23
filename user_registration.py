from notion_client import Client
from datetime import datetime
import os
from linebot.models import TextSendMessage

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
USERID_DB_ID = "21bd8d0b09f180908e1df38429153325"
notion = Client(auth=NOTION_TOKEN)

def register_user(event, user_id, user_message, line_bot_api):
    staff_id = user_message.replace("員編：", "").strip()

    try:
        user_check = notion.databases.query(
            database_id=USERID_DB_ID,
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

    try:
        staff_check = notion.databases.query(
            database_id=USERID_DB_ID,
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

    try:
        notion.pages.create(
            parent={"database_id": USERID_DB_ID},
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
