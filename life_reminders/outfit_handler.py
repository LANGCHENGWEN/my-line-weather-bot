# life_reminders/outfit_handler.py
import json
import logging
import datetime
from linebot.v3.messaging.models import TextMessage, FlexMessage
from linebot.v3.webhooks.models import PostbackEvent
from urllib.parse import parse_qs # 用於解析 Postback data

from config import CWA_API_KEY

from utils.user_data_manager import get_default_city
# 導入訊息建構工具 (用於將 Flex JSON 轉換為 Line SDK 物件)
from utils.message_builder import format_flex_message
# 導入通用工具
from utils.line_common_messaging import send_line_reply_message

# 導入穿搭邏輯
from utils.today_outfit_logic import get_outfit_suggestion_for_today_weather
from utils.current_outfit_logic import get_outfit_suggestion_for_current_weather 
from utils.forecast_outfit_logic import get_outfit_suggestion_for_forecast_weather

from weather_today.cwa_today_api import get_cwa_today_data
from weather_today.weather_today_parser import parse_today_weather

# 從新的路徑導入即時天氣 API 呼叫和解析器
from weather_current.cwa_current_api import get_cwa_current_data
from weather_current.weather_current_parser import parse_current_weather

from weather_forecast.cwa_forecast_api import get_cwa_forecast_data
from weather_forecast.weather_forecast_parser import parse_forecast_weather

# 導入你的 Flex Message 定義
# 它會返回你想要作為「穿搭建議」入口選單的 Flex Message JSON 結構
from life_reminders.outfit_type_flex_messages import build_outfit_suggestions_flex
from life_reminders.outfit_flex_messages import build_today_outfit_flex, build_current_outfit_flex
from life_reminders.forecast_outfit_flex_messages import build_forecast_outfit_carousel

logger = logging.getLogger(__name__)

