from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

from user_registration import register_user  # 員編登記
from meeting_notification import send_meeting_notification

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

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

    if user_message == "會議通知":
        send_meeting_notification(event, user_id, user_message, line_bot_api)
    elif user_message == "我要綁定":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入格式：員編：XXXX，進行綁定")
        )
    elif user_message.startswith("員編："):
        register_user(event, user_id, user_message, line_bot_api)
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="輸入錯誤，請重試")
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
