# weather_today/today_weather_flex_messages.py
"""
根據聚合好的天氣數據，動態生成 LINE Flex Message。
主要職責：
1. 數據整合：接收來自不同 API 來源解析後的天氣數據。
2. 組建 Flex Message：將天氣資訊以美觀、結構化的方式呈現在一個 Flex Message 氣泡（bubble）中。
3. 回傳完整訊息：將組建好的 `FlexBubble` 包裝成 `FlexMessage` 物件並回傳，發送給用戶。
***這是用戶手動查詢時的卡片，與推播時發送的卡片內容不一樣 (今日天氣的推播卡片有穿搭建議，這裡沒有)
"""
from typing import Any, List, Dict 
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble, FlexMessage, FlexSeparator
)

from utils.flex_message_elements import make_kv_row

def build_daily_weather_flex_message(
    location: str,
    parsed_weather: Dict[str, Any],
    parsed_data: List[Dict[str, Any]],
    parsed_uv_data: Dict[str, Any]
) -> FlexMessage:
    """
    生成每日天氣預報的 Flex Message。
    使用 LINE Flex Message 的各個組件來佈局和填充內容，最終返回一個完整的 FlexMessage 物件。

    Args:
        location (str): 查詢的城市名稱。
        parsed_weather (dict): 來自 F-C0032-001 的天氣數據。
        parsed_data (list): 來自 F-D0047-089 的未來 3 天天氣預報數據。
        parsed_uv_data (dict): 來自 O-A0005-001 的紫外線指數數據。

    Returns:
        FlexMessage 物件。
    """
    date_display_string = parsed_weather.get("date_full_formatted") # 提取已格式化的日期

    hourly_data = parsed_data[0] if parsed_data else {} # 如果 parsed_data 是空的，避免索引錯誤

    # --- 天氣資訊區塊內容 ---
    """
    使用一個輔助函式 `make_kv_row` 生成天氣資訊的鍵值對佈局。
    這種方式將常見的鍵值對排版邏輯抽象成一個獨立的函式，讓主函式 `build_daily_weather_flex_message` 的程式碼更簡潔，並方便在其他地方重複使用相同的排版。
    數據直接從傳入的 `parsed_weather`、`hourly_data` 和 `parsed_uv_data` 中獲取。
    """
    weather_info_contents = [
        make_kv_row("🌈 天氣狀況：", parsed_weather.get("weather_phenomenon")),
        make_kv_row("🧥 體感溫度：", hourly_data.get("apparent_temp_formatted")),
        make_kv_row("🌡️ 溫度：", parsed_weather.get("formatted_temp_range")),
        make_kv_row("💧 濕度：", hourly_data.get("humidity_formatted")),
        make_kv_row("🌧️ 降雨機率：", parsed_weather.get("pop_formatted")),
        make_kv_row("🌬️ 風速：", hourly_data.get("wind_scale_formatted")),
        make_kv_row("      (風向：", f"{hourly_data.get('wind_direction')})"),
        make_kv_row("😌 舒適度：", parsed_weather.get("comfort_index")),
        make_kv_row("☀️ 紫外線指數:", parsed_uv_data.get("UVIndexFormatted"))
    ]
    
    # --- Flex Message 結構化與回傳 ---
    """
    使用 `FlexBubble` 作為最外層的容器，並設定基本的方向。
    `body` 區塊使用 `FlexBox` 佈局，從上到下依次放置標題、副標題、分隔線、天氣資訊區塊，以及文字敘述，形成一個完整且美觀的今日天氣卡片。
    最後將 `FlexBubble` 包裝在一個 `FlexMessage` 物件中並返回。
    """
    bubble = FlexBubble(
        direction="ltr",
        body=FlexBox(
            layout="vertical", # 內容垂直排列
            contents=[
                # --- 標題 ---
                FlexText(
                    text=f"📍 {location} 今日天氣",
                    weight="bold",  # 粗體
                    size="lg",
                    align="center", # 置中對齊
                    margin="md",
                    color="#000000"
                ),
                # --- 觀測時間 ---
                FlexText(
                    text=date_display_string,
                    size="sm",
                    color="#666666",
                    align="center",
                    margin="none"
                ),
                FlexSeparator(margin="md"), # 分隔線
                # --- 天氣資訊 ---
                FlexBox(
                    layout="vertical",
                    spacing="sm", # 行與行之間有小間距
                    margin="md",
                    contents=weather_info_contents
                ),
                FlexSeparator(margin="md"),
                # --- 文字敘述 ---
                FlexText(
                    text="想查詢其他縣市的今日天氣嗎？可以直接輸入縣市名稱哦！",
                    size="sm",
                    color="#999999",
                    align="center",
                    wrap=True, # 確保文字在超出範圍時自動換行
                    margin="md"
                )
            ]
        )
    )

    return FlexMessage(
        alt_text=f"{location} 今日天氣預報",
        contents=bubble
    )