# life_reminders/outfit_handler.py
import json
import logging
from typing import List, Dict
from urllib.parse import parse_qs # 用於解析 Postback data
from linebot.v3.messaging.models import TextMessage, FlexMessage, FlexBubble, FlexCarousel
from linebot.v3.webhooks.models import PostbackEvent

from config import CWA_API_KEY

from utils.user_data_manager import get_default_city, clear_user_state
from utils.text_processing import normalize_city_name
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

from weather_today.cwa_3days_api import get_cwa_3days_data
from weather_today.weather_3days_parser import parse_3days_weather

from weather_today.uv_station_mapping import get_uv_station_id
from weather_today.today_uvindex_handler import get_uv_index_for_location

# 從新的路徑導入即時天氣 API 呼叫和解析器
from weather_current.cwa_current_api import get_cwa_current_data
from weather_current.weather_current_parser import parse_current_weather

from weather_forecast.cwa_forecast_api import get_cwa_forecast_data
from weather_forecast.weather_forecast_parser import parse_forecast_weather

# 🚀 從 life_reminders/outfit_responses.py 導入通用回覆選單函式
from life_reminders.outfit_responses import reply_outfit_weather_of_city

# 導入你的 Flex Message 定義
# 它會返回你想要作為「穿搭建議」入口選單的 Flex Message JSON 結構
from life_reminders.outfit_type_flex_messages import build_outfit_suggestions_flex
from life_reminders.outfit_flex_messages import build_today_outfit_flex, build_current_outfit_flex
# from life_reminders.forecast_outfit_flex_messages import build_forecast_outfit_carousel

from weather_forecast.forecast_flex_converter import convert_forecast_to_bubbles, build_flex_carousel

logger = logging.getLogger(__name__)

