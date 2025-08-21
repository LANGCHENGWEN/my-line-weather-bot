# weather_forecast/forecast_builder_flex.py
"""
建構 LINE Flex Message 的天氣預報氣泡 (Bubble)。
接收一個已經過處理和格式化的天氣預報資料字典，並根據這些資料動態生成一個美觀且易於閱讀的 Flex Message。
"""
import logging
from linebot.v3.messaging.models import FlexBox, FlexText, FlexBubble, FlexSeparator

from utils.flex_message_elements import make_kv_row

logger = logging.getLogger(__name__)

def build_observe_weather_flex(data, days) -> FlexBubble:
    """
    根據解析並格式化後的預報天氣數據，建立一個 LINE Flex Message 的氣泡物件。
    這個氣泡物件會將所有預報資訊以視覺化的方式呈現，並回傳給呼叫端。
    特別處理了標題，根據是單日預報還是多日預報來動態顯示。
    """
    # 標題
    """
    根據傳入的參數來決定 Flex Message 的標題文字。
    如果 data 字典中包含 'day_index' 鍵，表示這是單日預報，標題會顯示具體的第幾天預報，例如「未來第 3 天預報」。
    如果沒有 'day_index'，則會顯示泛稱的「未來 X 天預報」。
    """
    day_index = data.get('day_index', None)
    if day_index:
        title_text = f"📍 {data['county_name']} 未來第 {day_index} 天預報"
    else:
        title_text = f"📍 {data['county_name']} 未來 {days} 天預報"
        
    return FlexBubble(
        size="mega",
        body=FlexBox(
            layout="vertical", # 內容垂直排列
            contents=[
                # --- 標題 ---
                FlexText(
                    text=title_text,
                    color="#000000",
                    weight="bold", # 粗體
                    size="lg",
                    margin="md",
                    align="center" # 置中對齊
                ),
                # --- 觀測時間 ---
                FlexText(
                    text=data["obs_time"],
                    color="#666666",
                    size="sm",
                    margin="sm",
                    align="center"
                ),
                FlexSeparator(margin="md"), # 分隔線
                # --- 天氣資訊 ---
                FlexBox(
                    layout="vertical",
                    margin="lg",
                    spacing="sm", # 行與行之間有小間距
                    contents=[
                        make_kv_row("🌈 天氣狀況：", data["display_weather_desc"]),
                        FlexBox(
                            layout="vertical",
                            spacing="sm",
                            contents=[
                                make_kv_row("🌡️ 最高溫度：", data["display_max_temp"]),
                                make_kv_row("❄️ 最低溫度：", data["display_min_temp"]),
                                make_kv_row("    (體感：", f"{data['display_feels_like_temp']})")
                            ]
                        ),
                        make_kv_row("💧 濕度：", data["display_humidity"]),
                        make_kv_row("🌧️ 降雨機率：", data["display_pop"]),
                        FlexBox(
                            layout="vertical",
                            spacing="sm",
                            contents=[
                                make_kv_row("🌬️ 風速：", data["display_wind_speed"]),
                                make_kv_row("      (風向：", f"{data['display_wind_dir']})")
                            ]
                        ),
                        make_kv_row("🔥 最大舒適度:", data["display_comfort_max"]),
                        make_kv_row("🧊 最小舒適度:", data["display_comfort_min"]),
                        make_kv_row("☀️ 紫外線指數:", data["display_uv_index"])
                    ]
                ),
                FlexSeparator(margin="md"),
                # --- 免責聲明 ---
                FlexText(
                    text="--- 資訊僅供參考，請以中央氣象署最新發布為準 ---",
                    size="md",
                    color="#808080",
                    wrap=True, # 允許文字換行
                    margin="md",
                    align="center"
                )
            ]
        )
    )