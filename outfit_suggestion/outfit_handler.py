# outfit_suggestion/outfit_handler.py
"""
穿搭建議功能的核心處理器。
處理來自 LINE Bot 與穿搭建議相關的 Postback 事件。
`handle_outfit_advisor` 用於處理用戶進入穿搭功能時的入口點。
`handle_outfit_query` 根據用戶選擇的時段（如今日、即時、未來預報）來提供相應的穿搭建議。
這個處理器將數據獲取、穿搭建議邏輯判斷和最終的訊息呈現三個步驟串連起來，實現一個完整且模組化的穿搭建議服務。
"""
import logging
from typing import List
from urllib.parse import parse_qs # 用於解析 Postback data
from linebot.v3.messaging.models import TextMessage, FlexBubble, FlexMessage
from linebot.v3.webhooks.models import PostbackEvent

from utils.text_processing import normalize_city_name
from utils.line_common_messaging import send_line_reply_message
from utils.firestore_manager import clear_user_state, get_default_city

# 導入獲取或解析數據的函式
from weather_today.today_weather_aggregator import get_today_all_weather_data
from weather_current.current_handler import fetch_and_parse_weather_data
from weather_forecast.postback_handler import fetch_and_parse_forecast_data

# 導入穿搭建議邏輯
from outfit_suggestion.today_outfit_logic import get_outfit_suggestion_for_today_weather
from outfit_suggestion.current_outfit_logic import get_outfit_suggestion_for_current_weather 
from outfit_suggestion.forecast_outfit_logic import get_outfit_suggestion_for_forecast_weather

# 導入回覆穿搭建議時段 Flex Message 的函式
from outfit_suggestion.outfit_responses import reply_outfit_weather_of_city

# 導入穿搭建議 Flex Message
from outfit_suggestion.outfit_flex_messages import build_today_outfit_flex, build_current_outfit_flex
from weather_forecast.forecast_flex_converter import build_flex_carousel, convert_forecast_to_bubbles

logger = logging.getLogger(__name__)

