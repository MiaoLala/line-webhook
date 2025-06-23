# meeting_notify.py
from notion_client import Client
from datetime import datetime, date
import pytz
import os
from linebot.models import TextSendMessage

# 設定台灣時區
tz = pytz.timezone("Asia/Taipei")

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
MEETING_DB_ID = "cd784a100f784e15b401155bc3313a1f"
USERID_DB_ID = "21bd8d0b09f180908e1df38429153325"
notion = Client(auth=NOTION_TOKEN)

def get_user_map():
    """取得 userid database 中 員編 -> userId 的對照字典"""
    user_map = {}
    user_pages = notion.databases.query(
        database_id=USERID_DB_ID,
        filter={
            "property": "Name",
            "title": {"is_not_empty": True}
        }
    ).get("results", [])

    for page in user_pages:
        name = page["properties"]["Name"]["title"][0]["text"]["content"]
        user_id_prop = page["properties"].get("User ID", {}).get("rich_text", [])
        user_id = user_id_prop[0]["text"]["content"] if user_id_prop else None
        if name and user_id:
            user_map[name] = user_id
    return user_map

def get_today_meetings_for_user(staff_id):
    """取得該員編今天所有相關會議列表"""
    now = datetime.now(tz)
    today_str = now.date().isoformat()
    today_display = now.strftime("%Y/%m/%d")

    filter_conditions = {
        "and": [
            {
                "property": "日期",
                "date": {
                    "on_or_after": today_str,
                    "on_or_before": today_str
                }
            },
            {
                "property": "類別",
                "select": {
                    "equals": "會議"
                }
            }
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

        match_found = any(staff_id in p.get("name", "") for p in persons)
        if not match_found:
            continue

        title = props["Name"]["title"][0]["text"]["content"] if props["Name"]["title"] else "未命名會議"
        datetime_str = props["日期"]["date"]["start"]
        dt_obj = datetime.fromisoformat(datetime_str).astimezone(tz)
        meeting_date = dt_obj.date()

        if meeting_date == now.date():
            date_time = dt_obj.strftime("%Y/%m/%d %H:%M")
            location = "未填寫"
            location_prop = props.get("地點")
            if location_prop and location_prop.get("select"):
                location = location_prop["select"]["name"]

            meetings_for_user.append({
                "title": title,
                "datetime": date_time,
                "location": location
            })

    if not meetings_for_user:
        return f"{today_display} 今天沒有會議喔！"

    lines = [f"{today_display} 會議提醒"]
    for idx, m in enumerate(meetings_for_user, start=1):
        lines.append(f"{idx}. {m['title']}")
        lines.append(f"－ 時間：{m['datetime']}")
        lines.append(f"－ 地點：{m['location']}")
        lines.append("")
    return "\n".join(lines).strip()

def send_meeting_notification(event, user_id, line_bot_api):
    try:
        user_map = get_user_map()
        staff_id = None
        for k, v in user_map.items():
            if v == user_id:
                staff_id = k
                break
        if not staff_id:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 找不到你的員編資料，請先登記員編")
            )
            return

        reply_text = get_today_meetings_for_user(staff_id)
    except Exception as e:
        print(f"❌ 查詢會議或使用者資料發生錯誤：{e}")
        reply_text = "❌ 取得會議資訊失敗，請稍後再試"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )