from notion_client import Client
import datetime
import os

notion = Client(auth=os.getenv("NOTION_TOKEN"))
PAGE_ID = "21dd8d0b09f180938ef8e17e9a92bea9"
MAX_PER_MONTH = 180

def is_same_month(date_str):
    if not date_str:
        return False
    now = datetime.datetime.now()
    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    return date_obj.year == now.year and date_obj.month == now.month

def get_message_count_info():
    page = notion.pages.retrieve(PAGE_ID)
    count = page["properties"]["Count"]["number"]
    last_sent = page["properties"]["LastSent"]["date"]["start"] if page["properties"]["LastSent"]["date"] else None
    return count, last_sent

def should_send():
    count, last_sent = get_message_count_info()
    if not is_same_month(last_sent):
        # 月份不同，自動重設
        reset_message_count()
        return True
    return count < MAX_PER_MONTH

def increment_message_count():
    count, _ = get_message_count_info()
    new_count = count + 1
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    notion.pages.update(PAGE_ID, properties={
        "Count": {"number": new_count},
        "LastSent": {"date": {"start": today}}
    })

def reset_message_count():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    notion.pages.update(PAGE_ID, properties={
        "Count": {"number": 0},
        "LastSent": {"date": {"start": today}}
    })
