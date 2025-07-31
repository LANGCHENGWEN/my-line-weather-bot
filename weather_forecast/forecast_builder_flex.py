# forecast_builder_flex.py
import json
import logging
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble, FlexSeparator
)
from utils.flex_message_elements import make_kv_row

logger = logging.getLogger(__name__)

# 主函式
def build_observe_weather_flex(data, days) -> FlexBubble:
    """
    根據天氣資料建立未來天氣預報的 FlexBubble。
    Args:
        data (dict): 必須包含以下鍵 (現在是帶 'display_' 前綴的鍵)：
            county_name, obs_time, display_weather_desc,
            display_max_temp, display_min_temp, display_feels_like_temp,
            display_humidity, display_pop, display_wind_speed, display_wind_dir,
            display_comfort_max, display_comfort_min, display_uv_index
        days (int): 預報的天數，用於標題顯示。
    Returns:
        FlexBubble: LINE Flex Message 的 Bubble 元件。
    """
    # logger.debug(f"🧪 傳入 Flex 的資料: {json.dumps(data, ensure_ascii=False, indent=2)}")

    day_index = data.get('day_index', None)
    if day_index:
        title_text = f"📍 {data['county_name']} 未來第 {day_index} 天預報"
    else:
        title_text = f"📍 {data['county_name']} 未來 {days} 天預報"
        
    return FlexBubble(
        size="mega",
        body=FlexBox(
            layout="vertical",
            contents=[
                FlexText(
                    text=title_text,
                    color="#000000",
                    weight="bold",
                    size="lg",
                    margin="md",
                    align="center"
                ),
                FlexText(
                    text=data["obs_time"],
                    color="#666666",
                    size="sm",
                    margin="sm",
                    align="center"
                ),
                FlexSeparator(margin="md"),
                FlexBox(
                    layout="vertical",
                    margin="lg",
                    spacing="sm",
                    contents=[
                        make_kv_row("🌈 天氣狀況：", data["display_weather_desc"]),
                        FlexBox(
                            layout="vertical",
                            spacing="sm",
                            contents=[
                                make_kv_row("🌡️ 最高溫度：", data["display_max_temp"]), # <--- 修正這裡
                                make_kv_row("❄️ 最低溫度：", data["display_min_temp"]), # <--- 修正這裡
                                make_kv_row("    (體感：", f"{data['display_feels_like_temp']})")
                            ]
                        ),
                        make_kv_row("💧 濕度：", data["display_humidity"]), # <--- 修正這裡
                        make_kv_row("🌧️ 降雨機率：", data["display_pop"]),
                        FlexBox(
                            layout="vertical",
                            spacing="sm",
                            contents=[
                                make_kv_row("🌬️ 風速：", data["display_wind_speed"]), # <--- 修正這裡
                                make_kv_row("      (風向：", f"{data['display_wind_dir']})")
                            ]
                        ),
                        make_kv_row("🔥 最大舒適度:", data["display_comfort_max"]), # <--- 修正這裡
                        make_kv_row("🧊 最小舒適度:", data["display_comfort_min"]), # <--- 修正這裡
                        make_kv_row("☀️ 紫外線指數:", data["display_uv_index"])
                    ]
                ),
                FlexSeparator(margin="md"),
                FlexText(
                    text="--- 資訊僅供參考，請以中央氣象署最新發布為準 ---",
                    size="md",
                    color="#808080",
                    wrap=True,
                    margin="md",
                    align="center"
                )
            ]
        )
    )