# forecast_flex_converter.py
import json
import logging
from typing import Any, List, Dict
from collections import Counter
from linebot.v3.messaging.models import FlexMessage, FlexCarousel
from .forecast_builder_flex import build_observe_weather_flex  # 已在同檔定義

logger = logging.getLogger(__name__)

def safe_float(val: Any) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError): # 捕捉更廣泛的錯誤
        return None

# --------- 將 parser 的結果 => Bubble 清單 ---------
def convert_forecast_to_bubbles(parsed_weather: Dict, max_days: int) -> List[Dict]:
    """
    parsed_weather: weather_forecast_parser.parse_forecast_weather() 的輸出
    max_days: 3 / 5 / 7
    回傳: [bubble1, bubble2, ...]
    """
    logger.debug(f"第一筆 forecast_period 資料: {parsed_weather.get('forecast_periods', [])[0] if parsed_weather.get('forecast_periods') else '無資料'}")
    bubbles: List[Dict] = []

    final_days_aggregated: List[Dict] = []

    for p in parsed_weather.get("forecast_periods", []):
        # 提取當天的日期鍵，以便後續操作
        date_key = p.get("date")  # 例如: "2025-07-17"
        if not date_key:
            logger.warning("單一預報時段缺少 'date' 鍵，跳過處理。")
            continue

        # 初始化每日資料儲存用
        current_day_data = {
            "county_name": parsed_weather.get("county_name", "N/A"),
            # "num_days": parsed_weather.get("num_days", 1),
            "obs_time": p.get("date_str", "N/A"), # 使用 parser 提供的格式化日期字串
            "date": date_key, # 原始日期鍵
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

        # 處理白天數據
        current_day_data["weather_descs"].append(p.get("weather_desc_day", "N/A"))
        for key, bucket in [
            ("max_temp_day", "max_temps"),
            ("max_feel_day", "max_feels"),
            ("min_temp_day", "min_temps"),
            ("min_feel_day", "min_feels"),
            ("humidity_day", "humidities"),
            ("pop_day", "pops"),
            ("wind_speed_day", "wind_speeds")
        ]:
            val = safe_float(p.get(key))
            if val is not None:
                current_day_data[bucket].append(val)

        wind_dir_day = p.get("wind_dir_day", "-")
        if wind_dir_day != "-" and wind_dir_day != "N/A":
            current_day_data["wind_dirs"].append(wind_dir_day)

        for key, bucket in [
            ("comfort_max_day", "comfort_maxs"),
            ("comfort_min_day", "comfort_mins"),
            ("uv_index_day", "uv_indices")
        ]:
            val = p.get(key, "-")
            if val != "-" and val != "N/A":
                current_day_data[bucket].append(val)

        # 處理夜晚數據
        current_day_data["weather_descs"].append(p.get("weather_desc_night", "N/A"))
        for key, bucket in [
            ("max_temp_night", "max_temps"),
            ("max_feel_night", "max_feels"),
            ("min_temp_night", "min_feels"),
            ("min_feel_night", "min_feels"),
            ("humidity_night", "humidities"),
            ("pop_night", "pops"),
            ("wind_speed_night", "wind_speeds")
        ]:
            val = safe_float(p.get(key))
            if val is not None:
                current_day_data[bucket].append(val)

        wind_dir_night = p.get("wind_dir_night", "-")
        if wind_dir_night != "-" and wind_dir_night != "N/A":
            current_day_data["wind_dirs"].append(wind_dir_night)
            
        for key, bucket in [
            ("comfort_max_night", "comfort_maxs"),
            ("comfort_min_night", "comfort_mins"),
            ("uv_index_night", "uv_indices")
        ]:
            val = p.get(key, "-")
            if val != "-" and val != "N/A":
                current_day_data[bucket].append(val)

        # --- 將累積的每日數據進行最終彙整 (取極值、平均值、最常見值) ---
        weather_desc_counter = Counter([d for d in current_day_data["weather_descs"] if d != "N/A"])
        weather_desc = weather_desc_counter.most_common(1)[0][0] if weather_desc_counter else "N/A"

        # 溫度/體感：取白天和夜晚的極值
        max_temp = max(current_day_data["max_temps"]) if current_day_data["max_temps"] else "-"
        max_feel = max(current_day_data["max_feels"]) if current_day_data["max_feels"] else "-"
        min_temp = min(current_day_data["min_temps"]) if current_day_data["min_temps"] else "-"
        min_feel = min(current_day_data["min_feels"]) if current_day_data["min_feels"] else "-"
        
        # 濕度：取平均值
        humidity = round(sum(current_day_data["humidities"]) / len(current_day_data["humidities"]), 1) if current_day_data["humidities"] else "-"
        # ⚠️ 修改濕度：如果不是 "-"，就轉換成整數
        if humidity != "-":
            humidity = int(humidity) # 或者 str(int(humidity)) 如果最終需要的是字串
        
        # 降雨機率：取白天和夜晚的最大值
        pop = max(current_day_data["pops"]) if current_day_data["pops"] else "-"
        # ⚠️ 修改降雨機率：如果不是 "-"，就轉換成整數
        if pop != "-":
            pop = int(pop) # 或者 str(int(pop)) 如果最終需要的是字串

        # 風速：取最大值
        wind_speed = max(current_day_data["wind_speeds"]) if current_day_data["wind_speeds"] else "-"
        
        # 風向：取頻率最高
        wind_dir_counter = Counter([d for d in current_day_data["wind_dirs"] if d != "N/A"])
        wind_dir = wind_dir_counter.most_common(1)[0][0] if wind_dir_counter else "-"

        # 舒適度/紫外線指數：取頻率最高
        comfort_max_counter = Counter([c for c in current_day_data["comfort_maxs"] if c != "N/A"])
        comfort_max = comfort_max_counter.most_common(1)[0][0] if comfort_max_counter else "-"
        
        comfort_min_counter = Counter([c for c in current_day_data["comfort_mins"] if c != "N/A"])
        comfort_min = comfort_min_counter.most_common(1)[0][0] if comfort_min_counter else "-"
        
        uv_index_counter = Counter([u for u in current_day_data["uv_indices"] if u != "N/A"])
        uv_index = uv_index_counter.most_common(1)[0][0] if uv_index_counter else "-"

        final_day_data = {
            "county_name": current_day_data["county_name"],
            # "num_days": current_day_data["num_days"],
            "obs_time": current_day_data["obs_time"],
            "date": current_day_data["date"],
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
            "loc_name": current_day_data["date"] # 暫時用日期鍵，後續會被縣市名稱覆蓋
        }
        final_days_aggregated.append(final_day_data)

    logger.debug(f"✅ 每日預報整理結果: {json.dumps(final_days_aggregated, ensure_ascii=False, indent=2)}")

    # 依序取前 N 天並建立 bubbles
    loc_name = f"{parsed_weather.get('county_name', 'N/A')}"
    for i, day_data in enumerate(final_days_aggregated):
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