def handle_outfit_advisor(api, event: PostbackEvent) -> bool:
    """
    處理來自 Rich Menu 或其他入口的 "outfit_advisor" Postback。
    此函式是進入穿搭建議功能的第一步，會檢查用戶是否已設定預設城市。
    如果有，直接回覆一個穿搭建議時段 Flex Message；如果沒有，則會提示用戶先設定城市。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    logger.info(f"[OutfitHandler] 用戶 {user_id} 請求穿搭建議主選單。")

    # --- 檢查用戶是否已經設定了預設城市 ---
    # 所有與天氣相關的功能都需要一個指定的城市
    # 通過在功能入口處就進行檢查，可以避免後續在沒有城市資訊的情況下處理邏輯，減少不必要的 API 請求和錯誤，並引導用戶完成必要的設定
    default_user_city = get_default_city(user_id)
    if default_user_city:
        default_city = normalize_city_name(default_user_city)
        logger.info(f"[OutfitHandler] 用戶 {user_id} 有預設城市 {default_city}，直接回覆穿搭建議時段 Flex Message 。")
        return reply_outfit_weather_of_city(api, reply_token, user_id, default_city)
    else:
        send_line_reply_message(api, reply_token, [TextMessage(text="尚未設定預設城市")])
        logger.info(f"[OutfitHandler] 用戶 {user_id} 無預設城市")
        return True

def handle_outfit_query(api, event: PostbackEvent) -> bool:
    """
    處理更具體的 "outfit_query" Postback 動作 (例如：今日、即時、未來穿搭建議)。
    此函式會解析 Postback data 中的參數，並根據用戶的選擇調用對應的數據獲取和邏輯處理函式。
    最終將生成的 Flex Message 回覆給用戶，這個函式是整個穿搭建議功能的執行核心。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    data = event.postback.data
    parsed_data = parse_qs(data) # 解析 Postback data 為字典

    query_type = parsed_data.get('type', [None])[0] # 查詢類型，例如 'temperature', 'occasion'
    target_query_city = parsed_data.get('city', [None])[0] # 查詢城市，如果沒有則使用預設城市
    
    logger.info(f"[OutfitHandler] 用戶 {user_id} 請求穿搭建議查詢: 類型={query_type}。")

    # --- 檢查是否成功獲取到查詢城市 ---
    """
    這是一個必要的防呆機制。
    如果 Postback data 中沒有包含城市資訊，後續所有邏輯都無法執行。
    提早返回並給予錯誤訊息，可以防止程式因 `None` 值而崩潰，並引導用戶重新操作。
    """
    if not target_query_city:
        logger.error(f"[OutfitHandler] 無法從 Postback data 中獲取查詢城市。")
        send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，查詢城市資訊不完整，請稍候再試。")])
        clear_user_state(user_id) # 清除可能存在的狀態
        return True

    try:
        # --- 處理今日穿搭建議的邏輯區塊 ---
        if query_type == "today":
            """
            這段程式碼專門處理用戶選擇「今日穿搭建議」的情況。
            程式碼流程：
            1. 數據獲取：首先呼叫 `get_today_all_weather_data` 聚合器來獲取所需的全部天氣數據。
            2. 邏輯處理：然後將這些數據傳遞給 `get_outfit_suggestion_for_today_weather` 函式，進行穿搭判斷並生成文字和圖片。
            3. 訊息呈現：最後，調用 `build_today_outfit_flex` 函式將處理後的資訊組合成一個 Flex Message，並發送給用戶。
            這種分層設計讓每個函式各司其職，易於維護和測試。
            """
            # 1. 使用數據聚合器取得該城市所有天氣預報數據
            # 這裡的 all_weather_data 包含了來自多個 API 的所有資訊
            all_weather_data = get_today_all_weather_data(target_query_city)
            if not all_weather_data: # 集中處理無法獲取數據的情況
                logger.error(f"無法為 {target_query_city} 取得完整的今日天氣數據。")
                send_line_reply_message(api, reply_token, [TextMessage(text=f"抱歉，無法取得 {target_query_city} 的天氣數據，請稍候再試。")])
                return True
            
            # 從聚合後的字典中提取建立 Flex Message 所需的參數
            # 聚合器已處理了所有預設值，所以這裡的程式碼是安全的
            location = all_weather_data.get("locationName", target_query_city)
            general_forecast = all_weather_data.get("general_forecast", {})
            hourly_forecast = all_weather_data.get("hourly_forecast", [])
            uv_data = all_weather_data.get("uv_data", {})
            
            # 2. 調用核心邏輯生成穿搭建議
            # 這裡將所有解析後的數據傳遞給 get_outfit_suggestion_for_today_weather
            outfit_info_for_today_flex = get_outfit_suggestion_for_today_weather(
                location=location,
                hourly_forecast=hourly_forecast,
                general_forecast=general_forecast,
                uv_data=uv_data
            )

            if not outfit_info_for_today_flex:
                logger.error(f"無法從 today_outfit_logic 生成 {target_query_city} 的今日穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法生成今日穿搭建議。")])
                return True

            # 3. 生成 Flex Bubble
            flex_bubble_content_today = build_today_outfit_flex(
                outfit_info=outfit_info_for_today_flex, location_name=location
            )
            
            if not isinstance(flex_bubble_content_today, FlexBubble):
                logger.error(f"build_today_outfit_flex 返回了無效的 FlexBubble 物件，類型: {type(flex_bubble_content_today)}")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，今日穿搭建議卡片生成失敗 (內部錯誤)。")])
                return True
            
            # 包裝成 FlexMessage 並發送
            alt_text = f"{location} 今日穿搭建議"
            flex_message_to_send = FlexMessage(
                alt_text=alt_text, contents=flex_bubble_content_today
            )

            send_line_reply_message(api, reply_token, [flex_message_to_send])
            logger.info(f"成功為 {user_id} 發送 {location} 的今日穿搭建議 (Flex Message)。")
            return True

        # --- 處理即時穿搭建議的邏輯區塊 ---
        elif query_type == "current":
            """
            這段程式碼負責處理「即時穿搭建議」的請求。
            程式碼流程：
            1. 數據獲取：首先呼叫 `fetch_and_parse_weather_data` 來獲取即時天氣觀測數據。
            2. 邏輯處理：然後將即時數據傳遞給 `get_outfit_suggestion_for_current_weather` 進行穿搭邏輯判斷。
            3. 訊息呈現：最後，使用 `build_current_outfit_flex` 來構建 Flex Message 卡片，並回覆給用戶。
            這種流程確保即時數據能夠被正確處理和呈現。
            """
            # 1. 取得與解析該城市的即時天氣數據
            current_weather_data = fetch_and_parse_weather_data(city_name=target_query_city)
            if not current_weather_data: # 檢查共用函式是否成功回傳數據，如果失敗，發送通用的錯誤訊息
                logger.error(f"無法取得或解析 {target_query_city} 的即時天氣數據，無法提供穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法取得即時天氣數據以提供穿搭建議。")])
                return True
            
            # 2. 將解析後的即時數據傳給 get_outfit_suggestion_for_current_weather
            outfit_info = get_outfit_suggestion_for_current_weather(current_weather_data)
            if not outfit_info: # 檢查 get_outfit_suggestion_for_current_weather 是否成功返回數據
                logger.error(f"無法生成 {target_query_city} 的即時穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法生成即時穿搭建議。")])
                return True
            
            # 3. 生成 Flex Bubble
            flex_bubble_content = build_current_outfit_flex(outfit_info, location_name=target_query_city)
            if not isinstance(flex_bubble_content, FlexBubble): # 檢查 build_current_outfit_flex 是否返回了有效的 FlexBubble
                logger.error(f"build_current_outfit_flex 返回了無效的 FlexBubble 物件，類型: {type(flex_bubble_content)}")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，即時穿搭建議卡片生成失敗 (內部錯誤)。")])
                return True

            # 包裝成 FlexMessage 並發送
            alt_text = f"{target_query_city} 即時穿搭建議"
            flex_message_to_send = FlexMessage(
                alt_text=alt_text, contents=flex_bubble_content
            )

            send_line_reply_message(api, reply_token, [flex_message_to_send])
            logger.info(f"成功為 {user_id} 發送 {target_query_city} 的即時穿搭建議 (Flex Message)。")
            return True
            
        # --- 處理未來穿搭建議的邏輯區塊 ---
        elif query_type == "forecast":
            """
            這段程式碼處理「未來穿搭建議」的情況。
            程式碼流程：
            1. 數據獲取：呼叫 `fetch_and_parse_forecast_data` 獲取未來幾天的天氣預報。
            2. 邏輯處理：將預報數據傳遞給 `get_outfit_suggestion_for_forecast_weather` 進行穿搭建議邏輯判斷。
            3. 訊息呈現：這裡採用了更複雜的 `FlexCarousel` 結構，通過 `convert_forecast_to_bubbles` 函式，生成包含每日天氣預報和穿搭建議的 `FlexBubble` 列表。
            4. 發送訊息：最後將這些 `FlexBubble` 包裝成 `FlexCarousel` 並發送。
            這樣可以讓用戶在一則訊息中，橫向滑動查看未來多天的穿搭建議，提供視覺化體驗。
            """
            # 預設為查詢未來 7 天的預報
            days = 7
            logger.info(f"用戶 {user_id} 請求未來 {days} 天的預報和穿搭建議。")

            # 1. 呼叫共用函式來獲取並解析預報天氣數據
            parsed_full_forecast = fetch_and_parse_forecast_data(city_name=target_query_city)
            if not parsed_full_forecast: # 檢查共用函式是否成功回傳數據，如果失敗，發送一個通用的錯誤訊息
                logger.error(f"無法取得或解析 {target_query_city} 的未來預報數據，無法提供穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法取得未來預報數據以提供穿搭建議。")])
                return True
            
            # 2. 將解析後的預報天氣數據傳給 get_outfit_suggestion_for_forecast_weather
            # 這裡的 `outfit_info` 實際上只是一個單獨的建議，但 `convert_forecast_to_bubbles` 已經在內部處理了每個日期的穿搭邏輯
            outfit_info = get_outfit_suggestion_for_forecast_weather(parsed_full_forecast)
            if not outfit_info: # 檢查 get_outfit_suggestion_for_forecast_weather 是否成功返回數據
                logger.error(f"無法生成 {target_query_city} 的未來穿搭建議。")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法生成未來穿搭建議。")])
                return True
            
            try:
                # 3. 調用 convert_forecast_to_bubbles，它會返回兩個 FlexBubble 列表
                # 第一個是天氣預報的 Bubble 列表
                # 第二個是穿搭建議的 Bubble 列表 (這已在 forecast_flex_converter.py 中生成好)
                _, outfit_bubbles = \
                    convert_forecast_to_bubbles(parsed_full_forecast, days, include_outfit_suggestions=True)

                messages_to_send: List[FlexMessage | TextMessage] = []

                if outfit_bubbles:
                    outfit_flex_message = build_flex_carousel(outfit_bubbles, alt_text=f"{target_query_city} 未來 {days} 天穿搭建議")
                    messages_to_send.append(outfit_flex_message)
                else:
                    logger.warning(f"未能生成 {target_query_city} 的未來穿搭建議卡片。")
                    messages_to_send.append(TextMessage(text=f"抱歉，未能為 {target_query_city} 生成未來穿搭建議。"))

                if not messages_to_send:
                    logger.error(f"為 {target_query_city} 生成訊息失敗，無任何訊息可發送。")
                    send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法提供預報資訊。")])
                    return True

                # 4. 包裝成 FlexCarousel 並發送
                send_line_reply_message(api, reply_token, messages_to_send)
                logger.info(f"成功發送 {target_query_city} 未來 {days} 天的穿搭建議。")
                return True

            except Exception as e:
                logger.exception(f"處理未來穿搭建議時發生錯誤: {e}")
                send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，處理未來預報時發生系統錯誤，請稍候再試。")])
                return True
            
        # --- 未知的查詢類型 ---
        # 這段程式碼處理了所有不符合上述 `if/elif` 條件的 `query_type`
        # 捕獲未預期的 `query_type` 值，避免程式繼續執行無效的邏輯，並向用戶發送一個友善的錯誤訊息，告知他們當前無法處理該請求
        else:
            logger.warning(f"[OutfitHandler] 未知的穿搭查詢類型: {query_type}")
            send_line_reply_message(api, reply_token, [TextMessage(text="抱歉，無法識別的穿搭建議類型。")])
            return True

    # --- 通用的異常處理 ---
    except Exception as e:
        # 使用 `try...except` 區塊包裹整個處理流程，能夠捕獲任何未預期的執行時錯誤，防止程式崩潰
        logger.exception(f"[OutfitHandler] 處理 outfit_query 時發生錯誤，用戶: {user_id}: {e}")
        send_line_reply_message(api, reply_token, [TextMessage(text="處理穿搭建議查詢時發生錯誤，請稍候再試。")])
        return True

logger.info("穿搭建議處理器已載入。")