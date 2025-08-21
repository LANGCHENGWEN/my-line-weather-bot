# weather_current/weather_flex_message.py
"""
生成用於 LINE Flex Message 的即時天氣資訊。
將從 weather_current_parser.py 模組解析並格式化後的字典數據，轉換成符合 LINE Flex Message 規格的結構。
"""
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble, FlexButton, FlexSeparator, PostbackAction
)
from utils.flex_message_elements import make_kv_row

def build_weather_flex(data: dict) -> FlexBubble:
    """
    根據解析好的天氣數據字典，建構並回傳一個 LINE Flex Message 的氣泡 (FlexBubble) 物件。
    這個氣泡包含即時天氣資訊的完整視覺化呈現，包括標題、時間、各種天氣數值和一個查詢按鈕。
    """
    return FlexBubble(
        size="mega",
        body=FlexBox(
            layout="vertical", # 內容垂直排列
            contents=[
                # --- 標題 ---
                FlexText(
                    text=f"📍 {data['location_name']} 即時天氣",
                    color="#000000",
                    weight="bold", # 粗體
                    size="lg",
                    margin="md",
                    align="center" # 置中對齊
                ),
                # --- 觀測時間 ---
                FlexText(
                    text=data["observation_time"],
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
                        make_kv_row("🌈 天氣狀況：", data["weather_description"]),
                        FlexBox(
                            layout="vertical",
                            spacing="sm",
                            contents=[
                                make_kv_row("🌡️ 溫度：", data["current_temp"]),
                                make_kv_row("    (體感溫度：", f"{data['sensation_temp_display']})")
                            ]
                        ),
                        make_kv_row("💧 濕度：", data["humidity"]),
                        make_kv_row("🌧️ 降雨量：", data["precipitation"]),
                        FlexBox(
                            layout="vertical",
                            spacing="sm",
                            contents=[
                                make_kv_row("🌬️ 風速：", data["wind_speed_beaufort_display"]),
                                make_kv_row("      (風向：", f"{data['wind_direction']})")
                            ]
                        ),
                        make_kv_row("🧭 氣壓：", data["pressure"]),
                        make_kv_row("☀️ 紫外線指數:", data["uv_index"])
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
                ),
                # --- 按鈕 ---
                FlexButton(
                    style="primary",
                    margin="lg",
                    height="sm",
                    color="#1DB446",
                    action=PostbackAction(
                        label="查詢其他縣市",
                        data="action=change_city" # 後端用來判斷用戶意圖的資料
                    )
                )
            ]
        )
    )