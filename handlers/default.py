# handlers/default.py
"""
這個檔案是訊息路由器的最後一道防線，主要負責處理所有未被其他特定規則（例如指令、狀態處理函式）匹配到的文字訊息。
它的主要職責是回覆通用的問候語、感謝語，以及針對無法識別的訊息提供一個友善的「不明白」回覆，以避免訊息沒有任何回應。
這個機制確保了無論用戶輸入什麼，都能得到一個基本的、不會讓對話中斷的回應。
"""
import logging
from linebot.v3.messaging.models import TextMessage

from utils.api_helper import get_messaging_api
from utils.line_common_messaging import send_line_reply_message

logger = logging.getLogger(__name__)

def handle(event):
    """
    這是預設的訊息處理函式，會處理所有未被 text_router.py 其他規則匹配到的文字訊息。
    函式會根據訊息內容，判斷是問候語、感謝語，或是不明的訊息，並給予對應的回覆。
    """
    api = get_messaging_api()
    text = event.message.text
    reply_token = event.reply_token
    user_id = event.source.user_id

    logger.info(f"[DefaultHandler] 處理通用/未識別訊息來自用戶 {user_id}: '{text}'")

    # --- 處理問候語 ---
    # 偵測用戶是否輸入了通用的問候語，例如「你好」或「哈囉」
    if "你好" in text or "哈囉" in text:
        messages = [
            TextMessage(text="🤗哈囉！您好～我是暖心天氣語"),
            TextMessage(text="您可以先設定預設城市，然後點擊選單，我會告訴您天氣資訊和穿搭建議喔！")
        ]
        send_line_reply_message(api, reply_token, messages)
        logger.info(f"[DefaultHandler] 已回覆問候語給用戶 {user_id}。")
        return True # 表示訊息已成功處理，阻止訊息路由器繼續執行後續的處理函式

    # --- 處理感謝語 ---
    # 偵測用戶是否輸入了感謝語，例如「謝謝」
    elif "謝謝" in text:
        send_line_reply_message(api, reply_token, [TextMessage(text="不客氣！很高興為您服務 ～🙏")])
        logger.info(f"[DefaultHandler] 已回覆感謝語給用戶 {user_id}。")
        return True # 表示訊息已成功處理，阻止訊息路由器繼續執行後續的處理函式

    # --- 處理所有未匹配的訊息 ---
    # 捕捉所有不符合上述問候語或感謝語的文字訊息，回覆一個通用的「不明白」訊息
    else:
        messages = [
            TextMessage(text="抱歉，我不明白您的意思🤔。請嘗試點擊選單或輸入特定關鍵字。")
        ]
        send_line_reply_message(api, reply_token, messages)
        logger.info(f"[DefaultHandler] 已回覆不明白訊息給用戶 {user_id}: '{text}'。")
        return True # 表示訊息已成功處理，阻止訊息路由器繼續執行後續的處理函式