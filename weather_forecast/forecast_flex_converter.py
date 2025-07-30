# forecast_flex_converter.py
# 處理從「原始解析數據」到「可填充到 LINE Flex Message 模板的格式」之間的複雜數據和聚合邏輯，並協調 forecast_builder_flex.py 來實際生成多個天氣預報卡片
import json
import datetime
import logging
from typing import Any, List, Dict
from collections import Counter
from linebot.v3.messaging.models import FlexMessage, FlexBubble, FlexCarousel
from .forecast_builder_flex import build_observe_weather_flex  # 已在同檔定義
from utils.forecast_outfit_logic import get_outfit_suggestion_for_forecast_weather
from life_reminders.forecast_outfit_flex_messages import build_forecast_outfit_card

logger = logging.getLogger(__name__)

def safe_float(val: Any) -> float | None:
    """嘗試安全地將值轉換為浮點數，失敗則返回 None。"""
    try:
        return float(val)
    except (ValueError, TypeError): # 捕捉更廣泛的錯誤
        return None
    
def safe_int(val: Any) -> int | None:
    """嘗試安全地將值轉換為整數，失敗則返回 None。"""
    try:
        return int(float(val)) # 先轉 float 再轉 int，處理 "25.0" 這種情況
    except (ValueError, TypeError):
        return None
    
# --- 新增的蒲福風級描述函數 ---
def get_beaufort_scale_description(wind_scale_int: int) -> str:
    """
    根據蒲福風級數字返回對應的文字描述。
    Args:
        wind_scale_int (int): 蒲福風級數字 (0-12)。
    Returns:
        str: 蒲福風級的文字描述。
    """
    if wind_scale_int == 0:
        return "無風"
    elif wind_scale_int == 1:
        return "軟風"
    elif wind_scale_int == 2:
        return "輕風"
    elif wind_scale_int == 3:
        return "微風"
    elif wind_scale_int == 4:
        return "和風"
    elif wind_scale_int == 5:
        return "清風"
    elif wind_scale_int == 6:
        return "強風"
    elif wind_scale_int == 7:
        return "疾風"
    elif wind_scale_int == 8:
        return "大風"
    elif wind_scale_int == 9:
        return "烈風"
    elif wind_scale_int == 10:
        return "狂風"
    elif wind_scale_int == 11:
        return "暴風"
    elif wind_scale_int == 12:
        return "颶風"
    else:
        return "N/A" # 超出範圍或無效風級

# --- 新增的風速轉換函式 ---
def convert_ms_to_beaufort_scale(wind_speed_ms: float) -> int:
    """
    將風速 (m/s) 轉換為蒲福風級 (Beaufort scale)。
    參考中央氣象署風級對照表 (簡化)。
    """
    if wind_speed_ms < 0.3:
        return 0 # 無風
    elif wind_speed_ms <= 1.5:
        return 1 # 軟風
    elif wind_speed_ms <= 3.3:
        return 2 # 輕風
    elif wind_speed_ms <= 5.4:
        return 3 # 微風
    elif wind_speed_ms <= 7.9:
        return 4 # 和風
    elif wind_speed_ms <= 10.7:
        return 5 # 勁風
    elif wind_speed_ms <= 13.8:
        return 6 # 強風
    elif wind_speed_ms <= 17.1:
        return 7 # 疾風
    elif wind_speed_ms <= 20.7:
        return 8 # 大風
    elif wind_speed_ms <= 24.4:
        return 9 # 烈風
    elif wind_speed_ms <= 28.4:
        return 10 # 狂風
    elif wind_speed_ms <= 32.6:
        return 11 # 暴風
    else:
        return 12 # 颶風 (或更高)

