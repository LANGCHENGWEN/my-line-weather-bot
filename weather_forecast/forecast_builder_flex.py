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
def build_observe_weather_flex(data):
    """
    data 需包含這些鍵：
        county_name, township_name, num_days, obs_time, weather_desc,
        max_temp, max_feel, min_temp, min_feel,
        humidity, pop, wind_speed, wind_dir,
        comfort_max, comfort_min, uv_index
        📍 **{county_name}{township_name} 未來 {num_days} 天預報**
        "📍 {data['location_name']} 即時天氣"
    """
    return {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": f"📍 {data['county_name']}{data['township_name']} 未來 {data['num_days']} 天預報",
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
                        make_kv_row("⏱️ 觀測時間:", data["obs_time"]),
                        make_kv_row("🌈 天氣狀況:", data["weather_desc"]),
                        {
                            "type": "box",
                            "layout": "vertical",
                            "spacing": "sm",
                            "contents": [
                                make_kv_row("🌡️ 最高溫度:", data["max_temp"]),
                                make_kv_row("    (體感最高:", f"{data['max_feel']})")
                            ]
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "spacing": "sm",
                            "contents": [
                                make_kv_row("❄️ 最低溫度:", data["min_temp"]),
                                make_kv_row("    (體感最低:", f"{data['min_feel']})")
                            ]
                        },
                        make_kv_row("💧 濕度:", data["humidity"]),
                        make_kv_row("🌧️ 降雨機率:", data["pop"]),
                        {
                            "type": "box",
                            "layout": "vertical",
                            "spacing": "sm",
                            "contents": [
                                make_kv_row("🌬️ 風速:", data["wind_speed"]),
                                make_kv_row("      (風向:", f"{data['wind_dir']})")
                            ]
                        },
                        make_kv_row("🔥 最大舒適度:", data["comfort_max"]),
                        make_kv_row("🧊 最小舒適度:", data["comfort_min"]),
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
                }
            ]
        }
    }