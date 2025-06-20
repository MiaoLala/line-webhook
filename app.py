import os
from flask import Flask, request, abort
from linebot.v3.messaging import MessagingApi
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhook.exceptions import InvalidSignatureError
from linebot.v3.webhook.models import MessageEvent, TextMessageEvent, TextMessage
from linebot.v3.messaging.models import TextSendMessage

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

messaging_api = MessagingApi(channel_access_token=LINE_CHANNEL_ACCESS_TOKEN)
webhook_handler = WebhookHandler(channel_secret=LINE_CHANNEL_SECRET)

@app.route("/", methods=["GET"])
def home():
    return "LINE Webhook Running!"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        webhook_handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@webhook_handler.add(MessageEvent, message=TextMessageEvent)
def handle_message(event: MessageEvent):
    user_id = event.source.user.user_id
    print(f"✅ 收到來自使用者的 userId：{user_id}")

    messaging_api.reply_message(
        reply_token=event.reply_token,
        messages=[TextSendMessage(text="✅ Hello! 已收到你的訊息，userId 已記錄！")]
    )

if __name__ == "__main__":
    app.run(debug=True)
