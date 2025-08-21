# weather_forecast/line_forecast_messaging.py
"""
將處理好的天氣預報數據轉換成 LINE Flex Message。
1. 從外部接收已經解析和處理過的原始天氣數據。
2. 檢查數據的有效性；如果數據無效，則生成一個友好的錯誤提示 Flex Message。
3. 如果數據有效，會協調 `forecast_flex_converter.py` 中的函式，將每日的預報數據轉換成獨立的 Flex Bubble 卡片。
4. 最後將所有生成的 Flex Bubble 組織成一個 Flex Carousel（輪播）訊息，以便用戶可以在 LINE 上左右滑動來瀏覽不同天的天氣預報。
這個模組是將「數據」變成「視覺化且可發送的 LINE 訊息」的最後一步。
"""
import logging
from linebot.v3.messaging.models import FlexBox, FlexText, FlexBubble, FlexMessage

from .forecast_flex_converter import convert_forecast_to_bubbles, build_flex_carousel

logger = logging.getLogger(__name__)

def build_forecast_weather_flex(parsed_data: dict, days: int, city_name: str) -> FlexMessage:
    """
    將解析後的天氣字典轉成 FlexMessage Carousel。
    此函式是整個未來天氣預報流程的最終環節。
    接收來自 API 模組的原始數據，並交由 `forecast_flex_converter` 處理，最終生成一個包含多張天氣預報卡片的輪播訊息。
    處理數據不存在或無效的例外情況，回傳一個友善的錯誤提示。

    Args:
        parsed_data (dict): 包含解析後天氣數據的字典。
        days (int): 預報的天數 (3 / 5 / 7)。
        city_name (str): 外部傳入的查詢縣市名稱，用於 Flex Message 的標題。

    Returns:
        FlexMessage: 包含未來天氣預報的 Flex Message 輪播。
    """
    # --- 錯誤處理：檢查數據完整性 ---
    """
    檢查傳入的 `parsed_data` 是否有效。
    如果 `parsed_data` 是空的，或者不包含 `forecast_periods` 鍵，立即返回一個 Flex Message，不會讓程式因為找不到鍵而崩潰。
    """
    if not parsed_data or not parsed_data.get("forecast_periods"):
        logger.warning(f"沒有提供預報天氣數據或數據不完整供格式化。查詢城市: {city_name}, 天數: {days}")

        alt_text = f"{city_name} 未來天氣預報"
        return FlexMessage(
            alt_text=alt_text,
            contents=FlexBubble(
                body=FlexBox(type="box", layout="vertical", contents=[
                    FlexText(text=f"⚠️ 抱歉，暫時無法取得 {city_name} 的預報資料。", wrap=True)
                ])
            )
        )

    # --- 轉換數據為 Flex Bubble 列表 ---
    """
    整個函式的核心邏輯。
    呼叫 `convert_forecast_to_bubbles` 函式，將解析好的數據轉換成一個包含多個 `FlexBubble` 物件的列表。
    `convert_forecast_to_bubbles` 函式負責處理數據聚合和卡片建立的所有複雜細節。
    傳入 `days` 參數只生成所需天數的預報卡片。
    """
    general_weather_bubbles, _ = convert_forecast_to_bubbles(parsed_data, days)

    # --- 錯誤處理：檢查 Bubble 列表是否成功建立 ---
    """
    檢查 `convert_forecast_to_bubbles` 函式是否成功返回了預期的 Bubble 列表。
    如果列表為空，會返回一個錯誤提示，明確告知用戶無法生成預報卡片。
    """
    if not general_weather_bubbles:
        logger.error(f"無法從解析後的數據構建天氣預報 Bubble 列表。城市: {city_name}, 天數: {days}")
        alt_text = f"{city_name} 未來天氣預報"
        return FlexMessage(
            alt_text=alt_text,
            contents=FlexBubble(
                body=FlexBox(type="box", layout="vertical", contents=[
                    FlexText(text=f"⚠️ 抱歉，無法生成 {city_name} 的天氣預報顯示。", wrap=True)
                ])
            )
        )

    # --- 組建 Flex Carousel 並回傳 ---
    """
    如果前面的步驟都成功，程式會來到這裡。
    呼叫 `build_flex_carousel` 函式，將前面生成的 `FlexBubble` 列表組裝成一個 `FlexCarousel` 物件。
    `FlexCarousel` 允許用戶左右滑動來查看多個卡片。
    最終將 `FlexCarousel` 包裝到一個 `FlexMessage` 中，並設定替代文字，回傳並發送給用戶。
    """
    alt_txt = f"{city_name} 未來 {days} 天氣預報"
    flex_msg = build_flex_carousel(general_weather_bubbles, alt_text=alt_txt)

    logger.info(f"預報 FlexMessage 已建立，共 {len(general_weather_bubbles)} 張 bubble，alt_text: {alt_txt}")
    return flex_msg