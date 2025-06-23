import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from notion_client import Client
from datetime import datetime, date

app = Flask(__name__)

# ======== LINE Bot 設定 ========
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# ======== Notion 設定 ========
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
MEETING_DB_ID = "cd784a100f784e15b401155bc3313a1f"  # 會議 database
USERID_DB_ID = "21bd8d0b09f180908e1df38429153325"  # userID database
notion = Client(auth=NOTION_TOKEN)

# ======== 輔助函式 ========
def get_user_map():
    """取得 userID database 中 員編 -> userId 的對照字典"""
    user_map = {}
    user_pages = notion.databases.query(
        database_id=USERID_DB_ID,
        filter={"property": "Name", "title": {"is_not_empty": True}}
    ).get("results", [])

    for page in user_pages:
        name = page["properties"]["Name"]["title"][0]["text"]["content"]
        user_id_prop = page["properties"].get("User ID", {}).get("rich_text", [])
        user_id = user_id_prop[0]["text"]["content"] if user_id_prop else None
        if name and user_id:
            user_map[name] = user_id
    return user_map

def get_today_meetings_for_user(staff_id):
    """取得指定員編今日相關會議"""
    today_str = date.today().isoformat()
    today_display = datetime.now().strftime("%Y/%m/%d")

    # 過濾條件：今天的會議
    filter_conditions = {
        "and": [
            {"property": "日期", "date": {
                "on_or_after": today_str,
                "on_or_before": today_str
            }},
            {"property": "類別", "select": {"equals": "會議"}}
        ]
    }

    meeting_pages = notion.databases.query(
        database_id=MEETING_DB_ID,
        filter=filter_conditions
    ).get("results", [])

    meetings_for_user = []

    for page in meeting_pages:
        props = page["properties"]
        persons = props.get("相關人員", {}).get("people", [])

        # 是否該員編在此會議中
        if not any(staff_id in p.get("name", "") for p in persons):
            continue

        # 確認會議是今天
        datetime_str = props["日期"]["date"]["start"]
        dt_obj = datetime.fromisoformat(datetime_str)
        if dt_obj.date() != date.today():
            continue

        # 取出資訊
        title = props["Name"]["title"][0]["text"]["content"] if props["Name"]["title"] else "未命名會議"
        date_time = dt_obj.strftime("%Y/%m/%d %H:%M")
        location = props.get("地點", {}).get("select", {}).get("name", "未填寫")

        meetings_for_user.append({
            "title": title,
            "datetime": date_time,
            "location": location
        })

    if not meetings_for_user:
        return f"{today_display} 今天沒有會議喔！"

    # 組合訊息文字
    lines = [f"{today_display} 會議提醒"]
    for idx, m in enumerate(meetings_for_user, 1):
        lines.append(f"{idx}. {m['title']}")
        lines.append(f"－ 時間：{m['datetime']}")
        lines.append(f"－ 地點：{m['location']}")
        lines.append("")
    return "\n".join(lines).strip()

# ======== Flask 路由 ========
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

# ======== LINE Bot 處理邏輯 ========
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip()
    print(f"✅ 收到來自 {user_id} 的訊息：{user_message}")

    # 處理「會議通知」指令
    if user_message == "會議通知":
        try:
            user_map = get_user_map()
            # 根據 user_id 找員編
            staff_id = next((k for k, v in user_map.items() if v == user_id), None)
            if not staff_id:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="❌ 找不到你的員編資料，請先登記員編")
                )
                return
            reply_text = get_today_meetings_for_user(staff_id)
        except Exception as e:
            print(f"❌ 錯誤：{e}")
            reply_text = "❌ 取得會議資訊失敗，請稍後再試"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
        return

    # 處理「員編：xxxx」登記
    if user_message.startswith("員編："):
        staff_id = user_message.replace("員編：", "").strip()

        # 查是否已登記過 user_id
        try:
            user_check = notion.databases.query(
                database_id=USERID_DB_ID,
                filter={"property": "User ID", "rich_text": {"equals": user_id}}
            )
        except Exception as e:
            print(f"❌ 查詢 User ID 錯誤：{e}")
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

        # 查是否員編已被其他人用過
        try:
            staff_check = notion.databases.query(
                database_id=USERID_DB_ID,
                filter={"property": "Name", "title": {"equals": staff_id}}
            )
        except Exception as e:
            print(f"❌ 查詢員編錯誤：{e}")
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

        # 寫入資料庫
        try:
            notion.pages.create(
                parent={"database_id": USERID_DB_ID},
                properties={
                    "Name": {
                        "title": [{"text": {"content": staff_id}}]
                    },
                    "User ID": {
                        "rich_text": [{"text": {"content": user_id}}]
                    },
                    "接收時間": {
                        "date": {"start": datetime.now().isoformat()}
                    }
                }
            )
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"✅ 已成功登記員編：{staff_id}")
            )
            print(f"✅ 登記成功：{staff_id} -> {user_id}")
        except Exception as e:
            print(f"❌ 寫入失敗：{e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 寫入 Notion 發生錯誤，請稍後再試")
            )
        return

    # 預設回應
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="請輸入格式：員編：XXXX（例如：員編：7701）")
    )

# ======== 啟動服務 ========
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
