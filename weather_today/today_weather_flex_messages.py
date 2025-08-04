# weather_today/today_weather_flex_messages.py
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexImage, FlexBubble, FlexSeparator
)
from utils.flex_message_elements import make_kv_row

from outfit_suggestion.today_outfit_logic import get_outfit_suggestion_for_today_weather

def create_daily_weather_flex_message(
    location: str,
    general_forecast: dict,
    hourly_forecast: dict,
    uv_data: dict
) -> FlexBubble:
    """
    生成每日天氣預報的 Flex Message。
    Args:
        location (str): 查詢的城市名稱。
        general_forecast (dict): 來自 F-C0032-001 的天氣概況數據。
        hourly_forecast (dict): 來自 F-D0047-089 的逐時天氣預報數據。
        uv_data (dict): 來自 O-A0005-001 的紫外線指數數據。
    Returns:
        FlexBubble: Flex Message 的內容物件。
    """
    date_display_string = general_forecast["date_full_formatted"]

    outfit_info = get_outfit_suggestion_for_today_weather(general_forecast, hourly_forecast, uv_data)

    suggestion_text = outfit_info.get("outfit_suggestion_text", "目前無法提供即時穿搭建議。")
    suggestion_image_url = outfit_info.get("suggestion_image_url", "https://i.imgur.com/default_forecast_outfit.png")

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

    # 創建天氣資訊的列表，直接從 general_forecast 和 uv_data 字典中獲取
    weather_info_contents = [
        make_kv_row("🌈 天氣狀況：", general_forecast["weather_phenomenon"]),
        make_kv_row("體感溫度：", general_forecast["apparent_temp_formatted"]),
        make_kv_row("🌡️ 溫度：", general_forecast["formatted_temp_range"]),
        make_kv_row("💧 濕度：", hourly_forecast[0]["humidity_formatted"]), # 假設 hourly_forecast 的第一個元素是當前時段
        make_kv_row("🌧️ 降雨機率：", general_forecast["pop_formatted"]),
        make_kv_row("🌬️ 風速：", hourly_forecast[0]["wind_scale_formatted"]), # 假設 hourly_forecast 的第一個元素是當前時段
        make_kv_row("      (風向：", f"{hourly_forecast[0]['wind_direction']})"),
        make_kv_row("舒適度：", general_forecast["comfort_index"]),
        make_kv_row("☀️ 紫外線指數:", uv_data.get("UVIndexFormatted")) # 這裡因為 uv_data 可能為 None，還是需要 .get() 或檢查
    ]

    """
    weather_info_contents = []

    weather_info_contents.append(make_kv_row("🌈 天氣狀況：", outfit_info.get("weather_phenomenon", "N/A")))
    weather_info_contents.append(make_kv_row("體感溫度：", outfit_info.get("feels_like", "N/A")))
    # --- 修改開始 ---
    # 直接從 outfit_info 提取格式化後的溫度範圍
    weather_info_contents.append(make_kv_row("🌡️ 溫度：", outfit_info.get("formatted_temp_range", "N/A")))
    # --- 修改結束 ---
    weather_info_contents.append(make_kv_row("💧 濕度：", outfit_info.get("weather_phenomenon", "N/A")))
    weather_info_contents.append(make_kv_row("🌧️ 降雨機率：", outfit_info.get("pop", "N/A")))
    weather_info_contents.append(make_kv_row("🌬️ 風速：", outfit_info.get("wind_scale", "N/A")))
    weather_info_contents.append(make_kv_row("風向：", outfit_info.get("feels_like", "N/A")))
    weather_info_contents.append(make_kv_row("舒適度：", outfit_info.get("weather_phenomenon", "N/A")))
    weather_info_contents.append(make_kv_row("☀️ 紫外線指數：", outfit_info.get("uv_index", "N/A")))
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
                    text=f"☀️ {location} 今日天氣",
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
                # paddingAll="20px",
                # backgroundColor="#e0f7fa" # 淡藍色背景
            ]
        )
    )