# default.py
# 處理未識別的訊息和通用問候語
import logging
from linebot.v3.messaging.models import TextMessage
from utils.api_helper import get_messaging_api
from utils.line_common_messaging import send_line_reply_message

logger = logging.getLogger(__name__)

def handle(event):
    """
    處理所有未被 text_router 其他規則匹配的文字訊息。
    包括通用問候語和最終的「不明白」回覆。
    """
    api = get_messaging_api()
    text = event.message.text
    reply_token = event.reply_token
    user_id = event.source.user_id

    logger.info(f"[DefaultHandler] 處理通用/未識別訊息來自用戶 {user_id}: '{text}'")

    # --- 處理問候語 ---
    if "你好" in text or "哈囉" in text:
        messages = [
            TextMessage(text="哈囉！您好～我是暖心天氣語"),
            TextMessage(text="您可以先設定預設城市，然後點擊選單，我會告訴您天氣資訊和穿搭建議喔！")
        ]
        send_line_reply_message(api, reply_token, messages)
        logger.info(f"[DefaultHandler] 已回覆問候語給用戶 {user_id}。")
        return True # 表示已處理

    elif "謝謝" in text:
        send_line_reply_message(api, reply_token, [TextMessage(text="不客氣！很高興為您服務。")])
        logger.info(f"[DefaultHandler] 已回覆感謝語給用戶 {user_id}。")
        return True # 表示已處理

    # --- 處理所有未匹配的訊息 (最終的「不明白」) ---
    else:
        # 可以選擇回覆一個通用的「不明白」訊息
        messages = [
            TextMessage(text="抱歉，我不明白您的意思。請嘗試使用其他指令。"),
            # TextMessage(text=f"您說了: '{text}'\n請使用選單操作功能或輸入特定關鍵字。") # 備用，提供用戶輸入內容
        ]
        send_line_reply_message(api, reply_token, messages)
        logger.info(f"[DefaultHandler] 已回覆不明白訊息給用戶 {user_id}: '{text}'。")
        return True # 表示已處理