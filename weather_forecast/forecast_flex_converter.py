# forecast_flex_converter.py
import json
import logging
from typing import List, Dict
from datetime import datetime
from collections import Counter, OrderedDict, defaultdict
from linebot.v3.messaging.models import FlexMessage, FlexCarousel
from .forecast_builder_flex import build_observe_weather_flex  # 已在同檔定義

logger = logging.getLogger(__name__)

def safe_float(val):
    try:
        return float(val)
    except:
        return None
"""    
def format_start_time(start_time_str: str) -> str:
    try:
        dt = datetime.fromisoformat(start_time_str)
        return dt.strftime("%Y年%-m月%-d日")  # Unix/MacOS
        # return dt.strftime("%Y年%m月%d日")  # Windows
    except Exception:
        return "N/A"
"""

# --------- 將 parser 的結果 => Bubble 清單 ---------
def convert_forecast_to_bubbles(parsed_weather: Dict, max_days: int) -> List[Dict]:
    """
    parsed_weather: weather_forecast_parser.parse_forecast_weather() 的輸出
    max_days: 3 / 5 / 7
    回傳: [bubble1, bubble2, ...]
    """
    logger.info(f"第一筆 forecast_period 資料: {parsed_weather.get('forecast_periods', [])[0] if parsed_weather.get('forecast_periods') else '無資料'}")
    bubbles: List[Dict] = []

    # 先把同一天的多個時段彙整成「日資料」
    day_bucket = OrderedDict()                 # key = YYYY-MM-DD
    for p in parsed_weather.get("forecast_periods", []):
        date_key = p.get("date")  # 你在 parser 裡自己決定要不要帶這欄
        day_key = date_key

        if date_key not in day_bucket:

            # 初始化每日資料儲存用
            day_bucket[day_key] = {
                "county_name": parsed_weather.get("county_name", "N/A"),
                "num_days": parsed_weather.get("num_days", 1),
                "obs_time": p.get("date_str", "N/A"),
                # 儲存多個欄位的累積值
                "weather_descs": [],
                "max_temps": [],
                "max_feels": [],
                "min_temps": [],
                "min_feels": [],
                "humidities": [],
                "pops": [],
                "wind_speeds": [],
                "wind_dirs": [],
                "comfort_maxs": [],
                "comfort_mins": [],
                "uv_indices": []
            }
        # 可在這裡做「取極值」或「覆蓋」… 視需求而定

        logger.debug(f"✅ 每日預報整理結果: {json.dumps(day_bucket, ensure_ascii=False, indent=2)}")

        # 累積每個時段資料
        day_data = day_bucket[day_key]
        day_data["weather_descs"].append(p.get("weather_desc", "N/A"))

        for key, bucket in [
            ("max_temp", "max_temps"),
            ("max_feel", "max_feels"),
            ("min_temp", "min_temps"),
            ("min_feel", "min_feels"),
            ("humidity", "humidities"),
            ("pop", "pops"),
            ("wind_speed", "wind_speeds")
        ]:
            val = safe_float(p.get(key))
            if val is not None:
                day_data[bucket].append(val)

        wind_dir = p.get("wind_dir", "-")
        if wind_dir != "-" and wind_dir != "N/A":
            day_data["wind_dirs"].append(wind_dir)

        for key, bucket in [
            ("comfort_max", "comfort_maxs"),
            ("comfort_min", "comfort_mins"),
            ("uv_index", "uv_indices")
        ]:
            val = p.get(key, "-")
            if val != "-" and val != "N/A":
                day_data[bucket].append(val)

    # 整理成最終每日資料 (取極值與主要描述)
    final_days = []
    for day_key, day_data in day_bucket.items():
        weather_desc = Counter(day_data["weather_descs"]).most_common(1)[0][0] if day_data["weather_descs"] else "N/A"
        # 取最大或最小，若空則用"-"
        max_temp = max(day_data["max_temps"]) if day_data["max_temps"] else "-"
        max_feel = max(day_data["max_feels"]) if day_data["max_feels"] else "-"
        min_temp = min(day_data["min_temps"]) if day_data["min_temps"] else "-"
        min_feel = min(day_data["min_feels"]) if day_data["min_feels"] else "-"
        humidity = round(sum(day_data["humidities"]) / len(day_data["humidities"]), 1) if day_data["humidities"] else "-"
        pop = max(day_data["pops"]) if day_data["pops"] else "-"
        wind_speed = max(day_data["wind_speeds"]) if day_data["wind_speeds"] else "-"
        # 風向取出現頻率最高
        wind_dir = Counter(day_data["wind_dirs"]).most_common(1)[0][0] if day_data["wind_dirs"] else "-"
        comfort_max = Counter(day_data["comfort_maxs"]).most_common(1)[0][0] if day_data["comfort_maxs"] else "-"
        comfort_min = Counter(day_data["comfort_mins"]).most_common(1)[0][0] if day_data["comfort_mins"] else "-"
        uv_index = Counter(day_data["uv_indices"]).most_common(1)[0][0] if day_data["uv_indices"] else "-"

        final_day_data = {
            "county_name": day_data["county_name"],
            "num_days": day_data["num_days"],
            "obs_time": day_data["obs_time"],
            "weather_desc": weather_desc,
            "max_temp": max_temp,
            "max_feel": max_feel,
            "min_temp": min_temp,
            "min_feel": min_feel,
            "humidity": humidity,
            "pop": pop,
            "wind_speed": wind_speed,
            "wind_dir": wind_dir,
            "comfort_max": comfort_max,
            "comfort_min": comfort_min,
            "uv_index": uv_index,
            "loc_name": day_key  # 當作標題用
        }
        final_days.append(final_day_data)

    # 依序取前 N 天
    loc_name = f"{parsed_weather.get('county_name', 'N/A')}"
    for i, day_data in enumerate(final_days):
        if i >= max_days:
            break
        day_data['loc_name'] = loc_name
        day_data['day_index'] = i + 1  # 新增第幾天
        bubbles.append(build_observe_weather_flex(day_data))

    return bubbles

def build_flex_carousel(bubble_list, alt_text="天氣預報") -> FlexMessage:
    """bubble_list: List[dict]  →  FlexMessage 物件"""
    return FlexMessage(
        alt_text=alt_text,
        contents=FlexCarousel(contents=bubble_list)
    )