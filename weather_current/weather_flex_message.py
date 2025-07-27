# weather_current/weather_flex_message
from linebot.v3.messaging.models import (
    FlexBox, FlexText, FlexBubble, FlexButton, FlexSeparator, PostbackAction
)
from utils.flex_message_elements import make_kv_row

# 主函式
def build_weather_flex(data: dict) -> FlexBubble:
    return FlexBubble(
        size="mega",
        body=FlexBox(
            layout="vertical",
            contents=[
                FlexText(
                    text=f"📍 {data['location_name']} 即時天氣",
                    color="#000000",
                    weight="bold",
                    size="lg",
                    margin="md",
                    align="center"
                ),
                FlexText(
                    text=data["observation_time"],
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
                                make_kv_row("🌬️ 風速：", data["wind_speed"]),
                                make_kv_row("      (風向：", f"{data['wind_direction']})")
                            ]
                        ),
                        make_kv_row("🧭 氣壓：", data["pressure"]),
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
                ),
                FlexButton(
                    style="primary",
                    margin="lg",
                    height="sm",
                    color="#1DB446",
                    action=PostbackAction(
                        label="查詢其他縣市",
                        data="action=change_city"
                    )
                )
            ]
        )
    )