# outfit_suggestion/outfit_handler.py
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
from outfit_suggestion.today_outfit_logic import get_outfit_suggestion_for_today_weather
from outfit_suggestion.current_outfit_logic import get_outfit_suggestion_for_current_weather 
from outfit_suggestion.forecast_outfit_logic import get_outfit_suggestion_for_forecast_weather

# 導入我們新的數據聚合器
from weather_today.today_weather_aggregator import get_today_all_weather_data

from weather_current.current_handler import fetch_and_parse_weather_data

from weather_forecast.postback_handler import fetch_and_parse_forecast_data

# 🚀 從 life_reminders/outfit_responses.py 導入通用回覆選單函式
from outfit_suggestion.outfit_responses import reply_outfit_weather_of_city

# 導入你的 Flex Message 定義
# 它會返回你想要作為「穿搭建議」入口選單的 Flex Message JSON 結構
from outfit_suggestion.outfit_type_flex_messages import build_outfit_suggestions_flex
from outfit_suggestion.outfit_flex_messages import build_today_outfit_flex, build_current_outfit_flex
# from life_reminders.forecast_outfit_flex_messages import build_forecast_outfit_carousel

from weather_forecast.forecast_flex_converter import build_flex_carousel, convert_forecast_to_bubbles

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
            # 1. 使用數據聚合器取得該城市所有天氣預報數據
            # 這裡的 all_weather_data 包含了來自多個 API 的所有資訊
            all_weather_data = get_today_all_weather_data(target_query_city)
            # 集中處理無法獲取數據的情況
            if not all_weather_data:
                logger.error(f"無法為 {target_query_city} 取得完整的今日天氣數據。")
                send_line_reply_message(api, reply_token, [TextMessage(text=f"抱歉，無法取得 {target_query_city} 的天氣數據，請稍候再試。")])
                return True
            
            # 2. 從聚合後的字典中提取建立 Flex Message 所需的參數
            # 聚合器已處理了所有預設值，所以這裡的程式碼是安全的
            location = all_weather_data.get("locationName", target_query_city)
            general_forecast = all_weather_data.get("general_forecast", {})
            hourly_forecast = all_weather_data.get("hourly_forecast", [])
            uv_data = all_weather_data.get("uv_data", {}) # uv_data 現在是一個字典，不會是 None
            
            # --- 3. 調用核心邏輯生成天氣推播和穿搭建議 ---
            # 這裡將所有解析後的數據 (包括紫外線指數) 傳遞給 get_outfit_suggestion_for_today_weather
            outfit_info_for_today_flex = get_outfit_suggestion_for_today_weather(
                location=location,
                hourly_forecast=hourly_forecast,
                general_forecast=general_forecast,
                uv_data=uv_data  # 傳入紫外線指數數據
            )

            if not outfit_info_for_today_flex:
                logger.error(f"無法從 today_outfit_logic 生成 {target_query_city} 的今日穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法生成今日穿搭建議。")])
                return True

            # 4. 生成 Flex Bubble
            flex_bubble_content_today = build_today_outfit_flex(
                outfit_info=outfit_info_for_today_flex, location_name=location
            )
            
            if not isinstance(flex_bubble_content_today, FlexBubble):
                logger.error(f"build_today_outfit_flex 返回了無效的 FlexBubble 物件，類型: {type(flex_bubble_content_today)}")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，今日穿搭建議卡片生成失敗 (內部錯誤)。")])
                return True
            
            # 5. 包裝成 FlexMessage 並發送
            alt_text = f"{location} 今日穿搭建議"
            flex_message_to_send = FlexMessage(
                alt_text=alt_text, contents=flex_bubble_content_today
            )

            send_line_reply_message(api, reply_token, [flex_message_to_send])
            logger.info(f"成功為 {user_id} 發送 {location} 的今日穿搭建議 (Flex Message)。")
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
            # 獲取即時天氣數據並解析
            current_weather_data = fetch_and_parse_weather_data(city_name=target_query_city)
            # 1. 檢查共用函式是否成功回傳數據
            if not current_weather_data:
                # 如果失敗，fetch_and_parse_weather_data 會在內部記錄錯誤，
                # 我們在這裡發送通用的錯誤訊息即可。
                logger.error(f"無法取得或解析 {target_query_city} 的即時天氣數據，無法提供穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法取得即時天氣數據以提供穿搭建議。")])
                return True
            
            # 2. 將解析後的即時數據傳給 outfit_logic 函數
            outfit_info = get_outfit_suggestion_for_current_weather(current_weather_data)
            if not outfit_info: # 檢查 get_outfit_suggestion_for_current_weather 是否成功返回數據
                logger.error(f"無法生成 {target_query_city} 的即時穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法生成即時穿搭建議。")])
                return True
            
            # 3. 生成 Flex Bubble
            flex_bubble_content = build_current_outfit_flex(outfit_info, location_name=target_query_city)
            # 檢查 build_current_outfit_flex 是否返回了有效的 FlexBubble
            if not isinstance(flex_bubble_content, FlexBubble):
                logger.error(f"build_current_outfit_flex 返回了無效的 FlexBubble 物件，類型: {type(flex_bubble_content)}")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，穿搭建議卡片生成失敗 (內部錯誤)。")])
                return True

            # 4. 包裝成 FlexMessage
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
            # 預設為查詢未來 7 天的預報
            days = 7

            logger.info(f"用戶 {user_id} 請求未來 {days} 天的預報和穿搭建議。")

            # 1. 呼叫共用函式來獲取並解析預報天氣數據
            parsed_full_forecast = fetch_and_parse_forecast_data(city_name=target_query_city)

            # 檢查共用函式是否成功回傳數據
            if not parsed_full_forecast:
                # 如果失敗，_fetch_and_parse_forecast_data 會在內部記錄錯誤，
                # 我們在這裡發送一個通用的錯誤訊息即可。
                logger.error(f"無法取得或解析 {target_query_city} 的未來預報數據，無法提供穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法取得未來預報數據以提供穿搭建議。")])
                return True
            
            # 2. 將解析後的即時數據傳給 outfit_logic 函數
            outfit_info = get_outfit_suggestion_for_forecast_weather(parsed_full_forecast)
            if not outfit_info: # 檢查 get_outfit_suggestion_for_current_weather 是否成功返回數據
                logger.error(f"無法生成 {target_query_city} 的即時穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法生成即時穿搭建議。")])
                return True
            
            try:
                # 3. 調用 convert_forecast_to_bubbles，它會返回兩個 FlexBubble 列表
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