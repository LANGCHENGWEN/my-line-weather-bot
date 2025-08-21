# weather_forecast/forecast_flex_converter.py
"""
天氣預報功能的核心協調者。
將從中央氣象署 API 取得的原始 JSON 數據轉換為可直接用於 LINE Flex Message 的格式。
主要職責：
1. 數據聚合：將原始數據中多個時段的數據（如白天、晚上）進行彙整，計算每日的最高溫、最低溫、平均濕度等。
2. 數據格式化：將聚合後的數值數據轉換為適合閱讀的字串，例如將風速轉換為蒲福風級描述。
3. 卡片生成：協調 `forecast_builder_flex.py` 和 `forecast_outfit_flex_messages.py`，根據處理好的數據動態生成多個 Flex Bubble 物件。
4. 最終封裝：將多個 Flex Bubble 物件組合成一個 Flex Carousel 物件，方便在 LINE 上滑動瀏覽。
"""
import logging
from collections import Counter
from typing import Any, List, Dict
from linebot.v3.messaging.models import FlexMessage, FlexBubble, FlexCarousel

from utils.weather_utils import get_beaufort_scale_description, convert_ms_to_beaufort_scale

from .forecast_builder_flex import build_observe_weather_flex

from outfit_suggestion.forecast_outfit_flex_messages import build_forecast_outfit_card
from outfit_suggestion.forecast_outfit_logic import get_outfit_suggestion_for_forecast_weather

logger = logging.getLogger(__name__)

def safe_float(val: Any) -> float | None:
    """
    安全的將值轉換為浮點數，失敗則返回 None。
    """
    try:
        return float(val)
    except (ValueError, TypeError):
        return None
    
def safe_int(val: Any) -> int | None:
    """
    安全的將值轉換為整數，失敗則返回 None。
    """
    try:
        return int(float(val)) # 先轉 float 再轉 int，處理 "25.0" 這種情況
    except (ValueError, TypeError):
        return None

