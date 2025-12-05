# outfit_suggestion/outfit_flex_messages.py
"""
根據不同的天氣資訊（今日預報和即時天氣），來建立 LINE Flex Message 的穿搭建議卡片。
`build_today_outfit_flex` 函式用於生成當天預報的穿搭建議卡片。
`build_current_outfit_flex` 函式則用於生成即時天氣的穿搭建議卡片。
這兩個函式都接收已經處理好的穿搭資訊和天氣數據，然後將這些數據組裝成一個視覺化且易於閱讀的 FlexBubble 物件，有效的將數據邏輯與 UI 呈現邏輯分離。
"""
from utils.flex_message_elements import make_kv_row
from linebot.v3.messaging.models import FlexBox, FlexText, FlexImage, FlexBubble, FlexSeparator

def build_today_outfit_flex(outfit_info: dict, location_name: str) -> FlexBubble:
    """
    生成今日穿搭建議的 Flex Message 卡片，包含穿搭圖片、天氣概況和建議文字。
    將綜合性的今日天氣預報數據，以及根據這些數據生成的穿搭建議，轉換成一個結構化的 LINE Flex Message 物件。
    
    Args:
        outfit_info (dict): 包含穿搭建議和已經格式化好的天氣顯示資訊的字典。
                            包含 'outfit_suggestion_text', 'suggestion_image_url',
                                'date_full_formatted', 'weather_phenomenon', 'feels_like',
                                'formatted_temp_range', 'pop', 'wind_speed', 'uv_index'
        location_name (str): 縣市名稱。

    Returns:
        FlexBubble: LINE Flex Message 的 Bubble 物件。
    """

    # --- 從傳入的 `outfit_info` 字典中，安全的獲取穿搭建議文字和圖片 URL ---
    # 使用 `.get()` 方法，並為每個鍵提供預設值，這樣即使在 `outfit_info` 字典中缺少某些鍵，程式也不會報錯，而是會使用預設的圖片或文字
    # 確保在任何情況下都能回傳一個有效的 Flex Message，提高程式的穩定性
    suggestion_text = outfit_info.get("outfit_suggestion_text", ["目前無法提供今日穿搭建議。"])
    suggestion_image_url = outfit_info.get("suggestion_image_url", "https://i.postimg.cc/T3qs1kMf/NO-DATA.png")
    date_display_string = outfit_info.get("date_full_formatted", "未知日期")

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
    這種方式將常見的鍵值對排版邏輯抽象成一個獨立的函式，讓主函式 `build_today_outfit_flex` 的程式碼更簡潔，並方便在其他地方重複使用相同的排版。
    直接使用 weather_today_parser.py、weather_3days_parser.py、today_uvindex_parser.py 預先處理好的顯示字串。
    """
    weather_info_contents = []
    weather_info_contents.append(make_kv_row("天氣狀況：", outfit_info.get("weather_phenomenon")))
    weather_info_contents.append(make_kv_row("體感溫度：", outfit_info.get("feels_like")))
    weather_info_contents.append(make_kv_row("溫度：", outfit_info.get("formatted_temp_range")))
    weather_info_contents.append(make_kv_row("降雨機率：", outfit_info.get("pop")))
    weather_info_contents.append(make_kv_row("風速：", outfit_info.get("wind_scale")))
    weather_info_contents.append(make_kv_row("紫外線指數：", outfit_info.get("uv_index")))

    # --- 組裝並回傳最終的 `FlexBubble` 物件 ---
    """
    根據 LINE Flex Message 的 JSON 格式所建立的物件結構。
    `FlexBubble` 作為最外層的容器，包含了 `hero`（頂部圖片）和 `body`（內容區）兩個部分。

    `hero` 區塊放置代表穿搭建議的圖片。
    `body` 區塊使用 `FlexBox` 佈局，從上到下依次放置標題、副標題、分隔線、天氣資訊區塊，以及穿搭建議文字區塊，形成一個完整且美觀的今日穿搭卡片。
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
                    text=f"☀️ {location_name} 今日穿搭建議",
                    weight="bold",
                    size="lg",
                    align="center",
                    margin="md",
                    color="#000000"
                ),
                FlexText(
                    text=date_display_string,
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

def build_current_outfit_flex(outfit_info: dict, location_name: str) -> FlexBubble:
    """
    生成即時穿搭建議的 Flex Message 卡片，包含穿搭圖片、天氣概況和建議文字。
    作用與 `build_today_outfit_flex` 類似，但使用的是即時天氣觀測數據。
    
    Args:
        outfit_info (dict): 包含穿搭建議和已經格式化好的天氣顯示資訊的字典。
                            包含 'suggestion_text', 'suggestion_image_url',
                                'observation_time', 'weather_condition', 'feels_like',
                                'humidity', 'precipitation', 'wind_speed_beaufort_display', 'uv_index'
        location_name (str): 縣市名稱。

    Returns:
        FlexBubble: LINE Flex Message 的 Bubble 物件。
    """

    # --- 從傳入的 `outfit_info` 字典中，安全的獲取穿搭建議文字和圖片 URL ---
    # 使用 `.get()` 方法，並為每個鍵提供預設值，這樣即使在 `outfit_info` 字典中缺少某些鍵，程式也不會報錯，而是會使用預設的圖片或文字
    # 確保在任何情況下都能回傳一個有效的 Flex Message，提高程式的穩定性
    suggestion_text = outfit_info.get("suggestion_text", ["目前無法提供即時穿搭建議。"])
    suggestion_image_url = outfit_info.get("suggestion_image_url", "https://i.postimg.cc/T3qs1kMf/NO-DATA.png")
    date_full_formatted = outfit_info.get("observation_time")

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
    這種方式將常見的鍵值對排版邏輯抽象成一個獨立的函式，讓主函式 `build_current_outfit_flex` 的程式碼更簡潔，並方便在其他地方重複使用相同的排版。
    直接使用 weather_current_parser.py 預先處理好的顯示字串。
    """
    weather_info_contents = []
    weather_info_contents.append(make_kv_row("天氣狀況：", outfit_info.get("weather_condition")))
    weather_info_contents.append(make_kv_row("體感溫度：", outfit_info.get("feels_like")))
    weather_info_contents.append(make_kv_row("濕度：", outfit_info.get("humidity")))
    weather_info_contents.append(make_kv_row("降雨量：", outfit_info.get("precipitation")))
    weather_info_contents.append(make_kv_row("風速：", outfit_info.get("wind_speed_beaufort_display")))
    weather_info_contents.append(make_kv_row("紫外線指數：", outfit_info.get("uv_index")))

    # --- 組裝並回傳最終的 `FlexBubble` 物件 ---
    """
    根據 LINE Flex Message 的 JSON 格式所建立的物件結構。
    `FlexBubble` 作為最外層的容器，包含了 `hero`（頂部圖片）和 `body`（內容區）兩個部分。

    `hero` 區塊放置代表穿搭建議的圖片。
    `body` 區塊使用 `FlexBox` 佈局，從上到下依次放置標題、副標題、分隔線、天氣資訊區塊，以及穿搭建議文字區塊，形成一個完整且美觀的即時穿搭卡片。
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
                    text=f"⏰ {location_name} 即時穿搭建議",
                    weight="bold",
                    size="lg",
                    align="center",
                    margin="md",
                    color="#000000"
                ),
                FlexText(
                    text=date_full_formatted,
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