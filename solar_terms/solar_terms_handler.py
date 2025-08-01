# solar_terms/solar_terms_handler.py
import logging
from linebot.v3.messaging.models import TextMessage, FlexMessage, FlexBubble
from .solar_terms_calculator import get_current_solar_term_info_for_display
from .solar_terms_flex_builder import build_solar_term_flex_message
from utils.line_common_messaging import send_line_reply_message

logger = logging.getLogger(__name__)

def handle_solar_term_query(api, event):
    """
    處理節氣小知識的查詢請求。
    當用戶傳送 "節氣" 指令時，此函數被觸發。
    
    Args:
        api (LineBotApi): LINE Bot API 客戶端實例。
        event (Event): 收到的事件物件。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token

    logger.info(f"[SolarTermsHandler] 收到節氣查詢請求。用戶: {user_id}")
    
    try:
        # 獲取當前節氣資訊
        # 這裡使用 get_current_solar_term_info_for_display 來處理用戶查詢，
        # 它會找出最近一個已經發生的節氣作為「當前」節氣。
        solar_term_data = get_current_solar_term_info_for_display() 

        if solar_term_data:
            # 1. 直接呼叫建構器，它會返回完整的 FlexMessage 物件
            flex_message_to_send = build_solar_term_flex_message(solar_term_data)

            # 檢查 build_solar_term_flex_message 是否返回了有效的 FlexBubble
            if not isinstance(flex_message_to_send, FlexMessage):
                logger.error(f"build_solar_term_flex_message 返回了無效的物件，類型: {type(flex_message_to_send)}")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，節氣小知識卡片生成失敗 (內部錯誤)。")])
                return True
        
            # 2. 發送 FlexMessage。因為 build_solar_term_flex_message 已經返回一個完整的 FlexMessage
            # 所以 handler 只需要將它包裝在一個列表中即可。
            send_line_reply_message(api, reply_token, [flex_message_to_send])
            logger.info(f"[SolarTermsHandler] 成功回覆 {solar_term_data['name']} 節氣小知識 (Flex Message)。")
            return True
        
        else:
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，目前無法取得節氣資訊，請稍候再試。")])
            logger.warning("[SolarTermsHandler] 未能取得節氣資料。")
            return True

    except Exception as e:
        logger.exception(f"[SolarTermsHandler] 處理節氣查詢時發生錯誤: {e}")
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，查詢節氣小知識時發生內部錯誤，請稍候再試。")])
        return True