# ———— 小工具：快速做兩欄 Key‑Value row ————
def make_kv_row(label, value):
    return {
        "type": "box",
        "layout": "baseline",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": label,
                "color": "#4169E1",
                "size": "md",
                "flex": 4
            },
            {
                "type": "text",
                "text": value,
                "wrap": True,
                "color": "#8A2BE2",
                "size": "md",
                "flex": 5
            }
        ]
    }

# 主函式
def build_weather_flex(data):
    return {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"📍 {data['location_name']} 即時天氣",
                    "color": "#000000",
                    "weight": "bold",
                    "size": "lg",
                    "margin": "md",
                    "align": "center"
                },
                {"type": "separator", "margin": "md"},
                {
                    "type": "box",
                    "layout": "vertical",
                    "margin": "lg",
                    "spacing": "sm",
                    "contents": [
                        make_kv_row("⏱️ 觀測時間:", data["observation_time"]),
                        make_kv_row("🌈 天氣狀況:", data["weather_description"]),
                        {
                            "type": "box",
                            "layout": "vertical",
                            "spacing": "sm",
                            "contents": [
                                make_kv_row("🌡️ 溫度:", data["current_temp"]),
                                make_kv_row("    (體感溫度:", f"{data['sensation_temp_display']})")
                            ]
                        },
                        make_kv_row("💧 濕度:", data["humidity"]),
                        make_kv_row("🌧️ 降雨量:", data["precipitation"]),
                        {
                            "type": "box",
                            "layout": "vertical",
                            "spacing": "sm",
                            "contents": [
                                make_kv_row("🌬️ 風速:", data["wind_speed"]),
                                make_kv_row("      (風向:", f"{data['wind_direction']})")
                            ]
                        },
                        make_kv_row("🧭 氣壓:", data["pressure"]),
                        make_kv_row("☀️ 紫外線指數:", data["uv_index"])
                    ]
                },
                {"type": "separator", "margin": "md"},
                {
                    "type": "text",
                    "text": "--- 資訊僅供參考，請以中央氣象署最新發布為準 ---",
                    "size": "md",
                    "color": "#808080",
                    "wrap": True,
                    "margin": "md",
                    "align": "center"
                },
                {
                    "type": "button",
                    "style": "primary",
                    "margin": "lg",
                    "height": "sm",
                    "color": "#1E90FF",
                    "action": {
                        "type": "message",
                        "label": "查詢其他縣市",
                        "text": "查詢其他縣市"
                    },
                    "style": "secondary",
                    "margin": "lg"
                }
            ]
        }
    }