# forecast_flex_converter.py
from typing import List, Dict
from collections import OrderedDict
from linebot.v3.messaging.models import FlexMessage
from .forecast_builder_flex import build_observe_weather_flex  # 已在同檔定義

# --------- 將 parser 的結果 => Bubble 清單 ---------
def convert_forecast_to_bubbles(parsed_weather: Dict, max_days: int) -> List[Dict]:
    """
    parsed_weather: weather_forecast_parser.parse_forecast_weather() 的輸出
    max_days: 3 / 5 / 7
    回傳: [bubble1, bubble2, ...]
    """
    bubbles: List[Dict] = []

    # 先把同一天的多個時段彙整成「日資料」
    day_bucket = OrderedDict()                 # key = YYYY-MM-DD
    for p in parsed_weather.get("forecast_periods", []):
        date_key = p.get("forecast_date_iso")  # 你在 parser 裡自己決定要不要帶這欄
        if not date_key:
            # 若 parser 只有日期字串，可自行改用 p["forecast_date"]
            date_key = p.get("forecast_date")
        if date_key not in day_bucket:
            day_bucket[date_key] = {
                "county_name": parsed_weather.get("county_name", "N/A"),
                "township_name": parsed_weather.get("township_name", "N/A"),
                "num_days": parsed_weather.get("num_days", 1),
                "obs_time": parsed_weather.get("obs_time", "N/A"),
                "weather_desc": p.get("weather_desc", "N/A"),
                "max_temp": p.get("max_temp", "-"),
                "max_feel": p.get("max_feel", "-"),
                "min_temp": p.get("min_temp", "-"),
                "min_feel": p.get("min_feel", "-"),
                "humidity": p.get("humidity", "-"),
                "pop": p.get("pop", "-"),
                "wind_speed": p.get("wind_speed", "-"),
                "wind_dir": p.get("wind_dir", "-"),
                "comfort_max": p.get("comfort_max", "-"),
                "comfort_min": p.get("comfort_min", "-"),
                "uv_index": p.get("uv_index", "-")
            }
        # 可在這裡做「取極值」或「覆蓋」… 視需求而定

    # 依序取前 N 天
    loc_name = f"{parsed_weather['county_name']}{parsed_weather['township_name']}"
    for i, day_data in enumerate(day_bucket.values()):
        if i >= max_days:
            break
        bubbles.append(build_observe_weather_flex(day_data, loc_name))

    return bubbles

def build_flex_carousel(bubble_list, alt_text="天氣預報") -> FlexMessage:
    """bubble_list: List[dict]  →  FlexMessage 物件"""
    return FlexMessage(
        alt_text=alt_text,
        contents={
            "type": "carousel",
            "contents": bubble_list
        }
    )