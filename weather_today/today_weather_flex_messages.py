# weather_today/today_weather_flex_messages.py
import datetime

def build_today_weather_flex(weather_data: dict) -> dict:
    """
    根據解析後的今日天氣數據，建構 Flex Message 的 Bubble 內容字典。

    Args:
        weather_data (dict): 包含今日天氣資訊的字典，預期包含:
                             'location_name', 'date', 'weekday', 'time',
                             'weather_phenomenon', 'pop', 'min_temp', 'max_temp',
                             'comfort_index'。

    Returns:
        dict: Flex Message 的 Bubble 內容字典。
    """
    location_name = weather_data.get("location_name", "該地區")
    date_str = weather_data.get("date", "未知日期")
    weekday_num = weather_data.get("weekday", "0") # 0-6 for Sun-Sat
    time_str = weather_data.get("time", "未知時間")
    weather_phenomenon = weather_data.get("weather_phenomenon", "資料N/A")
    pop = weather_data.get("pop", "N/A")
    min_temp = weather_data.get("min_temp", "N/A")
    max_temp = weather_data.get("max_temp", "N/A")
    comfort_index = weather_data.get("comfort_index", "資料N/A")

    # 轉換星期幾數字為中文
    weekday_map = {
        "0": "日", "1": "一", "2": "二", "3": "三",
        "4": "四", "5": "五", "6": "六"
    }
    chinese_weekday = weekday_map.get(weekday_num, "")

    # 主標題
    main_title = f"✨ {location_name} 今日天氣預報 ✨"
    # 副標題
    sub_title = f"更新時間 : {date_str} (星期{chinese_weekday}) {time_str}"

    return {
        "type": "bubble",
        "direction": "ltr",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": main_title,
                    "weight": "bold",
                    "size": "xl",
                    "align": "center",
                    "color": "#0056b3"
                },
                {
                    "type": "text",
                    "text": sub_title,
                    "size": "sm",
                    "color": "#666666",
                    "align": "center",
                    "margin": "sm"
                }
            ],
            "paddingAll": "20px",
            "backgroundColor": "#e0f7fa" # 淡藍色背景
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {
                            "type": "icon",
                            "url": "https://i.imgur.com/weather_icon.png", # 可以換成天氣圖標
                            "size": "md"
                        },
                        {
                            "type": "text",
                            "text": f"天氣: {weather_phenomenon}",
                            "flex": 4,
                            "size": "lg",
                            "weight": "bold",
                            "color": "#333333",
                            "margin": "sm"
                        }
                    ],
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {
                            "type": "icon",
                            "url": "https://i.imgur.com/rain_icon.png", # 降雨圖標
                            "size": "md"
                        },
                        {
                            "type": "text",
                            "text": f"降雨機率: {pop}%",
                            "flex": 4,
                            "size": "lg",
                            "weight": "bold",
                            "color": "#333333",
                            "margin": "sm"
                        }
                    ],
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {
                            "type": "icon",
                            "url": "https://i.imgur.com/temp_icon.png", # 溫度圖標
                            "size": "md"
                        },
                        {
                            "type": "text",
                            "text": f"溫度: {min_temp}~{max_temp}°C",
                            "flex": 4,
                            "size": "lg",
                            "weight": "bold",
                            "color": "#333333",
                            "margin": "sm"
                        }
                    ],
                    "margin": "md"
                },
                {
                    "type": "box",
                    "layout": "baseline",
                    "contents": [
                        {
                            "type": "icon",
                            "url": "https://i.imgur.com/comfort_icon.png", # 舒適度圖標
                            "size": "md"
                        },
                        {
                            "type": "text",
                            "text": f"舒適度: {comfort_index}",
                            "flex": 4,
                            "size": "lg",
                            "weight": "bold",
                            "color": "#333333",
                            "margin": "sm"
                        }
                    ],
                    "margin": "md"
                }
            ],
            "paddingAll": "20px"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "style": "link",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "查看今日穿搭",
                        "data": "action=outfit_query&type=today" # 觸發今日穿搭建議
                    }
                }
            ],
            "paddingAll": "20px",
            "backgroundColor": "#e0f7fa"
        }
    }