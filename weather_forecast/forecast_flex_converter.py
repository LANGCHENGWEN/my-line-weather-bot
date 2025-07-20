# forecast_flex_converter.py
# 處理從「原始解析數據」到「可填充到 LINE Flex Message 模板的格式」之間的複雜數據和聚合邏輯，並協調 forecast_builder_flex.py 來實際生成多個天氣預報卡片
import json
import logging
from typing import Any, List, Dict
from collections import Counter
from linebot.v3.messaging.models import FlexMessage, FlexCarousel
from .forecast_builder_flex import build_observe_weather_flex  # 已在同檔定義

logger = logging.getLogger(__name__)

def safe_float(val: Any) -> float | None:
    try:
        return float(val) # 嘗試轉換為 float，如果失敗則返回 None
    except (ValueError, TypeError): # 捕捉更廣泛的錯誤
        return None

# --------- 將 parser 的結果 => Bubble 清單 ---------
def convert_forecast_to_bubbles(parsed_data: Dict, days: int) -> List[Dict]:
    """
    parsed_weather: weather_forecast_parser.parse_forecast_weather() 的輸出
    max_days: 3 / 5 / 7
    回傳: [bubble1, bubble2, ...]
    """
    logger.debug(f"第一筆 forecast_period 資料: {parsed_data.get('forecast_periods', [])[0] if parsed_data.get('forecast_periods') else '無資料'}")
    bubbles: List[Dict] = []

    final_days_aggregated: List[Dict] = []

    for p in parsed_data.get("forecast_periods", []):
        # 提取當天的日期鍵，以便後續操作
        date_key = p.get("date")  # 例如: "2025-07-17"
        if not date_key:
            logger.warning("單一預報時段缺少 'date' 鍵，跳過處理。")
            continue

        # 初始化每日資料儲存用
        current_day_data = {
            "county_name": parsed_data.get("county_name", "N/A"),
            # "num_days": parsed_weather.get("num_days", 1),
            "obs_time": p.get("date_str", "N/A"), # 使用 parser 提供的格式化日期字串
            "date": date_key, # 原始日期鍵
            # 儲存多個欄位的累積值
            "weather_desc_list": [],
            "max_temp_list": [],
            "max_feel_list": [],
            "min_temp_list": [],
            "min_feel_list": [],
            "humidity_list": [],
            "pop_list": [],
            "wind_speed_list": [],
            "wind_dir_list": [],
            "comfort_max_list": [],
            "comfort_min_list": [],
            "uv_index_list": []
        }
        # 可在這裡做「取極值」或「覆蓋」… 視需求而定

        # 定義數據提取的優先級順序 (從高到低)
        # 這裡的順序是 (day, night, unknown)
        # 例如，對於天氣描述，先找 weather_desc_day，然後 weather_desc_night，最後 weather_desc_unknown
        data_fields = {
            "weather_desc": ["weather_desc_day", "weather_desc_night", "weather_desc_unknown"],
            "max_temp": ["max_temp_day", "max_temp_night", "max_temp_unknown"],
            "max_feel": ["max_feel_day", "max_feel_night", "max_feel_unknown"],
            "min_temp": ["min_temp_day", "min_temp_night", "min_temp_unknown"],
            "min_feel": ["min_feel_day", "min_feel_night", "min_feel_unknown"],
            "humidity": ["humidity_day", "humidity_night", "humidity_unknown"],
            "pop": ["pop_day", "pop_night", "pop_unknown"],
            "wind_speed": ["wind_speed_day", "wind_speed_night", "wind_speed_unknown"],
            "wind_dir": ["wind_dir_day", "wind_dir_night", "wind_dir_unknown"],
            "comfort_max": ["comfort_max_day", "comfort_max_night", "comfort_max_unknown"],
            "comfort_min": ["comfort_min_day", "comfort_min_night", "comfort_min_unknown"],
            "uv_index": ["uv_index_day", "uv_index_night", "uv_index_unknown"]
        }

        # 迭代所有數據字段，根據優先級提取值並添加到對應的列表中
        for summary_key, source_keys in data_fields.items():
            for source_key in source_keys:
                raw_val = p.get(source_key)
                if raw_val is not None and raw_val != "N/A" and raw_val != "-":
                    target_list_key = summary_key + "_list"
                    # 根據數據類型處理
                    if summary_key in ["max_temp", "max_feel", "min_temp", "min_feel", "humidity", "pop", "wind_speed"]:
                        val = safe_float(raw_val)
                        if val is not None:
                            current_day_data[target_list_key].append(val)
                    else: # 文本類型，如 weather_desc, wind_dir, comfort, uv_index
                        current_day_data[target_list_key].append(str(raw_val))
                    # 找到第一個有效值就跳出內層迴圈，因為是優先級
                    break

        """
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
        """

        # --- 將累積的每日數據進行最終彙整 (取極值、平均值、最常見值) ---
        weather_desc_counter = Counter([d for d in current_day_data["weather_desc_list"] if d != "N/A"])
        weather_desc = weather_desc_counter.most_common(1)[0][0] if weather_desc_counter else "N/A"

        # 溫度/體感：取白天和夜晚的極值
        max_temp = max(current_day_data["max_temp_list"]) if current_day_data["max_temp_list"] else "-"
        max_feel = max(current_day_data["max_feel_list"]) if current_day_data["max_feel_list"] else "-"
        min_temp = min(current_day_data["min_temp_list"]) if current_day_data["min_temp_list"] else "-"
        min_feel = min(current_day_data["min_feel_list"]) if current_day_data["min_feel_list"] else "-"
        
        # 濕度：取平均值
        humidity = round(sum(current_day_data["humidity_list"]) / len(current_day_data["humidity_list"]), 1) if current_day_data["humidity_list"] else "-"
        # ⚠️ 修改濕度：如果不是 "-"，就轉換成整數
        if humidity != "-":
            humidity = int(humidity) # 或者 str(int(humidity)) 如果最終需要的是字串
        
        # 降雨機率：取白天和夜晚的最大值
        pop = max(current_day_data["pop_list"]) if current_day_data["pop_list"] else "-"
        # ⚠️ 修改降雨機率：如果不是 "-"，就轉換成整數
        if pop != "-":
            pop = int(pop) # 或者 str(int(pop)) 如果最終需要的是字串

        # 風速：取最大值
        wind_speed = max(current_day_data["wind_speed_list"]) if current_day_data["wind_speed_list"] else "-"
        
        # 風向：取頻率最高
        wind_dir_counter = Counter([d for d in current_day_data["wind_dir_list"] if d not in ["N/A", "-"]])
        wind_dir = wind_dir_counter.most_common(1)[0][0] if wind_dir_counter else "-"

        # 舒適度/紫外線指數：取頻率最高
        comfort_max_counter = Counter([c for c in current_day_data["comfort_max_list"] if c not in ["N/A", "-"]])
        comfort_max = comfort_max_counter.most_common(1)[0][0] if comfort_max_counter else "-"
        
        comfort_min_counter = Counter([c for c in current_day_data["comfort_min_list"] if c not in ["N/A", "-"]])
        comfort_min = comfort_min_counter.most_common(1)[0][0] if comfort_min_counter else "-"
        
        uv_index_counter = Counter([u for u in current_day_data["uv_index_list"] if u not in ["N/A", "-"]])
        uv_val = uv_index_counter.most_common(1)[0][0] if uv_index_counter else "-"

        # 🚀 這裡插入您的程式碼片段
        if uv_val != '-' and uv_val != 'N/A': # 確保 uv_val 是有效數字或可轉換為數字
            try:
                uv_int_val = int(float(uv_val)) # 轉換為整數以便比較
                if uv_int_val >= 11:
                    uv_index = f"{uv_int_val} (危險級)"
                elif uv_int_val >= 8:
                    uv_index = f"{uv_int_val} (過量級)"
                elif uv_int_val >= 6:
                    uv_index = f"{uv_int_val} (高)"
                elif uv_int_val >= 3:
                    uv_index = f"{uv_int_val} (中)"
                elif uv_int_val >= 0: # 包含 0-2 的低級
                    uv_index = f"{uv_int_val} (低)"
                else: # 考慮負值或其他異常情況
                    uv_index = "-" # 或其他適當的默認值
            except (ValueError, TypeError):
                uv_index = "-" # 如果轉換失敗，也設為 "-"
        else:
            uv_index = "無" # 如果原始值是 '-' 或 'N/A'

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
    loc_name = f"{parsed_data.get('county_name', 'N/A')}"
    for i, day_data in enumerate(final_days_aggregated):
        if i >= days:
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