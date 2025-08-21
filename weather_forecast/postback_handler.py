# weather_forecast/postback_handler.py
"""
處理「未來天氣預報」Postback 事件的核心控制器。
在用戶點擊 Flex Message 選單中的按鈕（例如「3 天預報」）後，執行一連串的後端任務：
1. 解析 Postback 數據：從 Postback 事件中解析出用戶選擇的天數和目標查詢城市。
2. 協調 API 呼叫與數據處理：呼叫 `cwa_forecast_api.py` 來獲取原始天氣數據，接著將數據傳遞給 `weather_forecast_parser.py` 進行解析。
3. 格式化訊息並回覆：將解析後的數據交給 `line_forecast_messaging.py`，生成最終的 Flex Carousel 訊息。
4. 狀態管理：在完成查詢流程後，清除用戶的狀態，重置為「閒置」（idle），以便進行下一個對話。
"""
import json
import logging
from urllib.parse import parse_qsl

from linebot.v3.messaging.models import TextMessage
from linebot.v3.webhooks.models import PostbackEvent

from config import CWA_API_KEY

from utils.firestore_manager import set_user_state # 導入用戶狀態管理器
from utils.line_common_messaging import (          # 導入通用訊息發送功能
    send_line_reply_message, send_api_error_message
)

# 導入天氣預報相關功能
from .cwa_forecast_api import get_cwa_forecast_data
from .weather_forecast_parser import parse_forecast_weather
from .line_forecast_messaging import build_forecast_weather_flex

logger = logging.getLogger(__name__)

# --- 共用函式：獲取並解析指定城市的天氣預報資料 ---
def fetch_and_parse_forecast_data(city_name: str) -> dict | None:
    """
    將獲取中央氣象署 API 資料、解析數據的步驟封裝在一起，方便在不同地方重複使用。
    進行 API 呼叫，並處理可能出現的錯誤（例如 API 無資料或解析失敗）。
    如果全部成功，會返回一個解析後天氣數據的字典；如果失敗，則返回 None。
    """
    try:
        # 1. 取得原始天氣數據
        weather_data = get_cwa_forecast_data(api_key=CWA_API_KEY, location_name=city_name) 
        if not weather_data:
            logger.warning(f"[ForecastPostbackHandler] get_cwa_forecast_data 未返回任何資料，城市: {city_name}")
            return None
        
        logger.debug(f"[ForecastPostbackHandler] 接收到的 CWA API 原始資料: {json.dumps(weather_data, indent=2, ensure_ascii=False)[:2000]}...")

        # 2. 解析並格式化天氣數據 (得到可直接用於 Flex Message 模板的字典)
        parsed_weather = parse_forecast_weather(weather_data, city_name)
        if not parsed_weather:
            logger.error(f"[ForecastPostbackHandler] 無法從取得的預報資料中解析出 {city_name} 的天氣資訊，或解析結果不完整。")
            return None
        
        logger.debug(f"[ForecastPostbackHandler] 成功解析天氣數據: {parsed_weather}")
        return parsed_weather
    
    except Exception as e:
        logger.error(f"在獲取及解析 {city_name} 預報天氣時發生錯誤: {e}", exc_info=True)
        return None

