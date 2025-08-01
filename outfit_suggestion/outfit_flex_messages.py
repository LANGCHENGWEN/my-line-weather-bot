# outfit_suggestion/outfit_flex_messages.py
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexImage, FlexBubble, FlexSeparator
)
from utils.flex_message_elements import make_kv_row

def build_today_outfit_flex(outfit_info: dict, location_name: str) -> FlexBubble:
    """
    生成今日穿搭建議的 Flex Message 字典，包含穿搭圖片、天氣概況和建議文字。
    Args:
        outfit_info (dict): 包含以下綜合天氣數據和建議文本：
                            'date_full_formatted' (str),
                            'weather_phenomenon' (str),
                            'feels_like' (str),
                            'formatted_temp_range' (str),
                            'pop' (str),
                            'humidity' (str), # 新增
                            'wind_speed' (str), # 新增
                            'uv_index' (str), # 新增，如果你的數據源有
                            'outfit_suggestion_text' (str or list[str]), # 確保是列表或單一字串
                            'suggestion_image_url' (str)
        location_name (str): 查詢的城市名稱，用於標題。
    Returns:
        FlexBubble: Flex Message 的內容物件。
    """
    suggestion_text = outfit_info.get("outfit_suggestion_text", "目前無法提供即時穿搭建議。")
    suggestion_image_url = outfit_info.get("suggestion_image_url", "https://i.imgur.com/default_forecast_outfit.png")

    date_display_string = outfit_info.get("date_full_formatted", "日期 N/A")

    # 創建一個列表，用於存放每個 FlexText 元件
    suggestion_text_contents = []
    for suggestion in suggestion_text:
        suggestion_text_contents.append(
            FlexText(
                text=suggestion,
                size="md",
                color="#333333",
                wrap=True,
                margin="sm",
                align="start"
                # 如果你希望每句話都粗體，可以在這裡加上 "weight": "bold"
            )
        )

    weather_info_contents = []

    weather_info_contents.append(make_kv_row("天氣狀況：", outfit_info.get("weather_phenomenon", "N/A")))
    weather_info_contents.append(make_kv_row("體感溫度：", outfit_info.get("feels_like", "N/A")))
    # --- 修改開始 ---
    # 直接從 outfit_info 提取格式化後的溫度範圍
    weather_info_contents.append(make_kv_row("溫度：", outfit_info.get("formatted_temp_range", "N/A")))
    # --- 修改結束 ---
    weather_info_contents.append(make_kv_row("降雨機率：", outfit_info.get("pop", "N/A")))
    weather_info_contents.append(make_kv_row("風速：", outfit_info.get("wind_scale", "N/A")))
    weather_info_contents.append(make_kv_row("紫外線指數：", outfit_info.get("uv_index", "N/A")))

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
                    contents=weather_info_contents
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
    生成即時穿搭建議的 Flex Message 字典，包含穿搭圖片、天氣資訊和建議文字。
    Args:
        outfit_info (dict): 包含 'suggestion_text', 'suggestion_image_url'
                            以及所有從 weather_current_parser.py 輸出並由
                            current_outfit_logic.py 傳遞過來的格式化天氣數據。
        location_name (str): 查詢的城市名稱，用於標題。
    Returns:
        FlexBubble: Flex Message 的內容字典。
    """
    # 獲取建議文字列表，如果沒有則使用預設單句建議
    suggestion_text = outfit_info.get("suggestion_text", ["目前無法提供即時穿搭建議。"])
    suggestion_image_url = outfit_info.get("suggestion_image_url", "https://i.imgur.com/default_forecast_outfit.png")

    date_full_formatted = outfit_info.get("observation_time", "日期 N/A")

    # 創建一個列表，用於存放每個 FlexText 元件
    suggestion_text_contents = []
    for suggestion in suggestion_text:
        suggestion_text_contents.append(
            FlexText(
                text=suggestion,
                size="md",
                color="#333333",
                wrap=True,
                margin="sm",
                align="start"
                # 如果你希望每句話都粗體，可以在這裡加上 "weight": "bold"
            )
        )

    # 創建天氣資訊內容列表
    weather_info_contents = []

    # 直接使用 outfit_info 中已經格式化好的字串
    weather_info_contents.append(make_kv_row("天氣狀況：", outfit_info.get("weather_condition", "N/A")))
    weather_info_contents.append(make_kv_row("體感溫度：", outfit_info.get("feels_like", "N/A")))
    weather_info_contents.append(make_kv_row("濕度：", outfit_info.get("humidity", "N/A")))
    weather_info_contents.append(make_kv_row("降雨量：", outfit_info.get("precipitation", "N/A")))
    weather_info_contents.append(make_kv_row("風速：", outfit_info.get("wind_speed_beaufort_display", "N/A")))
    weather_info_contents.append(make_kv_row("紫外線指數：", outfit_info.get("uv_index", "N/A")))

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
                    text=date_full_formatted, # 副標題
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
                    contents=weather_info_contents # 使用創建好的天氣資訊內容列表
                ),
                FlexSeparator(margin="md"),
                FlexBox(
                    layout="vertical",
                    spacing="sm",
                    margin="md",
                    contents=suggestion_text_contents
                )
            ]
        )
    )