# utils/menu_reply.py
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest

def build_text_reply(text: str, reply_token: str) -> ReplyMessageRequest:
    return ReplyMessageRequest(
        reply_token=reply_token,
        messages=[TextMessage(text=text)]
    )