# --- 聚合解析後的未來天氣預報數據 ---
def _aggregate_parsed_forecast_data(parsed_data: Dict) -> List[Dict]:
    """
    這個函式只負責數據的提取、處理和彙整，不生成 FlexBubble，也不處理日期格式化（由 weather_forecast_parser.py 完成）。
    其結果會被 convert_forecast_to_bubbles 和 get_weekend_forecast_flex_messages 使用。

    Args:
        parsed_data (Dict): 來自 weather_forecast_parser.parse_forecast_weather() 的輸出。

    Returns:
        List[Dict]: 包含每日聚合天氣數據的列表。
    """
    logger.debug(f"開始聚合原始預報數據。第一筆資料: {parsed_data.get('forecast_periods', [])[0] if parsed_data.get('forecast_periods') else '無資料'}")

    final_days_aggregated: List[Dict] = []

    # 數據處理
    """
    迭代解析器已經處理好的每一天的預報數據，並將每日的數據（包含白天和晚上的時段）聚合為一個單一的字典。
    提取數值型和字串型數據，並分別進行處理：
    - 數值型數據（如溫度、濕度、降雨機率）會取極值或平均值。
    - 字串型數據（如天氣描述、風向）會找出出現頻率最高的值。
    """
    for p in parsed_data.get("forecast_periods", []):
        # 這裡的 p 已經包含了 'date', 'date_obj', 'date_prefix', 'date_str', 'is_weekend'
        # 提取當天的日期鍵，以便後續操作
        date_key = p.get("date")
        if not date_key:
            logger.warning("單一預報時段缺少 'date' 鍵，跳過處理。")
            continue

        # --- 數據聚合：從原始數據中提取並處理數值 ---
        numeric_values: Dict[str, List[float]] = {
            "max_temp": [], "min_temp": [], "max_feel": [], "min_feel": [],
            "humidity": [], "pop": [], "wind_speed": [], "uv_index": []
        }
        string_values: Dict[str, List[str]] = {
            "weather_desc": [], "wind_dir": [], "comfort_max": [], "comfort_min": []
        }

        # 定義時段後綴
        # 這裡包含 'unknown' 是為了更全面的處理可能存在的數據
        time_suffixes = ["_day", "_night", "_unknown"] 

        # --- 遍歷每個時段後綴，安全的提取數據 ---
        for suffix in time_suffixes:
            # 提取數值類型數據
            for field_name in numeric_values:
                # 使用 .get() 並提供 None 作為預設值；如果鍵不存在，則返回 None
                raw_val = p.get(f"{field_name}{suffix}")
                safe_val = safe_float(raw_val)
                if safe_val is not None:
                    numeric_values[field_name].append(safe_val)
            
            # 提取字串類型數據
            for field_name in string_values:
                raw_val = p.get(f"{field_name}{suffix}")
                if raw_val is not None and str(raw_val).strip() not in ["無資料", "-"]:
                    string_values[field_name].append(str(raw_val).strip())

        # --- 將累積的每日數據進行最終彙整 (取極值、平均值、最常見值) ---
        weather_desc_counter = Counter(string_values["weather_desc"])
        weather_desc_display = weather_desc_counter.most_common(1)[0][0] if string_values["weather_desc"] else "無資料"

        # 溫度/體感：取白天和夜晚的極值
        max_temp = max(numeric_values["max_temp"]) if numeric_values["max_temp"] else None
        min_temp = min(numeric_values["min_temp"]) if numeric_values["min_temp"] else None
        max_feel = max(numeric_values["max_feel"]) if numeric_values["max_feel"] else None
        min_feel = min(numeric_values["min_feel"]) if numeric_values["min_feel"] else None
        
        # 體感溫度
        """
        如果最高和最低體感溫度的差異非常小（小於 1 度），只顯示一個值並加上「與實際溫度相近」的註解。
        否則，顯示一個範圍，例如「25.0°C ~ 30.0°C」。
        """
        feels_like_display = "無資料"
        if max_feel is not None and min_feel is not None:
            if abs(max_feel - min_feel) < 1.0:
                feels_like_display = f"{min_feel:.1f}°C 與實際溫度相近"
            else:
                feels_like_display = f"{min_feel:.1f}°C ~ {max_feel:.1f}°C"
        elif max_feel is not None:
            feels_like_display = f"{max_feel:.1f}°C"
        elif min_feel is not None:
            feels_like_display = f"{min_feel:.1f}°C"

        # 濕度：取平均值，並格式化
        humidity = round(sum(numeric_values["humidity"]) / len(numeric_values["humidity"]), 0) if numeric_values["humidity"] else None
        humidity_display = f"{int(humidity)}%" if humidity is not None else "無資料"
        
        # 降雨機率：取白天和夜晚的最大值，並格式化
        pop = max(numeric_values["pop"]) if numeric_values["pop"] else None
        pop_display = f"{int(pop)}%" if pop is not None else "無資料"

        # 風速：取最大值，並格式化
        """
        將原始的風速（單位為 m/s）轉換為更直觀的「蒲福風級」，並附上對應的文字描述。
        """
        raw_wind_speed_ms = max(numeric_values["wind_speed"]) if numeric_values["wind_speed"] else None
        wind_speed_beaufort_scale = None
        wind_speed_display = "無資料"
        if raw_wind_speed_ms is not None:
            wind_speed_beaufort_scale = convert_ms_to_beaufort_scale(raw_wind_speed_ms)        # 蒲福風級
            wind_scale_description = get_beaufort_scale_description(wind_speed_beaufort_scale) # 蒲福風級描述
            wind_speed_display = f"{wind_speed_beaufort_scale} 級 ({wind_scale_description})"  # 蒲福風級與描述的組合顯示

        # 風向：取頻率最高
        wind_dir_counter = Counter(string_values["wind_dir"])
        wind_dir_display = wind_dir_counter.most_common(1)[0][0] if string_values["wind_dir"] else "無資料"

        # 舒適度/紫外線指數：取頻率最高，並格式化紫外線指數
        """
        根據紫外線指數的數值，附加對應的危險等級描述，例如「11 (危險)」或「6 (高)」。
        """
        comfort_max_counter = Counter(string_values["comfort_max"])
        comfort_max_display = comfort_max_counter.most_common(1)[0][0] if string_values["comfort_max"] else "無資料"

        comfort_min_counter = Counter(string_values["comfort_min"])
        comfort_min_display = comfort_min_counter.most_common(1)[0][0] if string_values["comfort_min"] else "無資料"

        uv_val = max(numeric_values["uv_index"]) if numeric_values["uv_index"] else None
        uv_index_display = "無資料"
        if uv_val is not None:
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
                    uv_index_display = "無資料"
            except (ValueError, TypeError):
                logger.warning(f"無法將 uv_val 值 '{uv_val}' 轉換為整數。設定為無資料。")
                uv_index_display = "無資料" # 如果轉換失敗，也設為 "無資料"
        else:
            uv_index_display = "無資料"

        # --- 傳遞給 forecast_outfit_logic.py 的原始數值數據 ---
        # 這裡需要確保所有值都是 int 或 float，且非 None
        processed_data_for_outfit_logic = {
            "weather_phenomena": set(string_values["weather_desc"]),
            "max_feels_like_temp": safe_int(max_feel) if max_feel is not None else 0,
            "min_feels_like_temp": safe_int(min_feel) if min_feel is not None else 0,
            "temp_range_diff": safe_int(max_feel - min_feel) if max_feel is not None and min_feel is not None else 0,
            "avg_humidity": safe_int(humidity) if humidity is not None else 0,
            "pop": safe_int(pop) if pop is not None else 0,
            "wind_speed": wind_speed_beaufort_scale if wind_speed_beaufort_scale is not None else 0,
            "comfort_max_desc": comfort_max_display,
            "comfort_min_desc": comfort_min_display,
            "uvi": safe_int(uv_val) if uv_val is not None else 0
        }

        # --- 格式化為顯示字串的數據 (用於 Flex Message) ---
        # 直接使用 weather_forecast_parser.py 提供的日期和地點資訊
        final_day_data = {
            "county_name": parsed_data.get("county_name", "無資料"),
            "obs_time": p.get("date_str"),
            "date": date_key,
            "loc_name": parsed_data.get("county_name", "無資料"),
            "display_weather_desc": weather_desc_display,
            "display_max_temp": f"{int(max_temp)}°C" if max_temp is not None else "無資料",
            "display_min_temp": f"{int(min_temp)}°C" if min_temp is not None else "無資料",
            "display_feels_like_temp": feels_like_display,
            "display_humidity": humidity_display,
            "display_pop": pop_display,
            "display_wind_speed": wind_speed_display,
            "display_wind_dir": wind_dir_display,
            "display_comfort_max": comfort_max_display,
            "display_comfort_min": comfort_min_display,
            "display_uv_index": uv_index_display,
            "raw_period_data_for_outfit": processed_data_for_outfit_logic, # 保留原始數據供 forecast_outfit_logic.py 使用
            "date_obj": p.get("date_obj"),
            "is_weekend": p.get("is_weekend"),
            "date_prefix": p.get("date_prefix"),
            "date_formatted": p.get("date_str") # ***週末天氣的日期一直沒有數據，是因為沒有增加這行
        }
        
        final_days_aggregated.append(final_day_data)

    logger.debug(f"✅ 每日預報數據已彙整完畢。總計 {len(final_days_aggregated)} 天數據。")
    return final_days_aggregated