def handle_outfit_advisor(api, event: PostbackEvent) -> bool:
    """
    處理來自 Rich Menu 或其他入口的 "outfit_advisor" Postback。
    這通常是進入穿搭建議功能的第一步。
    根據用戶是否有預設城市，決定直接顯示選單還是提示輸入城市。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    logger.info(f"[OutfitHandler] 用戶 {user_id} 請求穿搭建議主選單。")

    # 獲取用戶的預設城市
    default_user_city = get_default_city(user_id)
    if default_user_city:
        default_city = normalize_city_name(default_user_city)
        logger.info(f"[OutfitHandler] 用戶 {user_id} 有預設城市 {default_city}，直接回覆穿搭建議類型選單。")
        return reply_outfit_weather_of_city(api, reply_token, user_id, default_city)
    else:
        send_line_reply_message(api, reply_token, [TextMessage(text="尚未設定預設城市")])
        logger.info(f"[OutfitHandler] 用戶 {user_id} 無預設城市")
        return True

    logger.debug(f"[OutfitHandler] 用戶 {user_id} 的預設城市 (from DB): {default_city_display}")

    # 呼叫 outfit_flex_messages.py 中用於取得選單 Flex 的函式
    flex_message_object = build_outfit_suggestions_flex(target_query_city=target_city, default_city_display=default_city_display)

    if flex_message_object:
        send_line_reply_message(api, reply_token, [flex_message_object])
        logger.info(f"[OutfitHandler] 成功回覆穿搭建議主選單給 {user_id}。")
        return True
    else:
        logger.error(f"[OutfitHandler] build_outfit_suggestions_flex 返回 None 或空。Flex Message 可能有問題。")
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法載入穿搭建議選單，請稍候再試。")])
        return False

        if not flex_message_object:
            logger.error("[OutfitHandler] 無法取得穿搭建議選單的 Flex 內容。")
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，目前無法提供穿搭建議選項。請稍候再試。")])
            return True

        # 將 Flex Message 轉換為 Line SDK 的 FlexMessage 物件
        # flex_message_object = format_flex_message("穿搭建議選單", flex_json_content)

        """
        # 檢查 format_flex_message 是否有降級處理返回 TextMessage
        if isinstance(flex_message_object, TextMessage):
            send_line_reply_message(api, reply_token, [flex_message_object])
        elif isinstance(flex_message_object, FlexMessage): # 確保是 FlexMessage 類型
            send_line_reply_message(api, reply_token, [flex_message_object])
        else:
            # 如果 format_flex_message 返回了意料之外的類型，也需要處理
            logger.error(f"[OutfitHandler] format_flex_message 返回了未預期的類型: {type(flex_message_object)}")
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，生成穿搭建議時發生未知錯誤。")])
        """

        logger.info(f"[OutfitHandler] 已向用戶 {user_id} 發送穿搭建議 Flex Message 選單。")
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
    target_query_city = parsed_data.get('city', [None])[0] # 查詢城市，如果沒有則使用預設城市
    # query_value = parsed_data.get('value', [None])[0] # 查詢值，例如 'cold', 'casual'
    
    logger.info(f"[OutfitHandler] 用戶 {user_id} 請求穿搭查詢: 類型={query_type}。")

    """
    if CWA_API_KEY == "YOUR_CWB_API_KEY" or not CWA_API_KEY: # 檢查 API 金鑰是否有效
        send_line_reply_message(api, reply_token, [TextMessage(text="錯誤：未設定中央氣象署 API 金鑰。")])
        return True
    """

    # 檢查是否成功獲取到查詢城市
    if not target_query_city:
        logger.error(f"[OutfitHandler] 無法從 Postback data 中獲取查詢城市。")
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，查詢城市資訊不完整，請稍候再試。")])
        clear_user_state(user_id) # 清除可能存在的狀態
        return True

    try:
        # user_city = get_default_city(user_id)

        if query_type == "today":
            # --- 1. 獲取 F-C0032-001 數據 (整體天氣概況) ---
            raw_general_data = get_cwa_today_data(api_key=CWA_API_KEY, location_name=target_query_city) # 假設用戶在台中市
            logger.debug(f"DEBUG: raw_general_data content: {raw_general_data}")
            logger.debug(f"DEBUG: raw_general_data type: {type(raw_general_data)}")
            if not raw_general_data:
                logger.error(f"無法取得 {target_query_city} 的整體天氣概況資料 (F-C0032-001)。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法取得 {target_query_city} 的今日天氣概況數據，請稍候再試。")])
                return True
            
            # 2. 解析原始即時天氣數據 (使用 weather_current_parser)
            # 這裡的 parsed_from_current_api 現在會直接傳給 outfit_logic
            general_forecast_parsed = parse_today_weather(raw_general_data, location_name=target_query_city)
            
            # --- 在這裡新增日誌 ---
            logger.debug(f"DEBUG: general_forecast_parsed content: {general_forecast_parsed}")

            if not general_forecast_parsed:
                logger.error(f"無法解析或格式化 {target_query_city} 的今日天氣概況資訊 (F-C0032-001)。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法解析 {user_city} 的今日天氣概況數據以提供建議。")])
                return True
            
            # --- 2. 獲取 F-D0047-089 數據 (逐時詳細預報) ---
            raw_hourly_data = get_cwa_3days_data(api_key=CWA_API_KEY, location_name=target_query_city)
            if not raw_hourly_data:
                logger.error(f"無法取得 {target_query_city} 的逐時天氣資料 (F-D0047-089)。")
                send_line_reply_message(api, reply_token, [TextMessage(text=f"抱歉，無法取得 {target_query_city} 的詳細天氣數據，請稍候再試。")])
                return True
            
            # 2. 解析原始即時天氣數據
            hourly_forecast_parsed = parse_3days_weather(raw_hourly_data, location_name=target_query_city)
            if not hourly_forecast_parsed:
                logger.error(f"無法從逐時天氣資料中解析或格式化 {target_query_city} 的天氣資訊 (F-D0047-089)。")
                send_line_reply_message(api, reply_token, [TextMessage(text=f"抱歉，無法解析 {target_query_city} 的詳細天氣數據以提供建議。")])
                return True
            
            # --- 新增: 獲取紫外線指數 (O-A0005-001) ---
            # 使用 get_uv_station_id 函式來動態獲取測站 ID
            uv_station_id = get_uv_station_id(target_query_city)
            uv_data_parsed = None # 初始化為 None
    
            if uv_station_id:
                logger.info(f"為城市 '{target_query_city}' 找到對應的紫外線測站 ID: {uv_station_id}")
                uv_data_parsed = get_uv_index_for_location(CWA_API_KEY, uv_station_id)
                if not uv_data_parsed:
                    logger.warning(f"雖然找到了測站 ID '{uv_station_id}'，但無法取得 {target_query_city} 的紫外線指數資料 (O-A0005-001)。建議將不會包含紫外線資訊。")
            else:
                logger.warning(f"未能為城市 '{target_query_city}' 找到對應的紫外線測站 ID。將不查詢紫外線資訊。")
                # uv_data_parsed 保持為 None
            
            # --- 3. 調用核心邏輯生成天氣推播和穿搭建議 ---
            # 這裡將所有解析後的數據 (包括紫外線指數) 傳遞給 get_outfit_suggestion_for_today_weather
            outfit_info_for_today_flex = get_outfit_suggestion_for_today_weather(
                location=target_query_city,
                hourly_forecast=hourly_forecast_parsed,
                general_forecast=general_forecast_parsed,
                uv_data=uv_data_parsed  # 傳入紫外線指數數據
            )

            if not outfit_info_for_today_flex:
                logger.error(f"無法從 today_outfit_logic 生成 {target_query_city} 的今日穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法生成今日穿搭建議。")])
                return True

            # 4. 生成 Flex Bubble
            flex_bubble_content_today = build_today_outfit_flex(
                outfit_info=outfit_info_for_today_flex, location_name=target_query_city
            )
            
            if not isinstance(flex_bubble_content_today, FlexBubble):
                logger.error(f"build_today_outfit_flex 返回了無效的 FlexBubble 物件，類型: {type(flex_bubble_content_today)}")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，今日穿搭建議卡片生成失敗 (內部錯誤)。")])
                return True
            
            # 5. 包裝成 FlexMessage 並發送
            alt_text = f"{target_query_city} 今日穿搭建議"
            flex_message_to_send = FlexMessage(
                alt_text=alt_text, contents=flex_bubble_content_today
            )

            send_line_reply_message(api, reply_token, [flex_message_to_send])
            logger.info(f"成功為 {user_id} 發送 {target_query_city} 的今日穿搭建議 (Flex Message)。")
            return True

            """
            #✅ 直接使用 FlexMessage 建構（不是 FlexSendMessage，也不需要 format_flex_message）
            flex_message_to_send = format_flex_message(alt_text, flex_json_to_format)
            send_line_reply_message(api, reply_token, [flex_message_to_send])
            logger.info(f"成功為 {user_id} 發送 {user_city} 的今日穿搭建議 (Flex Message)。")
            return True
            """

        # 這裡根據 query_type 來獲取數據並構建 Flex Message
        elif query_type == "current":
            # 獲取即時天氣數據 (假設你需要用戶的城市，這裡暫時寫死或從用戶設定中獲取)
            # 你需要自行實作 get_current_weather_data
            current_weather = get_cwa_current_data(api_key=CWA_API_KEY, location_name=target_query_city) # 假設用戶在台中市
            if not current_weather:
                logger.error(f"無法取得 {target_query_city} 的即時觀測資料。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法取得即時天氣數據，請稍候再試。")])
                return True

            # 2. 解析原始即時天氣數據 (使用 weather_current_parser)
            # 這裡的 parsed_from_current_api 現在會直接傳給 outfit_logic
            parsed_from_current_api = parse_current_weather(current_weather, target_query_city)
            if not parsed_from_current_api:
                logger.error(f"無法從即時觀測資料中解析或格式化 {target_query_city} 的天氣資訊。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法解析即時天氣數據以提供穿搭建議。")])
                return True
            
            # 3. 直接將解析後的即時數據傳給 outfit_logic 函數
            outfit_info = get_outfit_suggestion_for_current_weather(parsed_from_current_api)
            if not outfit_info: # 檢查 get_outfit_suggestion_for_current_weather 是否成功返回數據
                logger.error(f"無法生成 {target_query_city} 的即時穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法生成即時穿搭建議。")])
                return True
            
            # 4. 生成 Flex Bubble
            flex_bubble_content = build_current_outfit_flex(outfit_info, location_name=target_query_city)
            # 檢查 build_current_outfit_flex 是否返回了有效的 FlexBubble
            if not isinstance(flex_bubble_content, FlexBubble):
                logger.error(f"build_current_outfit_flex 返回了無效的 FlexBubble 物件，類型: {type(flex_bubble_content)}")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，穿搭建議卡片生成失敗 (內部錯誤)。")])
                return True

            # 5. 包裝成 FlexMessage
            alt_text = f"{target_query_city} 即時穿搭建議"
            flex_message_to_send = FlexMessage(
                alt_text=alt_text, contents=flex_bubble_content
            )

            send_line_reply_message(api, reply_token, [flex_message_to_send])
            logger.info(f"成功為 {user_id} 發送 {target_query_city} 的即時穿搭建議 (Flex Message)。")
            return True

            """
            #✅ 直接使用 FlexMessage 建構（不是 FlexSendMessage，也不需要 format_flex_message）
            flex_message_to_send = format_flex_message(alt_text, flex_json_to_format)
            """
            
        elif query_type == "forecast":
            # 獲取未來天氣預報數據 (假設你需要用戶的城市，這裡暫時寫死)
            # 你需要自行實作 get_forecast_weather_data
            days = 7  # 預設為查詢未來 7 天的預報

            logger.info(f"用戶 {user_id} 請求未來 {days} 天的預報和穿搭建議。")

            forecast_weather = get_cwa_forecast_data(api_key=CWA_API_KEY, location_name=target_query_city) # 假設用戶在台中市
            if not forecast_weather:
                logger.error(f"無法取得 {target_query_city} 的未來預報資料。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法取得未來預報數據，請稍候再試。")])
                return True

            # 2. 解析原始未來天氣數據，得到一個包含多天數據的列表
            # 每個元素應該是單一天的詳細天氣數據字典
            parsed_full_forecast = parse_forecast_weather(forecast_weather, target_query_city)
            if not parsed_full_forecast or not parsed_full_forecast.get('forecast_periods'):
                logger.error(f"無法從未來預報資料中解析或格式化 {target_query_city} 的天氣資訊，或缺少 'forecast_periods' 鍵。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法解析未來預報數據以提供穿搭建議。")])
                return True
            
            try:
                # 這裡調用 convert_forecast_to_bubbles，它會返回兩個 FlexBubble 列表
                # 第一個是天氣預報的 Bubble 列表
                # 第二個是穿搭建議的 Bubble 列表 (這已在 forecast_flex_converter 中生成好)
                _, outfit_bubbles = \
                    convert_forecast_to_bubbles(parsed_full_forecast, days, include_outfit_suggestions=True)

                messages_to_send: List[FlexMessage | TextMessage] = []

                if outfit_bubbles:
                    outfit_flex_message = build_flex_carousel(outfit_bubbles, alt_text=f"{target_query_city} 未來 {days} 天穿搭建議")
                    messages_to_send.append(outfit_flex_message)
                else:
                    logger.warning(f"未能生成 {target_query_city} 的穿搭建議卡片。")
                    messages_to_send.append(TextMessage(text=f"抱歉，未能為 {target_query_city} 生成穿搭建議。"))

                if not messages_to_send:
                    logger.error(f"為 {target_query_city} 生成訊息失敗，無任何訊息可發送。")
                    send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法提供預報資訊。")])
                    return True

                send_line_reply_message(api, reply_token, messages_to_send)
                logger.info(f"成功發送 {target_query_city} 未來 {days} 天的穿搭建議。")
                return True

            except Exception as e:
                logger.exception(f"處理未來穿搭建議時發生錯誤: {e}")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，處理未來預報時發生系統錯誤，請稍候再試。")])
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
            # logger.debug(f"[OutfitHandler] daily_outfit_suggestions = {daily_outfit_suggestions}")
            flex_json_content = build_forecast_outfit_carousel(daily_outfit_suggestions, location_name=user_city)
            
            # 在這裡添加一個臨時的 debug log，確認 flex_json_content 的類型和內容
            # logger.debug(f"DEBUG: build_forecast_outfit_carousel 返回的原始 flex_json_content 類型: {type(flex_json_content)}")
            # logger.debug(f"DEBUG: build_forecast_outfit_carousel 返回的原始 flex_json_content 內容: {json.dumps(flex_json_content, indent=2, ensure_ascii=False)}")
            
            alt_text = f"{user_city} 未來穿搭建議 (1-7天)"

            """
            #✅ 直接使用 FlexMessage 建構（不是 FlexSendMessage，也不需要 format_flex_message）
            flex_message_to_send = format_flex_message(alt_text, flex_json_to_format)
            """
            
        # 未知的查詢類型
        else:
            logger.warning(f"[OutfitHandler] 未知的穿搭查詢類型: {query_type}")
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法識別的穿搭建議類型。")])
            return True
        
        # 統一檢查並發送 Flex Message
        if flex_json_content:
            flex_message_to_send = format_flex_message(alt_text, flex_json_content)
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