# --------- 將 parser 的結果 => Bubble 清單 ---------
def convert_forecast_to_bubbles(parsed_data: Dict, days: int, include_outfit_suggestions: bool = False) -> tuple[List[FlexBubble], List[FlexBubble]]:
    """
    將解析後的未來天氣預報數據轉換為 LINE Flex Message 的氣泡列表。
    此函數負責數據的聚合、格式化和協調穿搭建議的生成。

    Args:
        parsed_data (Dict): 來自 weather_forecast_parser.parse_forecast_weather() 的輸出。
        days (int): 需要生成預報的日數 (例如 3, 5, 7)。
        include_outfit_suggestions (bool): 是否包含穿搭建議卡片。

    Returns:
        tuple[List[FlexBubble], List[FlexBubble]]: 
            包含兩個列表的元組：
            - 第一個列表是每日天氣預報的 FlexBubble 物件。
            - 第二個列表是每日穿搭建議的 FlexBubble 物件 (如果 include_outfit_suggestions 為 True)。
    """
    logger.debug(f"第一筆 forecast_period 資料: {parsed_data.get('forecast_periods', [])[0] if parsed_data.get('forecast_periods') else '無資料'}")

    final_days_aggregated: List[Dict] = []

    for p in parsed_data.get("forecast_periods", []):
        # 提取當天的日期鍵，以便後續操作
        date_key = p.get("date")  # 例如: "2025-07-17"
        if not date_key:
            logger.warning("單一預報時段缺少 'date' 鍵，跳過處理。")
            continue

        # --- 新增日期和星期幾的處理 ---
        formatted_date_weekday = "N/A"
        try:
            # 假設 date_key 是 YYYY-MM-DD 格式
            date_obj = datetime.datetime.strptime(date_key, "%Y-%m-%d").date()
            
            # 獲取中文星期幾
            weekday_map = {
                0: "一", 1: "二", 2: "三", 3: "四",
                4: "五", 5: "六", 6: "日"
            }
            # weekday() 回傳 0=星期一, 6=星期日。我們需要轉換成 %w (0=星期日, 6=星期六)
            # 或者更簡單地，直接使用 strftime("%w") 來獲取 0-6 的數字，然後對應
            # weekday_num = date_obj.strftime("%w") # 0=星期一, 1=星期二, ..., 6=星期日
            # 調整為 %w 的對應關係 (0=日, 1=一, ...)
            # adjusted_weekday_num = (weekday_num + 1) % 7 # 0(一) -> 1, 6(日) -> 0
            
            chinese_weekday = weekday_map.get(date_obj.weekday(), "")

            # 格式化日期字串
            # 兼容不同系統的 strftime 格式
            try:
                formatted_date = date_obj.strftime("%Y年%-m月%-d日") # For Linux/macOS
            except ValueError:
                formatted_date = date_obj.strftime("%Y年%m月%d日") # For Windows

            formatted_date_weekday = f"日期：{formatted_date} ({chinese_weekday})"

        except ValueError as e:
            logger.error(f"日期格式化錯誤: {e}, 原始日期鍵: {date_key}")
        # --- 結束日期和星期幾的處理 ---

        # --- 數據聚合：從原始數據中提取並處理數值 (使用重構方式) ---
        # 初始化字典來收集所有數值和字串類型的值
        numeric_values: Dict[str, List[float]] = {
            "max_temp": [], "min_temp": [], "max_feel": [], "min_feel": [],
            "humidity": [], "pop": [], "wind_speed": [], "uv_index": []
        }
        string_values: Dict[str, List[str]] = {
            "weather_desc": [], "wind_dir": [], "comfort_max": [], "comfort_min": []
        }

        # 定義預期會有的時段後綴
        # 這裡包含 'unknown' 是為了更全面地處理可能存在的數據，即使目前 API 回傳沒有
        time_suffixes = ["_day", "_night", "_unknown"] 

        # 遍歷每個時段後綴，安全地提取數據
        for suffix in time_suffixes:
            # 提取數值類型數據
            for field_name in numeric_values:
                # 使用 .get() 並提供 None 作為預設值，如果鍵不存在，則返回 None
                raw_val = p.get(f"{field_name}{suffix}")
                safe_val = safe_float(raw_val) # 使用您的 safe_float 函數
                if safe_val is not None:
                    numeric_values[field_name].append(safe_val)
            
            # 提取字串類型數據
            for field_name in string_values:
                raw_val = p.get(f"{field_name}{suffix}")
                if raw_val is not None and str(raw_val).strip() not in ["N/A", "-"]: # 確保處理空字串和"N/A"
                    string_values[field_name].append(str(raw_val).strip())

        """
        # 初始化每日資料儲存用
        current_day_data = {
            "county_name": parsed_data.get("county_name", "N/A"),
            # "num_days": parsed_weather.get("num_days", 1),
            "obs_time": formatted_date_weekday, # 使用 parser 提供的格式化日期字串
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
            "uv_index_list": [],
            "raw_period_data": p
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
                if raw_val is not None and raw_val not in ["N/A", "-"]:
                    target_list_key = summary_key + "_list"
                    # 根據數據類型處理
                    if summary_key in ["max_temp", "max_feel", "min_temp", "min_feel", "humidity", "pop", "wind_speed", "uv_index"]:
                        val = safe_float(raw_val)
                        if val is not None:
                            current_day_data[target_list_key].append(val)
                    else: # 文本類型，如 weather_desc, wind_dir, comfort, uv_index
                        current_day_data[target_list_key].append(str(raw_val))
                    # 找到第一個有效值就跳出內層迴圈，因為是優先級
                    break
        """

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
        weather_desc_counter = Counter(string_values["weather_desc"])
        weather_desc_display = weather_desc_counter.most_common(1)[0][0] if string_values["weather_desc"] else "N/A"

        # 溫度/體感：取白天和夜晚的極值
        max_temp = max(numeric_values["max_temp"]) if numeric_values["max_temp"] else None
        min_temp = min(numeric_values["min_temp"]) if numeric_values["min_temp"] else None
        max_feel = max(numeric_values["max_feel"]) if numeric_values["max_feel"] else None
        min_feel = min(numeric_values["min_feel"]) if numeric_values["min_feel"] else None
        
        # 體感溫度顯示邏輯
        feels_like_display = "N/A"
        if max_feel is not None and min_feel is not None:
            # 確保體感溫度在顯示時也是 float，如果需要更精確
            if abs(max_feel - min_feel) < 1.0: # 如果差異小於1度，則顯示單一值
                feels_like_display = f"{min_feel:.1f}°C 與實際溫度相近" # 顯示單一體感溫度並註明相近
            else:
                feels_like_display = f"{min_feel:.1f}°C ~ {max_feel:.1f}°C"
        elif max_feel is not None:
            feels_like_display = f"{max_feel:.1f}°C"
        elif min_feel is not None:
            feels_like_display = f"{min_feel:.1f}°C"

        # 濕度：取平均值，並格式化
        humidity = round(sum(numeric_values["humidity"]) / len(numeric_values["humidity"]), 0) if numeric_values["humidity"] else None
        humidity_display = f"{int(humidity)}%" if humidity is not None else "N/A"
        
        # 降雨機率：取白天和夜晚的最大值，並格式化
        pop = max(numeric_values["pop"]) if numeric_values["pop"] else None
        pop_display = f"{int(pop)}%" if pop is not None else "N/A"

        # 風速：取最大值，並格式化
        raw_wind_speed_ms = max(numeric_values["wind_speed"]) if numeric_values["wind_speed"] else None
        wind_speed_beaufort_scale = None
        wind_speed_display = "N/A"
        if raw_wind_speed_ms is not None:
            wind_speed_beaufort_scale = convert_ms_to_beaufort_scale(raw_wind_speed_ms) # 蒲福風級
            wind_scale_description = get_beaufort_scale_description(wind_speed_beaufort_scale) # 蒲福風級描述
            wind_speed_display = f"{wind_speed_beaufort_scale} 級 ({wind_scale_description})" # 蒲福風級與描述的組合顯示

        # 風向：取頻率最高
        wind_dir_counter = Counter(string_values["wind_dir"])
        wind_dir_display = wind_dir_counter.most_common(1)[0][0] if string_values["wind_dir"] else "N/A"

        # 舒適度/紫外線指數：取頻率最高，並格式化紫外線指數
        comfort_max_counter = Counter(string_values["comfort_max"])
        comfort_max_display = comfort_max_counter.most_common(1)[0][0] if string_values["comfort_max"] else "N/A"

        comfort_min_counter = Counter(string_values["comfort_min"])
        comfort_min_display = comfort_min_counter.most_common(1)[0][0] if string_values["comfort_min"] else "N/A"

        uv_val = max(numeric_values["uv_index"]) if numeric_values["uv_index"] else None # 取 UV 最大值
        uv_index_display = "N/A"
        if uv_val is not None: # 確保 uv_val 是有效數字或可轉換為數字
            try:
                uv_int_val = int(uv_val) # 轉換為整數以便比較
                if uv_int_val >= 11:
                    uv_index_display = f"{uv_int_val} (危險)"
                elif uv_int_val >= 8:
                    uv_index_display = f"{uv_int_val} (過量)"
                elif uv_int_val >= 6:
                    uv_index_display = f"{uv_int_val} (高)"
                elif uv_int_val >= 3:
                    uv_index_display = f"{uv_int_val} (中)"
                elif uv_int_val >= 0: # 包含 0-2 的低級
                    uv_index_display = f"{uv_int_val} (低)"
                else: # 考慮負值或其他異常情況
                    uv_index_display = "N/A" # 或其他適當的默認值
            except (ValueError, TypeError):
                logger.warning(f"無法將 uv_val 值 '{uv_val}' 轉換為整數。設定為 N/A。")
                uv_index_display = "N/A" # 如果轉換失敗，也設為 "N/A"
        else:
            uv_index_display = "無" # 如果原始值是 '-' 或 'N/A'

        # 準備傳遞給 outfit_logic 的原始數值數據
        # 這裡需要確保所有值都是 int 或 float，且非 None
        processed_data_for_outfit_logic = {
            "weather_phenomena": set(string_values["weather_desc"]),
            "max_feels_like_temp": safe_int(max_feel) if max_feel is not None else 0,
            "min_feels_like_temp": safe_int(min_feel) if min_feel is not None else 0,
            "temp_range_diff": safe_int(max_feel - min_feel) if max_feel is not None and min_feel is not None else 0,
            "avg_humidity": safe_int(humidity) if humidity is not None else 0,
            "pop": safe_int(pop) if pop is not None else 0,
            "wind_speed": wind_speed_beaufort_scale if wind_speed_beaufort_scale is not None else 0, # 傳遞蒲福風級給穿搭邏輯
            "comfort_max_desc": comfort_max_display,
            "comfort_min_desc": comfort_min_display,
            "uvi": safe_int(uv_val) if uv_val is not None else 0,
        }

        # --- 格式化為顯示字串的數據 (用於 Flex Message) ---
        final_day_data = {
            "county_name": parsed_data.get("county_name", "N/A"),
            # "num_days": current_day_data["num_days"],
            "obs_time": formatted_date_weekday,
            "date": date_key,
            "loc_name": parsed_data.get("county_name", "N/A"), # 地點名稱
            "display_weather_desc": weather_desc_display,
            "display_max_temp": f"{int(max_temp)}°C" if max_temp is not None else "N/A",
            "display_min_temp": f"{int(min_temp)}°C" if min_temp is not None else "N/A",
            "display_feels_like_temp": feels_like_display, # 已經是 "X°C ~ Y°C" 或 "X°C"
            "display_humidity": humidity_display, # 已經是 "Z%"
            "display_pop": pop_display, # 已經是 "Z%"
            "display_wind_speed": wind_speed_display, # 使用格式化後的風速字串
            "display_wind_dir": wind_dir_display,
            "display_comfort_max": comfort_max_display,
            "display_comfort_min": comfort_min_display,
            "display_uv_index": uv_index_display, # 已經是 "X (描述)"
            "raw_period_data_for_outfit": processed_data_for_outfit_logic # 保留原始數據供 outfit_logic 使用
        }
        
        """
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
        """
        
        final_days_aggregated.append(final_day_data)

    logger.debug(f"✅ 每日預報數據已彙整完畢。總計 {len(final_days_aggregated)} 天數據。")

    general_weather_bubbles: List[FlexBubble] = []
    outfit_suggestion_bubbles: List[FlexBubble] = [] # 這個列表將包含每天的完整 outfit_info

    # logger.debug(f"✅ 每日預報整理結果: {json.dumps(final_days_aggregated, ensure_ascii=False, indent=2)}")


    # 依序取前 N 天並建立 bubbles
    loc_name = f"{parsed_data.get('county_name', 'N/A')}"
    for i, day_data_for_bubble in enumerate(final_days_aggregated):
        if i >= days:
            break

        day_data_for_bubble['loc_name'] = loc_name
        day_data_for_bubble['day_index'] = i + 1  # 新增第幾天
        # bubbles.append(build_observe_weather_flex(day_data))

        data_for_flex = day_data_for_bubble.copy() # 建立一個副本，避免影響原始數據或 outfit_logic

        # 將 processed_data_for_outfit_logic 中的 set 轉換為 list
        if "raw_period_data_for_outfit" in data_for_flex:
            if "weather_phenomena" in data_for_flex["raw_period_data_for_outfit"] and \
            isinstance(data_for_flex["raw_period_data_for_outfit"]["weather_phenomena"], set):
                
                data_for_flex["raw_period_data_for_outfit"]["weather_phenomena"] = \
                    list(data_for_flex["raw_period_data_for_outfit"]["weather_phenomena"])

        general_weather_bubbles.append(build_observe_weather_flex(day_data_for_bubble, days))

        # 如果需要包含穿搭建議，則生成穿搭建議數據
        if include_outfit_suggestions:
            # 將處理過的數值數據傳遞給穿搭建議邏輯
            outfit_suggestion = get_outfit_suggestion_for_forecast_weather(day_data_for_bubble["raw_period_data_for_outfit"])
            
            # 將格式化後的天氣數據和穿搭建議合併，形成一個完整的 outfit_info 字典
            outfit_info_for_card = {
                **day_data_for_bubble, # 包含所有 display_xxx 鍵
                **outfit_suggestion # 包含 outfit_description, outfit_image_url, outfit_tags
            }

            # 同樣，在 build_forecast_outfit_card 中進行 JSON 序列化之前，也可能需要將 set 轉換為 list
            # 這裡也建立一個副本並轉換，以防 build_forecast_outfit_card 內部也有 json.dumps
            outfit_data_for_card_flex = outfit_info_for_card.copy()
            if "raw_period_data_for_outfit" in outfit_data_for_card_flex and \
            "weather_phenomena" in outfit_data_for_card_flex["raw_period_data_for_outfit"] and \
            isinstance(outfit_data_for_card_flex["raw_period_data_for_outfit"]["weather_phenomena"], set):
                
                outfit_data_for_card_flex["raw_period_data_for_outfit"]["weather_phenomena"] = \
                    list(outfit_data_for_card_flex["raw_period_data_for_outfit"]["weather_phenomena"])

            outfit_bubble_obj = build_forecast_outfit_card(outfit_info_for_card, loc_name, i) # 這裡傳入 i 作為 day_offset
            outfit_suggestion_bubbles.append(outfit_bubble_obj)
            
            # all_outfit_data_for_carousel.append(outfit_info_for_card)

    logger.debug(f"✅ 每日天氣資料已整理完畢。共生成 {len(general_weather_bubbles)} 個天氣預報卡片。")
    if include_outfit_suggestions:
        logger.debug(f"✅ 穿搭建議卡片已整理完畢。共生成 {len(outfit_suggestion_bubbles)} 個穿搭卡片。")

    # 返回兩個列表
    return general_weather_bubbles, outfit_suggestion_bubbles

def build_flex_carousel(bubble_list: List[FlexBubble], alt_text="天氣預報") -> FlexMessage:
    """bubble_list: List[FlexBubble]  →  FlexMessage 物件"""
    return FlexMessage(
        alt_text=alt_text,
        contents=FlexCarousel(contents=bubble_list)
    )