# --- 將解析後的未來天氣預報數據轉換為 LINE Flex Message 的氣泡列表 ---
def convert_forecast_to_bubbles(parsed_data: Dict, days: int, include_outfit_suggestions: bool = False) -> tuple[List[FlexBubble], List[FlexBubble]]:
    """
    此函式負責數據的聚合、格式化和協調穿搭建議的生成。

    Args:
        parsed_data (Dict): 來自 weather_forecast_parser.parse_forecast_weather() 的輸出。
        days (int): 需要生成預報的日數 (例如 3, 5, 7)。
        include_outfit_suggestions (bool): 是否包含穿搭建議卡片。

    Returns:
        tuple[List[FlexBubble], List[FlexBubble]]: 
            包含兩個列表的元組：
            - 第一個列表：每日天氣預報的 FlexBubble 物件。
            - 第二個列表：每日穿搭建議的 FlexBubble 物件。
    """
    logger.debug(f"呼叫 convert_forecast_to_bubbles。")

    # 使用內部輔助函式獲取聚合後的數據
    all_aggregated_data = _aggregate_parsed_forecast_data(parsed_data)

    general_weather_bubbles: List[FlexBubble] = []
    outfit_suggestion_bubbles: List[FlexBubble] = []

    # 迴圈生成卡片
    """
    迭代聚合後的每日數據，根據指定的 `days` 參數，為每一天生成一個天氣預報卡片。
    如果 `include_outfit_suggestions` 參數為 True，會呼叫 `get_outfit_suggestion_for_forecast_weather` 函式，根據每日的天氣條件生成一套穿搭建議，並封裝成另一個 Flex Bubble 卡片。
    天氣預報卡片和穿搭建議卡片可以獨立生成，並最終被合併到同一個輪播訊息中。
    """
    loc_name = f"{parsed_data.get('county_name', '無資料')}"
    for i, day_data_for_bubble in enumerate(all_aggregated_data):
        if i >= days:
            break

        day_data_for_bubble['loc_name'] = loc_name # 確保 loc_name 傳遞給 Flex 模板
        day_data_for_bubble['day_index'] = i + 1   # 新增第幾天

        data_for_flex = day_data_for_bubble.copy() # 建立一個副本，避免影響原始數據

        # 將 processed_data_for_outfit_logic 中的 set 轉換為 list
        # 由於 JSON 序列化無法處理 set，因此在傳遞給可能進行 json.dumps 的函式之前需要轉換
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
            
            # 將格式化後的天氣數據和穿搭建議合併，形成一個完整的字典
            outfit_info_for_card = {
                **day_data_for_bubble, # 包含所有 display_xxx 鍵
                **outfit_suggestion    # 包含 outfit_description, outfit_image_url
            }

            # 同樣在 build_forecast_outfit_card 中進行 JSON 序列化之前，也需要將 set 轉換為 list
            # 這裡也建立一個副本並轉換，以防 build_forecast_outfit_card 內部也有 json.dumps
            outfit_data_for_card_flex = outfit_info_for_card.copy()
            if "raw_period_data_for_outfit" in outfit_data_for_card_flex and \
                "weather_phenomena" in outfit_data_for_card_flex["raw_period_data_for_outfit"] and \
                isinstance(outfit_data_for_card_flex["raw_period_data_for_outfit"]["weather_phenomena"], set):
                    outfit_data_for_card_flex["raw_period_data_for_outfit"]["weather_phenomena"] = \
                        list(outfit_data_for_card_flex["raw_period_data_for_outfit"]["weather_phenomena"])

            outfit_bubble_obj = build_forecast_outfit_card(outfit_info_for_card, loc_name, i) # 這裡傳入 i 作為 day_offset
            outfit_suggestion_bubbles.append(outfit_bubble_obj)

    logger.debug(f"✅ 每日天氣資料已整理完畢。共生成 {len(general_weather_bubbles)} 個天氣預報卡片。")
    if include_outfit_suggestions:
        logger.debug(f"✅ 穿搭建議卡片已整理完畢。共生成 {len(outfit_suggestion_bubbles)} 個穿搭建議卡片。")

    # 返回兩個列表
    return general_weather_bubbles, outfit_suggestion_bubbles

# --- 將一個或多個 FlexBubble 物件封裝成一個 FlexCarousel 物件，並最終回傳一個完整的 FlexMessage ---
def build_flex_carousel(bubble_list: List[FlexBubble], alt_text="天氣預報") -> FlexMessage:
    """
    多個卡片可以並排顯示，用戶可以左右滑動來查看每一天的預報。

    Args:
        bubble_list (List[FlexBubble]): 包含一個或多個 FlexBubble 物件的列表。
        alt_text (str): 當 FlexMessage 無法顯示時的替代文字。

    Returns:
        FlexMessage: 完整的 LINE Flex Message 物件。
    """
    return FlexMessage(
        alt_text=alt_text,
        contents=FlexCarousel(contents=bubble_list)
    )