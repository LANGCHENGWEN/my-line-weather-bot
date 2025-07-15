# forecast_flex_converter.py
from typing import List, Dict
from collections import Counter, OrderedDict, defaultdict
from linebot.v3.messaging.models import FlexMessage, FlexCarousel
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
        date_key = p.get("date")  # 你在 parser 裡自己決定要不要帶這欄
        # 這裡去除「今天」「明天」前綴，只保留日期方便分組
        if date_key in ("今天", "明天"):
            # 用 start_time 取日期，如果有的話
            # 如果沒日期就用"今天"或"明天"本身當key
            # 但parser應該有start_time欄位可用，假設有就用它
            # 以下示範用date_key直接分組，視實際可調整
            day_key = date_key
        else:
            day_key = date_key  # mm/dd格式直接當key

        if date_key not in day_bucket:
            # 初始化每日資料儲存用
            day_bucket[day_key] = {
                "county_name": parsed_weather.get("county_name", "N/A"),
                "num_days": parsed_weather.get("num_days", 1),
                "obs_time": parsed_weather.get("obs_time", "N/A"),
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

        # 累積每個時段資料
        day_data = day_bucket[day_key]
        day_data["weather_descs"].append(p.get("weather_desc", "N/A"))
        # 最高溫轉換成float(失敗就跳過)
        try:
            day_data["max_temps"].append(float(p.get("max_temp", "-")))
        except:
            pass
        try:
            day_data["max_feels"].append(float(p.get("max_feel", "-")))
        except:
            pass
        try:
            day_data["min_temps"].append(float(p.get("min_temp", "-")))
        except:
            pass
        try:
            day_data["min_feels"].append(float(p.get("min_feel", "-")))
        except:
            pass
        try:
            day_data["humidities"].append(float(p.get("humidity", "-")))
        except:
            pass
        try:
            day_data["pops"].append(float(p.get("pop", "-")))
        except:
            pass
        try:
            day_data["wind_speeds"].append(float(p.get("wind_speed", "-")))
        except:
            pass
        # 風向文字用列表，先累積起來
        wind_dir = p.get("wind_dir", "-")
        if wind_dir != "-" and wind_dir != "N/A":
            day_data["wind_dirs"].append(wind_dir)
        # 舒適度與紫外線指數文字也累積
        comfort_max = p.get("comfort_max", "-")
        if comfort_max != "-" and comfort_max != "N/A":
            day_data["comfort_maxs"].append(comfort_max)
        comfort_min = p.get("comfort_min", "-")
        if comfort_min != "-" and comfort_min != "N/A":
            day_data["comfort_mins"].append(comfort_min)
        uv_index = p.get("uv_index", "-")
        if uv_index != "-" and uv_index != "N/A":
            day_data["uv_indices"].append(uv_index)

    # 整理成最終每日資料 (取極值與主要描述)
    final_days = []
    for day_key, day_data in day_bucket.items():
        # 天氣描述取出現頻率最高的
        if day_data["weather_descs"]:
            weather_desc = Counter(day_data["weather_descs"]).most_common(1)[0][0]
        else:
            weather_desc = "N/A"

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