def handle_outfit_advisor(api, event: PostbackEvent) -> bool:
    """
    處理 "outfit_advisor" 的 Postback 動作。
    這通常在使用者初次進入穿搭建議功能時觸發。
    它應該回覆一個包含穿搭查詢選項的 Flex Message 選單。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    
    logger.info(f"[OutfitHandler] 用戶 {user_id} 請求穿搭建議主選單。")

    try:
        # 呼叫 outfit_flex_messages.py 中用於取得選單 Flex JSON 的函數
        flex_json_content = build_outfit_suggestions_flex() 

        if not flex_json_content:
            logger.error("[OutfitHandler] 無法取得穿搭建議選單的 Flex JSON 內容。")
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，目前無法提供穿搭建議選項。請稍候再試。")])
            return True

        # 將 Flex Message JSON 轉換為 Line SDK 的 FlexMessage 物件
        flex_message_object = format_flex_message("穿搭建議選單", flex_json_content)

        # 檢查 format_flex_message 是否有降級處理返回 TextMessage
        if isinstance(flex_message_object, TextMessage):
            send_line_reply_message(api, reply_token, [flex_message_object])
        elif isinstance(flex_message_object, FlexMessage): # 確保是 FlexMessage 類型
            send_line_reply_message(api, reply_token, [flex_message_object])
        else:
            # 如果 format_flex_message 返回了意料之外的類型，也需要處理
            logger.error(f"[OutfitHandler] format_flex_message 返回了未預期的類型: {type(flex_message_object)}")
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，生成穿搭建議時發生未知錯誤。")])
        
        logger.info(f"[OutfitHandler] 已向用戶 {user_id} 發送穿搭建議 Flex Message 選單。")
        return True

    except Exception as e:
        logger.exception(f"[OutfitHandler] 處理 outfit_advisor 時發生錯誤，用戶: {user_id}: {e}")
        send_line_reply_message(api, reply_token, [TextMessage(text="處理穿搭建議時發生錯誤，請稍候再試。")])
        return True

def handle_outfit_query(api, event: PostbackEvent) -> bool:
    """
    處理更具體的 "outfit_query" Postback 動作 (例如：今日、即時、未來穿搭建議)。
    此函數會解析 Postback data 中的參數，並根據天氣數據提供客製化的穿搭建議。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    data = event.postback.data # 例如: 'action=outfit_query&type=temperature&value=cold'
    parsed_data = parse_qs(data) # 解析 Postback data 為字典

    query_type = parsed_data.get('type', [None])[0] # 查詢類型，例如 'temperature', 'occasion'
    # query_value = parsed_data.get('value', [None])[0] # 查詢值，例如 'cold', 'casual'
    
    logger.info(f"[OutfitHandler] 用戶 {user_id} 請求穿搭查詢: 類型={query_type}。")

    try:
        flex_json_content = None
        alt_text = "穿搭建議"

        user_city = get_default_city(user_id)

        if query_type == "today":
            # "今日穿搭建議"可以視為即時穿搭的一種
            today_weather = get_cwa_today_data(api_key=CWA_API_KEY, location_name=user_city) # 假設用戶在台中市
            
            if not today_weather:
                logger.error(f"無法取得 {user_city} 的今日天氣資料。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法取得今日天氣數據，請稍候再試。")])
                return True
            
            # 2. 解析原始即時天氣數據 (使用 weather_current_parser)
            # 這裡的 parsed_from_current_api 現在會直接傳給 outfit_logic
            parsed_from_today_api = parse_today_weather(today_weather, user_city)

            if not parsed_from_today_api:
                logger.error(f"無法從今日天氣資料中解析或格式化 {user_city} 的天氣資訊。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法解析今日天氣數據以提供穿搭建議。")])
                return True
            
            # 3. 直接將解析後的即時數據傳給 outfit_logic 函數
            outfit_info = get_outfit_suggestion_for_today_weather(parsed_from_today_api)
            alt_text = f"{user_city} 今日穿搭建議"

            flex_json_to_format = build_today_outfit_flex(outfit_info, location_name=user_city)

            #✅ 直接使用 FlexMessage 建構（不是 FlexSendMessage，也不需要 format_flex_message）
            flex_message_to_send = format_flex_message(alt_text, flex_json_to_format)

        # 這裡根據 query_type 來獲取數據並構建 Flex Message
        elif query_type == "current":
            # 獲取即時天氣數據 (假設你需要用戶的城市，這裡暫時寫死或從用戶設定中獲取)
            # 你需要自行實作 get_current_weather_data
            current_weather = get_cwa_current_data(api_key=CWA_API_KEY, location_name=user_city) # 假設用戶在台中市
            
            if not current_weather:
                logger.error(f"無法取得 {user_city} 的即時觀測資料。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法取得即時天氣數據，請稍候再試。")])
                return True

            # 2. 解析原始即時天氣數據 (使用 weather_current_parser)
            # 這裡的 parsed_from_current_api 現在會直接傳給 outfit_logic
            parsed_from_current_api = parse_current_weather(current_weather, user_city)

            if not parsed_from_current_api:
                logger.error(f"無法從即時觀測資料中解析或格式化 {user_city} 的天氣資訊。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法解析即時天氣數據以提供穿搭建議。")])
                return True
            
            # 3. 直接將解析後的即時數據傳給 outfit_logic 函數
            outfit_info = get_outfit_suggestion_for_current_weather(parsed_from_current_api)
            alt_text = f"{user_city} 即時穿搭建議"

            flex_json_to_format = build_current_outfit_flex(outfit_info, location_name=user_city)

            #✅ 直接使用 FlexMessage 建構（不是 FlexSendMessage，也不需要 format_flex_message）
            flex_message_to_send = format_flex_message(alt_text, flex_json_to_format)

        elif query_type == "forecast":
            # 獲取未來天氣預報數據 (假設你需要用戶的城市，這裡暫時寫死)
            # 你需要自行實作 get_forecast_weather_data
            forecast_weather = get_cwa_forecast_data(api_key=CWA_API_KEY, location_name=user_city) # 假設用戶在台中市
            
            if not forecast_weather:
                logger.error(f"無法取得 {user_city} 的未來預報資料。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法取得未來預報數據，請稍候再試。")])
                return True

            # 2. 解析原始未來天氣數據，得到一個包含多天數據的列表
            # 每個元素應該是單一天的詳細天氣數據字典
            parsed_full_forecast = parse_forecast_weather(forecast_weather, user_city)

            if not parsed_full_forecast or 'forecast_periods' not in parsed_full_forecast:
                logger.error(f"無法從未來預報資料中解析或格式化 {user_city} 的天氣資訊，或缺少 'forecast_periods' 鍵。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法解析未來預報數據以提供穿搭建議。")])
                return True
            
            # 從完整的解析結果中取出 daily_forecast_data 列表
            # 這是實際包含每天數據的列表
            daily_forecast_data = parsed_full_forecast.get('forecast_periods', [])

            if not daily_forecast_data:
                logger.error(f"解析後 {user_city} 的未來預報資料中 'forecast_periods' 為空。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，未來幾天沒有可用的預報數據。")])
                return True
            
            # 3. 為每一天的數據生成穿搭建議
            daily_outfit_suggestions = []
            for day_data in daily_forecast_data:
                if not isinstance(day_data, dict):
                    logger.warning(f"跳過非字典類型的預報數據: {day_data}")
                    continue

                # 將單一天的數據包裝成列表傳遞給 get_outfit_suggestion_for_forecast_weather
                outfit_info_for_day = get_outfit_suggestion_for_forecast_weather([day_data])
                daily_outfit_suggestions.append(outfit_info_for_day)

            if not daily_outfit_suggestions:
                logger.error(f"未能為 {user_city} 生成任何穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，未能生成未來穿搭建議，請稍候再試。")])
                return True

            # 4. 使用 build_forecast_outfit_carousel 構建可滑動的 Flex Message
            # daily_outfit_suggestions 是一個列表，其中包含了每一天的 outfit_info 字典
            logger.debug(f"[OutfitHandler] daily_outfit_suggestions = {daily_outfit_suggestions}")
            flex_json_to_format = build_forecast_outfit_carousel(daily_outfit_suggestions, location_name=user_city)
            
            # 在這裡添加一個臨時的 debug log，確認 flex_json_content 的類型和內容
            logger.debug(f"DEBUG: build_forecast_outfit_carousel 返回的原始 flex_json_content 類型: {type(flex_json_content)}")
            logger.debug(f"DEBUG: build_forecast_outfit_carousel 返回的原始 flex_json_content 內容: {json.dumps(flex_json_content, indent=2, ensure_ascii=False)}")
            
            alt_text = f"{user_city} 未來穿搭建議 (1-7天)"

            #✅ 直接使用 FlexMessage 建構（不是 FlexSendMessage，也不需要 format_flex_message）
            flex_message_to_send = format_flex_message(alt_text, flex_json_to_format)
        
        else:
            logger.warning(f"[OutfitHandler] 未知的穿搭查詢類型: {query_type}")
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法識別的穿搭建議類型。")])
            return True
        
        # 統一檢查並發送 Flex Message
        if flex_message_to_send:
            if not isinstance(flex_message_to_send, FlexMessage):
                logger.error(f"[OutfitHandler] 錯誤！flex_message_to_send 的類型不是 FlexMessage，而是 {type(flex_message_to_send)}")
                send_line_reply_message(api, reply_token, [TextMessage(text="內部錯誤：訊息類型不符。")])
                return True

            # ===> 關鍵修正點 <===
            # logger.debug("DEBUG: 最終準備發送的 FlexMessage 物件內容 (用於確認):\n%s", json.dumps(flex_message_to_send.as_json(), indent=2, ensure_ascii=False, default=str))
            send_line_reply_message(api, reply_token, [flex_message_to_send])
            logger.info(f"[OutfitHandler] 已向用戶 {user_id} 發送 {query_type} 特定穿搭建議。")
            return True
        else:
            logger.error(f"[OutfitHandler] 即使有天氣數據，仍然無法取得 {query_type} 的 Flex JSON 內容。")
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法生成穿搭建議卡片。")])
            return True

        """
        #✅ 直接使用 FlexMessage 建構（不是 FlexSendMessage，也不需要 format_flex_message）
        flex_message_object = FlexMessage(alt_text=alt_text, contents=flex_json_content)

        # 5. 發送 Flex Message
        logger.debug(f"完整 Flex payload: {json.dumps(flex_message_object.as_json(), ensure_ascii=False, indent=2)}")
        send_line_reply_message(api, reply_token, [flex_message_object])
        
        logger.info(f"[OutfitHandler] 已向用戶 {user_id} 發送 {query_type} 特定穿搭建議。")
        return True
        """

    except Exception as e:
        logger.exception(f"[OutfitHandler] 處理 outfit_query 時發生錯誤，用戶: {user_id}: {e}")
        send_line_reply_message(api, reply_token, [TextMessage(text="處理穿搭建議查詢時發生錯誤，請稍候再試。")])
        return True

logger.info("穿搭建議處理器已載入。")