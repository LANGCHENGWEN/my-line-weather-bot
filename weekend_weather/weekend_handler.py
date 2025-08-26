# weekend_weather/weekend_handler.py
"""
處理與「週末天氣」相關的所有邏輯。
主要職責：
1. 處理 Postback 事件：當用戶點擊 LINE 上的「週末天氣」按鈕時，`handle_weekend_weather_postback` 函式會被觸發。
2. 查詢用戶設定：根據用戶的 ID 從資料庫中獲取設定的預設城市；如果沒有設定，則使用一個預設值。
3. 整合外部服務：調用中央氣象署 API 獲取天氣數據，並使用 `weather_forecast_parser` 和 `weekend_forecast_converter` 等工具來解析和處理這些數據。
4. 動態生成 Flex Message：將處理好的天氣數據轉換為美觀的 Flex Message，特別是使用 `FlexCarousel` 來展示多天的預報卡片。
5. 訊息發送：最終將生成的訊息通過 LINE Messaging API 發送給用戶。
"""
import logging
from typing import List, Optional
from linebot.v3.messaging.models import Message, TextMessage, FlexMessage, FlexCarousel

from config import CWA_API_KEY

from utils.firestore_manager import get_default_city
from utils.text_processing import normalize_city_name
from utils.line_common_messaging import send_line_reply_message

from weather_forecast.cwa_forecast_api import get_cwa_forecast_data
from weather_forecast.weather_forecast_parser import parse_forecast_weather
from weekend_weather.weekend_forecast_converter import get_weekend_forecast_flex_messages 

logger = logging.getLogger(__name__)

# --- 從 API 取得並處理天氣數據，最終生成 Flex Message ---
def create_weekend_weather_message(county_name: str) -> Optional[List[Message]]:
    """
    生成週末天氣訊息的核心邏輯。
    首先獲取中央氣象署的七天預報數據，然後進行解析，接著調用專門的轉換器來篩選週末數據並生成 Flex Message 氣泡。
    最終將這些氣泡組合成一個 `FlexCarousel` 物件，並返回一個可以發送的訊息列表。
    如果任何步驟失敗，返回一個適當的錯誤訊息。
    """
    try:
        # 對城市名稱進行標準化，確保與 API 查詢的格式一致
        normalized_location_name = normalize_city_name(county_name)

        # 1. 從中央氣象署 API 獲取天氣預報數據
        cwa_data = get_cwa_forecast_data(CWA_API_KEY, normalized_location_name)
        # 檢查 cwa_data 是否為空或沒有 'records' 鍵
        if not cwa_data or not cwa_data.get("records"):
            logger.warning(f"無法取得 {county_name} 的天氣預報資訊。API 返回空數據或無效格式。")
            return [TextMessage(text=f"抱歉，無法取得 {county_name} 的天氣預報資訊。")]
        
        # 2. 解析並格式化天氣數據
        parsed_forecast_weather = parse_forecast_weather(cwa_data, normalized_location_name)
        # 再次檢查結果是否有效
        if not parsed_forecast_weather or not parsed_forecast_weather.get("forecast_periods"):
            logger.error(f"無法從取得的週末天氣資料中解析或格式化出 {normalized_location_name} 的天氣資訊。")
            return [TextMessage(text=f"抱歉，無法顯示 {normalized_location_name} 的天氣資訊卡片。請稍候再試。")]

        # 3. 篩選數據並生成 Flex Message 氣泡
        # 從完整的預報數據中篩選出週末的部分，並為每一天生成一個單獨的 Flex Message 氣泡 (`FlexBubble`)
        weekend_weather_bubbles = get_weekend_forecast_flex_messages(parsed_forecast_weather)
        messages_to_send: List[Message] = []

        if weekend_weather_bubbles:
            # 將多個 Flex Bubble 包裝在 FlexCarousel 中，以便用戶可以滑動查看
            messages_to_send.append(FlexMessage(
                alt_text=f"{normalized_location_name} 週末天氣預報",
                contents=FlexCarousel(contents=weekend_weather_bubbles)
            ))
        else: # 如果沒有生成任何氣泡，返回一個文字訊息作為備用方案
            logger.warning(f"沒有為 {normalized_location_name} 生成週末天氣預報 Flex Bubbles。")
            messages_to_send.append(TextMessage(text=f"目前沒有 {normalized_location_name} 的週末天氣預報資訊。"))

        return messages_to_send # 將 `FlexMessage` 包裝在一個列表中並返回，準備發送
    
    except Exception as e:
        logger.exception(f"生成週末天氣 Flex Message 時發生錯誤: {e}")
        return [TextMessage(text="抱歉，查詢週末天氣時發生內部錯誤。")]

# --- 處理週末天氣預報的 Postback 事件 ---
def handle_weekend_weather_postback(api, event) -> bool:
    """
    此函式是事件的入口點。
    從 Postback 事件中獲取用戶 ID 和回覆令牌，然後獲取用戶設定的預設城市。
    將城市名稱傳遞給 `create_weekend_weather_message` 函式，處理所有的天氣數據獲取和訊息生成邏輯。
    最後將生成的訊息發送給用戶。
    """
    user_id = event.source.user_id
    reply_token = event.reply_token
    logger.info(f"處理週末天氣 postback，用戶: {user_id}")

    # 1. 從資料庫中獲取用戶先前設定的預設城市
    county_name = get_default_city(user_id)
    # 如果用戶沒有設定預設城市，退回到一個預設值
    if not county_name:
        county_name = "臺中市"
        logger.info(f"用戶 {user_id} 未設定預設城市，使用預設值：{county_name}")

    # 2. 呼叫核心邏輯並發送訊息
    # 將前面獲取的城市名稱傳遞給 `create_weekend_weather_message` 函式，處理所有數據處理和訊息生成工作
    messages_to_send = create_weekend_weather_message(county_name)
        
    # 檢查返回的訊息列表是否有效，如果有效，發送訊息
    if messages_to_send:
        send_line_reply_message(api, reply_token, messages_to_send)
        logger.info(f"✅ 成功發送 {county_name} 週末天氣預報和穿搭建議。")
    return True