# life_reminders/weekend_handler.py
import json
import logging
from typing import Dict, List
from linebot.v3.messaging.models import Message, TextMessage, FlexMessage, FlexBubble, FlexCarousel
from linebot.v3.webhooks.models import PostbackEvent

from config import CWA_API_KEY

# 引入必要的工具函數和轉換器
from utils.api_helper import get_messaging_api
from utils.text_processing import normalize_city_name
from utils.user_data_manager import get_user_state, get_default_city
from utils.line_common_messaging import send_line_reply_message, send_api_error_message

from weather_forecast.cwa_forecast_api import get_cwa_forecast_data
from weather_forecast.weather_forecast_parser import parse_forecast_weather
# from life_reminders.weekend_weather_flex import build_weekend_weather_flex
from life_reminders.weekend_forecast_converter import get_weekend_forecast_flex_messages 

logger = logging.getLogger(__name__)

def handle_weekend_weather_postback(api, event) -> bool:
    """
    處理週末天氣預報的 Postback 事件。
    它將從用戶設定中獲取城市，調用氣象局 API，
    然後使用 weekend_forecast_converter 生成 Flex 訊息並回覆用戶。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    logger.info(f"處理週末天氣 postback，用戶: {user_id}")

    try:
        # 1. 獲取用戶設定的城市
        county_name = get_default_city(user_id)
        if not county_name:
            county_name = "臺中市" # 這裡可以設定一個最常用的預設城市
            logger.info(f"用戶 {user_id} 未設定預設城市，使用預設值：{county_name}")

        # 🚀 在這裡將 LOCATION_NAME 正規化
        normalized_location_name = normalize_city_name(county_name)

        # 2. 從中央氣象局 API 獲取天氣預報數據
        # 這裡會獲取完整的未來一週數據
        cwa_data = get_cwa_forecast_data(CWA_API_KEY, normalized_location_name)

        # cwa_data_for_log = json.loads(json.dumps(cwa_data, default=str)) # 處理不可序列化的對象
        # logger.debug(f"DEBUG: 原始 CWA API 回傳數據: {json.dumps(cwa_data_for_log, ensure_ascii=False, indent=2)}")

        if not cwa_data or not cwa_data.get("records"): # 檢查 cwa_data 是否為空或沒有 'records' 鍵
            send_line_reply_message(api, reply_token, [TextMessage(text=f"抱歉，無法取得 {county_name} 的天氣預報資訊。API 返回空數據或無效格式。")])
            return True
        
        # 2. 解析並格式化天氣數據 (得到可以直接用於 Flex Message 模板的字典)
        parsed_forecast_weather = parse_forecast_weather(cwa_data, normalized_location_name)
        
        if not parsed_forecast_weather or not parsed_forecast_weather.get("forecast_periods"):
            logger.error(f"無法從取得的即時觀測資料中解析或格式化出 {normalized_location_name} 的天氣資訊。")
            send_api_error_message(api, user_id, reply_token, normalized_location_name)
            return True # 即使出錯也表示這個 handler 嘗試處理了
        
        """
        # 3. 將格式化後的數據填充到 Flex Message 模板中 (得到 Flex Message 的字典結構)
        # 用你的 builder 產生 Flex JSON
        weather_flex_bubble = build_weekend_weather_flex(parsed_forecast_weather, county_name)

        # 檢查 format_forecast_weather_message 是否返回有效的字典 (而不是錯誤字串)
        if not isinstance(weather_flex_bubble, FlexBubble): # 檢查回傳的類型
            logger.error(f"build_weather_flex 返回了無效的 FlexBubble 物件: {type(weather_flex_bubble)}")
            # 這裡可以選擇發送一個通用的錯誤文字訊息，而不是嘗試再構建一次 FlexMessage
            error_message_obj = TextMessage(text=f"抱歉，無法顯示 {normalized_location_name} 的天氣資訊卡片。請稍候再試。")
            send_line_reply_message(api, reply_token, [error_message_obj])
            return True
        """
        
        # 3. 調用 weekend_forecast_converter 來篩選週末數據並生成 Flex Message
        # get_weekend_forecast_flex_messages 會負責從 cwa_data 中提取週末預報和穿搭建議
        weekend_weather_bubbles = get_weekend_forecast_flex_messages(parsed_forecast_weather)

        # 4. 準備要回覆給 LINE 平台的訊息列表
        messages_to_send: List[Message] = []

        if weekend_weather_bubbles:
            # 將多個 Flex Bubble 包裝在 FlexCarousel 中
            messages_to_send.append(FlexMessage(
                alt_text=f"{normalized_location_name} 週末天氣預報",
                contents=FlexCarousel(contents=weekend_weather_bubbles)
            ))
        else:
            logger.warning(f"沒有為 {normalized_location_name} 生成週末天氣預報 Flex Bubbles。")
            messages_to_send.append(TextMessage(text=f"目前沒有 {normalized_location_name} 的週末天氣預報資訊。"))

        """
        if weekend_outfit_bubbles:
            messages_to_send.append(FlexMessage(alt_text=f"{normalized_location_name} 週末穿搭建議",
            contents=FlexCarousel(contents=weekend_outfit_bubbles)
            ))
        else:
            logger.warning(f"沒有為 {normalized_location_name} 生成週末穿搭建議 Flex Bubbles。")
        """
        
        # 5. 發送回覆訊息
        if messages_to_send:
            send_line_reply_message(api, reply_token, messages_to_send)
            logger.info(f"✅ 成功發送 {normalized_location_name} 週末天氣預報和穿搭建議。")
            return True
        else:
            # 如果因為某些原因兩個列表都為空
            send_line_reply_message(api, reply_token, [TextMessage(text=f"抱歉，未能為 {normalized_location_name} 找到週末天氣預報訊息。")])
            return True

        """
        # 4. 將 Flex Message 字典轉換為 Line Bot SDK 的 FlexMessage 物件
        # 使用 line_common_messaging 中的 format_flex_message 函數
        flex_msg_to_send = FlexMessage(
            alt_text=f"{normalized_location_name} 即時天氣",
            contents=weather_flex_bubble # 直接傳入 FlexBubble 物件
        )

        # 5. 發送回覆訊息 (傳入 Line Bot SDK 的 Message 物件列表)
        # line_flex_message_object 已經是一個 FlexMessage 物件，將其放入列表中
        send_line_reply_message(api, reply_token, [flex_msg_to_send])
        return True # 訊息已處理
        """

    except Exception as e:
        logger.exception(f"處理週末天氣預報時發生錯誤: {e}")
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，查詢週末天氣時發生內部錯誤。")])
        return True