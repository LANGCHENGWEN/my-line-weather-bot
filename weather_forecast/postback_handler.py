# postback_handler.py
import json
import logging

from linebot.v3.messaging.models import TextMessage
from linebot.v3.webhooks.models import PostbackEvent

# 從 config 載入設定
from config import CWA_API_KEY

# 載入預報天氣相關功能
# from .forecast_options_flex import create_forecast_options_flex_message
from .cwa_forecast_api import get_cwa_forecast_data
from .weather_forecast_parser import parse_forecast_weather
from .line_forecast_messaging import build_forecast_weather_flex
# from .welcome_flex import create_welcome_flex_message

# 載入使用者狀態管理器
from utils.user_data_manager import set_user_state, clear_user_state

from utils.debug_tools import debug_parsed_weather

# 載入通用訊息發送功能
from utils.line_common_messaging import (
    send_line_reply_message, send_api_error_message, format_text_message
)

logger = logging.getLogger(__name__)

def handle_forecast_postback(messaging_api, event: PostbackEvent) -> bool:
    """
    處理天氣預報相關的 Postback 事件 (例如點擊 3/5/7 天按鈕)。
    如果 Postback 被處理，則返回 True，否則返回 False。
    """
    user_id = event.source.user_id
    postback_data = event.postback.data
    reply_token = event.reply_token

    logger.info(f"收到來自用戶 {user_id} 的 Postback 數據: '{postback_data}'")

    # 處理查詢天氣預報的 Postback (點擊 3/5/7 天按鈕)
    if "action=get_weather" in postback_data:
        params = {}
        try: # 使用 try-except 確保解析安全
            for item in postback_data.split('&'):
                if '=' in item:
                    key, value = item.split('=', 1) # 拆分一次，處理值中可能有的 =
                    params[key] = value
        except Exception as e:
            logger.error(f"解析 Postback 數據時發生錯誤: {e}，原始數據: {postback_data}")
            send_line_reply_message(messaging_api, reply_token, [TextMessage(text="查詢參數解析失敗，請稍候再試。")])
            return True

        county = params.get('county')
        # township = params.get('township')
        days_str = params.get('days')

        if not all([county, days_str]):
            logger.error(f"Postback 數據不完整: {postback_data}")
            send_line_reply_message(messaging_api, reply_token, [TextMessage(text="查詢參數不完整，請稍候再試。")])
            return True

        try:
            days = int(days_str)
        except ValueError:
            logger.error(f"天數參數無效: {days_str}")
            send_line_reply_message(messaging_api, reply_token, [TextMessage(text="天數參數錯誤，請再試一次。")])
            return True
        
        clear_user_state(user_id) # 清除狀態，完成一個對話流程

        # 獲取中央氣象署資料 (傳入鄉鎮市區名稱，因為使用 F-D0047-091)
        weather_data = get_cwa_forecast_data(api_key=CWA_API_KEY, location_name=county)
        
        if weather_data:
            logger.debug(f"接收到的 CWA API 原始資料: {json.dumps(weather_data, indent=2)[:2000]}...")
        else:
            logger.warning("get_cwa_forecast_data 未返回任何資料。")

        if not weather_data:
            logger.error("無法取得中央氣象署預報資料。")
            send_api_error_message(messaging_api, user_id, reply_token, f"{county}")
            return True

        # 解析天氣數據
        parsed_weather = parse_forecast_weather(weather_data, county)

        # 呼叫 debug helper 印出log
        debug_parsed_weather(parsed_weather, weather_data)

        if parsed_weather:
            # 格式化為 LINE 訊息
            response_message = build_forecast_weather_flex(parsed_weather, days)
            # 修改這裡，傳入 user_id
            send_line_reply_message(messaging_api, reply_token, [response_message], user_id=user_id)
            logger.info(f"已成功回覆用戶 {user_id} {county} 的 {days} 天天氣預報。")
            clear_user_state(user_id)
            return True
        else:
            logger.error(f"無法從取得的預報資料中解析出 {county} 的天氣資訊，或解析結果不完整。")
            send_api_error_message(messaging_api, user_id, reply_token, f"{county}")
            return True
    
    """
    # 處理查詢其他縣市+鄉鎮市區的 Postback (來自第一個選單的按鈕)
    elif "action=select_county_and_township_input" in postback_data:
        # 設定使用者狀態，讓下一個文字訊息被解析為完整的縣市+鄉鎮市區
        set_user_state(user_id, {"state": "expecting_full_location"})
        logger.debug(f"設定用戶 {user_id} 狀態為 'expecting_full_address_input'")

        # 回覆用戶，引導他們輸入完整的縣市+鄉鎮市區名稱
        reply_message_content = "請直接輸入您要查詢的縣市+鄉鎮市區名稱，例如：臺北市信義區"
        send_line_reply_message(messaging_api, reply_token, format_text_message(reply_message_content), user_id=user_id)
        logger.info(f"用戶 {user_id} 請求選擇其他縣市，已回覆引導訊息。")
        return True

    return False # 此 handler 沒有處理此 Postback
    """

logger.info("postback_handler.py 模組已載入。")