# --- Postback 事件的入口點 ---
def handle_forecast_postback(messaging_api, event: PostbackEvent) -> bool:
    """
    處理天氣預報相關的 Postback 事件 (例如點擊 3/5/7 天按鈕)。
    解析 Postback 數據，並根據數據中的 `action` 執行相應的操作。
    主要邏輯：
    1. 驗證 `action` 是否為 `forecast_days`。
    2. 從 `data` 中提取出要查詢的城市和天數。
    3. 呼叫 `fetch_and_parse_forecast_data` 來獲取並處理數據。
    4. 呼叫 `build_forecast_weather_flex` 來生成最終的 Flex Message。
    5. 發送回覆並清除用戶狀態。
    如果 Postback 被處理，返回 True；否則返回 False。
    """
    user_id = event.source.user_id
    postback_data = event.postback.data
    reply_token = event.reply_token

    logger.info(f"[ForecastPostbackHandler] 收到來自用戶 {user_id} 的 Postback 數據: '{postback_data}'")

    try:
        # 解析 Postback 數據
        """
        使用 `urllib.parse.parse_qsl` 函式解析 Postback 數據。
        `parse_qsl` 可以將像 `key1=value1&key2=value2` 這樣的查詢字串安全的轉換成一個字典。
        這個方法比手動使用 `.split('&')` 和 `.split('=')` 更健壯、更安全，因為它可以正確處理值中包含 `=` 或特殊字元的情況。
        """
        params = dict(parse_qsl(postback_data)) # 將查詢字串解析成字典
        action = params.get('action')
        city_to_query = params.get('city')
        days_str = params.get('days')

        # 驗證 Postback action
        """
        確保此函式只處理它應該處理的 Postback 事件。
        如果 `action` 不等於 `"forecast_days"`，程式會立即返回 `False`。
        這樣處理事件的路由器（router）就知道這個事件應該交給下一個 `handler` 處理，避免處理不相關的事件。
        """
        if action != "forecast_days":
            logger.warning(f"[ForecastPostbackHandler] 收到的 action 不是 forecast_days: {action}")
            return False

        # 驗證參數完整性
        # 在進行任何 API 呼叫之前，檢查必要的參數（城市和天數）是否存在且有效
        if not all([city_to_query, days_str]):
            logger.error(f"[ForecastPostbackHandler] forecast_days Postback 數據不完整: city={city_to_query}, days={days_str}")
            send_line_reply_message(messaging_api, reply_token, [TextMessage(text="查詢參數不完整，請稍候再試。")])
            set_user_state(user_id, "idle")
            return True
        
        # 將天數字串轉換為整數
        # 錯誤處理：確保 `days_str` 可以安全的轉換為整數；否則發送錯誤訊息
        try:
            days = int(days_str)
        except ValueError:
            logger.error(f"[ForecastPostbackHandler] 天數參數無效: {days_str}", exc_info=True)
            send_line_reply_message(messaging_api, reply_token, [TextMessage(text="天數參數錯誤，請再試一次。")])
            set_user_state(user_id, "idle")
            return True
        
        logger.info(f"[ForecastPostbackHandler] 為用戶 {user_id} 查詢 {city_to_query} 的 {days} 天天氣預報。")
        
        # --- 呼叫共用函式並處理結果 ---
        """
        呼叫前面定義的 `fetch_and_parse_forecast_data` 函式執行主要邏輯。
        將「獲取數據」和「解析數據」的複雜步驟封裝起來，讓 `handle_forecast_postback` 的程式碼更乾淨、更易讀。
        如果 `fetch_and_parse_forecast_data` 返回 `None`，表示數據處理失敗，程式會向用戶發送一個錯誤提示。
        """
        parsed_weather = fetch_and_parse_forecast_data(city_to_query)
        if not parsed_weather:
            send_api_error_message(messaging_api, user_id, reply_token, f"{city_to_query} (天氣資料處理失敗)")
            set_user_state(user_id, "idle")
            return True
        
        # --- 建立並發送 Flex Message ---
        """
        如果數據獲取和解析成功，將 `parsed_weather` 和 `days` 傳遞給 `build_forecast_weather_flex` 函式，生成最終的 Flex Message 輪播。
        最後將訊息回覆給用戶，完成整個流程。
        """
        response_message = build_forecast_weather_flex(parsed_weather, days, city_to_query)
        if not response_message:
            logger.error(f"[ForecastPostbackHandler] 無法構建 Flex Message，parsed_weather 或 days 有問題。")
            send_line_reply_message(messaging_api, reply_token, [TextMessage(text=f"抱歉，無法顯示 {city_to_query} 的天氣預報。")])
            set_user_state(user_id, "idle")
            return True

        # 發送回覆
        send_line_reply_message(messaging_api, reply_token, [response_message])
        logger.info(f"[ForecastPostbackHandler] 已成功回覆用戶 {user_id} {city_to_query} 的 {days} 天天氣預報。")
        
        # 清除用戶狀態
        set_user_state(user_id, "idle")
        return True

    except Exception as e:
        logger.error(f"[ForecastPostbackHandler] 處理 forecast_days Postback 時發生未預期錯誤: {e}", exc_info=True)
        send_line_reply_message(messaging_api, reply_token, [TextMessage(text="處理您的預報請求時發生錯誤，請稍候再試。")])
        set_user_state(user_id, "idle")
        return True

logger.info("postback_handler.py 模組已載入。")