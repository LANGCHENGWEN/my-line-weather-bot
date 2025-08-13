# menu_handlers/menu_reply.py
"""
切換使用者的 Rich Menu 時，回覆給使用者切換狀態的文字訊息。
用來建構單一文字回覆訊息的輔助函式，用於快速建立並回傳單一文字訊息的 ReplyMessageRequest 物件。
將建立 LINE 回覆訊息的通用邏輯封裝起來，避免在多個地方重複寫相同的程式碼，從而提高程式碼的可重用性和可讀性。
"""
from linebot.v3.messaging.models import TextMessage, ReplyMessageRequest

def build_text_reply(text: str, reply_token: str) -> ReplyMessageRequest:
    """
    將 reply_token 和 TextMessage 封裝在 ReplyMessageRequest 中，供後續發送給 LINE Messaging API。
    這是 LINE API 要求的回覆格式，以便能正確的發送訊息給使用者。
    將建立訊息的細節抽象化，讓呼叫方只需要提供文字內容和權杖，就能得到一個完整的訊息物件，使得程式碼更簡潔、更易於理解。
    """
    return ReplyMessageRequest(
        reply_token=reply_token,
        messages=[TextMessage(text=text)]
    )