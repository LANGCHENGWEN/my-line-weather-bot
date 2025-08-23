# outfit_suggestion/forecast_outfit_flex_messages.py
"""
根據未來天氣的穿搭建議資訊，建立 LINE Flex Message 的單日卡片 (FlexBubble)。
將從穿搭邏輯模組 (`forecast_outfit_logic.py`) 獲取的文字建議和圖片 URL，以及從天氣預報解析器 (`weather_forecast_parser.py`) 獲取的格式化天氣數據，組合成一個視覺化且易於閱讀的卡片。
這種將「數據處理」與「介面生成」分開的設計，讓程式碼結構更清晰，易於維護和修改。
"""
import logging
from utils.flex_message_elements import make_kv_row
from linebot.v3.messaging.models import FlexBox, FlexText, FlexImage, FlexBubble, FlexSeparator

logger = logging.getLogger(__name__)

def build_forecast_outfit_card(outfit_info: dict, location_name: str, day_offset: int) -> FlexBubble:
    """
    根據提供的穿搭資訊和已經格式化好的天氣數據，來構建一個單天的 Flex Message 卡片。
    將後端處理好的資料，轉換成 LINE Bot 前端能夠顯示的視覺化元件（FlexBubble 物件）。
    將資料邏輯與 UI 呈現邏輯分離，讓開發者可以專注於建立美觀的卡片，而不必擔心資料處理的細節。
    
    Args:
        outfit_info (dict): 包含穿搭建議和已經格式化好的天氣顯示資訊的字典。
                            包含 'suggestion_text', 'suggestion_image_url',
                            'obs_time', 'display_weather_desc', 'display_feels_like_temp',
                            'display_humidity', 'display_pop', 'display_uv_index'
        location_name (str): 縣市名稱。
        day_offset (int): 從今天開始的天數偏移 (0=今天, 1=明天)。

    Returns:
        FlexBubble: LINE Flex Message 的 Bubble 物件。
    """

    # --- 從傳入的 `outfit_info` 字典中，安全的獲取穿搭建議文字和圖片 URL ---
    # 使用了 `.get()` 方法，並為每個鍵提供了預設值，這樣即使在 `outfit_info` 字典中缺少某些鍵，程式也不會報錯，而是會使用預設的圖片或文字
    # 確保在任何情況下都能回傳一個有效的 Flex Message，提高了程式的穩定性
    suggestion_text = outfit_info.get("suggestion_text", ["目前無法提供未來穿搭建議。"])
    suggestion_image_url = outfit_info.get("suggestion_image_url", "https://i.imgur.com/default_forecast_outfit.png")
    date_full_formatted = outfit_info.get("obs_time", "未知日期") # 例如 "2025年07月23日 (三)"

    # 從 outfit_info 獲取 day_index，這個值在 forecast_flex_converter.py 中被設定為 i + 1
    display_day_index = outfit_info.get("day_index", day_offset + 1) # 如果 outfit_info 沒有，再使用 day_offset 計算（作為備用）

    # --- 組合主標題：使用 day_index 動態顯示「未來第 X 天」---
    # 結合縣市名稱和動態的日期偏移量（未來第幾天），讓用戶能清楚知道這張卡片顯示的是哪一個縣市、哪一天的資訊
    title_text = f"📍 {location_name} 未來第 {display_day_index} 天穿搭建議"

    # --- 組合副標題 (日期和星期) ---
    # 生成卡片頂部顯示的日期資訊
    # 直接使用 `outfit_info` 中已經處理好的格式化日期字串 (`date_full_formatted`)，這樣就不需要在這個函式內部重複進行日期格式化邏輯，減少了不必要的計算，讓程式碼更乾淨
    subtitle_text = date_full_formatted

    # --- 創建一個穿搭建議的文字列表，用於存放每個 FlexText 元件 ---
    """
    將穿搭建議的文字列表 `suggestion_text` 轉換為一系列的 `FlexText` 物件。
    因為 Flex Message 的內容元件需要是特定的物件（如 `FlexText`）。
    透過迴圈，為每一條建議文字都生成一個獨立的 `FlexText` 物件，並將其加入列表，以便後續的 `FlexBox` 佈局使用。
    """
    suggestion_text_contents = []
    for suggestion in suggestion_text:
        suggestion_text_contents.append(
            FlexText(
                text=suggestion,
                size="md",
                color="#333333",
                wrap=True, # 確保文字在超出範圍時自動換行
                margin="sm",
                align="start"
            )
        )

    # --- 天氣資訊區塊內容 ---
    """
    使用一個輔助函式 `make_kv_row` 生成天氣資訊的鍵值對佈局。
    這種方式將常見的鍵值對排版邏輯抽象成一個獨立的函式，讓主函式 `build_forecast_outfit_card` 的程式碼更簡潔，並方便在其他地方重複使用相同的排版。
    直接使用 forecast_flex_converter.py 預先處理好的顯示字串。
    """
    weather_info_contents = []
    weather_info_contents.append(make_kv_row("天氣狀況：", outfit_info.get("display_weather_desc")))
    weather_info_contents.append(make_kv_row("體感溫度：", outfit_info.get("display_feels_like_temp")))
    weather_info_contents.append(make_kv_row("濕度：", outfit_info.get("display_humidity")))
    weather_info_contents.append(make_kv_row("降雨機率：", outfit_info.get("display_pop")))
    weather_info_contents.append(make_kv_row("紫外線指數：", outfit_info.get("display_uv_index")))

    # --- 組裝並回傳最終的 `FlexBubble` 物件 ---
    """
    根據 LINE Flex Message 的 JSON 格式所建立的物件結構。
    `FlexBubble` 作為最外層的容器，包含了 `hero`（頂部圖片）和 `body`（內容區）兩個部分。

    `hero` 區塊放置代表穿搭建議的圖片。
    `body` 區塊使用 `FlexBox` 佈局，從上到下依次放置標題、副標題、分隔線、天氣資訊區塊，以及穿搭建議文字區塊，形成一個完整且美觀的單日穿搭卡片。
    """
    return FlexBubble(
        direction="ltr",
        hero=FlexBox(
            layout="vertical",
            contents=[
                FlexImage(
                    url=suggestion_image_url, 
                    size="full",
                    aspectRatio="20:9",
                    aspectMode="cover"
                )
            ]
        ),
        body=FlexBox(
            layout="vertical",
            contents=[
                FlexText(
                    text=title_text,
                    weight="bold",
                    size="lg",
                    align="center",
                    margin="md",
                    color="#000000"
                ),
                FlexText(
                    text=subtitle_text,
                    size="sm",
                    color="#666666",
                    align="center",
                    margin="none"
                ),
                FlexSeparator(margin="md"),
                FlexBox(
                    layout="vertical",
                    spacing="sm",
                    margin="md",
                    contents=weather_info_contents # 這裡直接放入 FlexBox 物件列表
                ),
                FlexSeparator(margin="md"),
                FlexBox(
                    layout="vertical",
                    spacing="sm",
                    margin="md",
                    contents=suggestion_text_contents # 這裡直接放入 FlexText 物件列表
                )
            ]
        )
    )