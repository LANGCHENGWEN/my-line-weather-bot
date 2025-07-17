# forecast_builder_flex.py
import json
import logging
from linebot.v3.messaging.models import (
    FlexBubble, FlexBox, FlexText, FlexSeparator
)

logger = logging.getLogger(__name__)

# ———— 小工具：快速做兩欄 Key‑Value row ————
def make_kv_row(label: str, value: str) -> FlexBox:
    """
    建立一行兩欄的 Key-Value FlexBox。
    """
    return FlexBox(
        layout="baseline",
        spacing="sm",
        contents=[
            FlexText(
                text=str(label),
                color="#4169E1",
                size="md",
                flex=4
            ),
            FlexText(
                text=str(value) if value is not None else "N/A",
                wrap=True,
                color="#8A2BE2",
                size="md",
                flex=5
            )
        ]
    )

# 主函式
def build_observe_weather_flex(data) -> FlexBubble:
    """
    根據天氣資料建立未來天氣預報的 FlexBubble。
    Args:
        data (dict): 必須包含以下鍵：
            county_name, township_name, num_days, obs_time, weather_desc,
            max_temp, max_feel, min_temp, min_feel,
            humidity, pop, wind_speed, wind_dir,
            comfort_max, comfort_min, uv_index
        📍 **{county_name}{township_name} 未來 {num_days} 天預報**
        "📍 {data['location_name']} 即時天氣"   
    Returns:
        FlexBubble: LINE Flex Message 的 Bubble 元件。
    """
    logger.debug(f"🧪 傳入 Flex 的資料: {json.dumps(data, ensure_ascii=False, indent=2)}")

    day_index = data.get('day_index', None)
    if day_index:
        title_text = f"📍 {data['county_name']} 未來第 {day_index} 天預報"
    else:
        title_text = f"📍 {data['county_name']} 未來 {data['num_days']} 天預報"
        
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
                FlexSeparator(margin="md"),
                FlexBox(
                    layout="vertical",
                    margin="lg",
                    spacing="sm",
                    contents=[
                        make_kv_row("⏱️ 觀測時間:", data["obs_time"]),
                        make_kv_row("🌈 天氣狀況:", data["weather_desc"]),
                        FlexBox(
                            layout="vertical",
                            spacing="sm",
                            contents=[
                                make_kv_row("🌡️ 最高溫度:", f"{data['max_temp']}°C"),
                                make_kv_row("    (體感最高:", f"{data['max_feel']}°C)")
                            ]
                        ),
                        FlexBox(
                            layout="vertical",
                            spacing="sm",
                            contents=[
                                make_kv_row("❄️ 最低溫度:", f"{data['min_temp']}°C"),
                                make_kv_row("    (體感最低:", f"{data['min_feel']}°C)")
                            ]
                        ),
                        make_kv_row("💧 濕度:", f"{data['humidity']}%" if data["humidity"] not in ("-", "N/A", None) else str(data["humidity"])),
                        make_kv_row("🌧️ 降雨機率:", f"{data['pop']}%" if data["pop"] not in ("-", "N/A", None) else str(data["pop"])),
                        FlexBox(
                            layout="vertical",
                            spacing="sm",
                            contents=[
                                make_kv_row("🌬️ 風速:", f"{data['wind_speed']} m/s" if data["wind_speed"] not in ("-", "N/A", None) else str(data["wind_speed"])),
                                make_kv_row("      (風向:", f"{data['wind_dir']})")
                            ]
                        ),
                        make_kv_row("🔥 最大舒適度:", data["comfort_max"]),
                        make_kv_row("🧊 最小舒適度:", data["comfort_min"]),
                        make_kv_row("☀️ 紫外線指數:", data["uv_index"])
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