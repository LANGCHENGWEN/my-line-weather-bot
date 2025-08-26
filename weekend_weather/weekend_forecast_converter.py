# weekend_weather/weekend_forecast_converter.py
"""
LINE bot 處理「週末天氣預報」功能的數據轉換器。
主要職責：
1. 篩選數據：從完整的七天預報數據中，精準的篩選出屬於週末（星期六和星期日）的數據。
2. 數據處理：對每個週末日期的數據進行加工，使其符合 Flex Message 的呈現格式。
3. 動態生成內容：根據每個週末日期的天氣狀況，呼叫 `outfit_suggestion` 邏輯，獲取該日的穿搭建議。
4. 組建 Flex Message：呼叫 `build_weekend_weather_flex` 函式，將天氣數據和動態生成的穿搭建議組合成一個美觀的 Flex Message 氣泡（bubble）。
5. 回傳結果：將生成的 Flex Message 氣泡列表返回，以便 LINE bot 能夠發送給用戶。
"""
import logging
from typing import List, Dict
from linebot.v3.messaging.models import FlexBubble

from weekend_weather.weekend_weather_flex import build_weekend_weather_flex
from weather_forecast.forecast_flex_converter import _aggregate_parsed_forecast_data
from outfit_suggestion.forecast_outfit_logic import get_outfit_suggestion_for_forecast_weather

logger = logging.getLogger(__name__)

# --- 獲取週末天氣預報的 Flex Message 氣泡列表 ---
def get_weekend_forecast_flex_messages(parsed_full_forecast_data: Dict) -> List[FlexBubble]:
    """
    生成週末天氣卡片的主要流程控制中心。
    首先調用輔助函式將原始數據聚合，然後遍歷聚合後的數據，只篩選出週末的數據。
    對於每一天的週末數據，都會單獨處理：
    呼叫穿搭建議邏輯、將數據格式化，然後調用 `build_weekend_weather_flex` 函式生成一個單獨的 Flex Message 氣泡。
    最後將所有生成的氣泡收集成一個列表並返回。

    Args:
        parsed_full_forecast_data (Dict): 來自 weather_forecast_parser.parse_forecast_weather() 的原始七天預報數據。

    Returns:
        List[FlexBubble]: 週末天氣預報的 FlexBubble 物件。
    """
    logger.info("開始處理週末天氣預報。")

    # --- 數據聚合與週末篩選 ---
    """
    從完整的七天預報數據中，精確的找出週末的數據。
    """
    # 獲取所有預報日的聚合數據
    all_aggregated_data = _aggregate_parsed_forecast_data(parsed_full_forecast_data)
    weekend_aggregated_data: List[Dict] = []

    # 遍歷聚合後的數據，篩選出週末數據 (星期六和星期日)
    for day_data in all_aggregated_data:
        logger.debug(f"📅 日期: {day_data.get('date_formatted')}, is_weekend: {day_data.get('is_weekend')}, 氣象資料：{day_data.get('display_weather_desc')}")
        # 判斷該日期是否為週末
        if day_data.get("is_weekend"): # 使用 weather_forecast_parser.py 提供的 'is_weekend' 鍵
            weekend_aggregated_data.append(day_data)
        
        # 一旦找到足夠的週末數據（通常是兩天），就會立即停止遍歷
        if len(weekend_aggregated_data) >= 2:
            break

    logger.debug(f"✅ 週末預報數據已從完整預報中篩選完畢。總計 {len(weekend_aggregated_data)} 天數據。")

    weekend_weather_bubbles: List[FlexBubble] = []

    # --- 逐日處理與 Flex Message 生成 ---
    """
    為每一天的週末數據，生成一個單獨的 Flex Message 氣泡。
    """
    loc_name = parsed_full_forecast_data.get("county_name", "無資料")
    # 遍歷前面篩選出的 `weekend_aggregated_data` 列表
    for i, day_data_for_bubble in enumerate(weekend_aggregated_data):
        # 在每次迴圈中，將地點名稱和當日索引（例如「第一天」、「第二天」）添加到數據字典中，以便於後續使用
        day_data_for_bubble['loc_name'] = loc_name
        day_data_for_bubble['day_index'] = i + 1 # 新增第幾天 (週末中的第一天/第二天)
        day_data_for_bubble["forecast_date"] = day_data_for_bubble.get("date_formatted", "未知日期")

        # 根據當日的原始數據，獲取穿搭建議
        outfit_suggestion_data = get_outfit_suggestion_for_forecast_weather(day_data_for_bubble["raw_period_data_for_outfit"])
        current_outfit_info = {
        "suggestion_text": outfit_suggestion_data.get("suggestion_text", ["目前無法提供穿搭建議。"]),
        "suggestion_image_url": outfit_suggestion_data.get("suggestion_image_url", "https://i.imgur.com/default_forecast_outfit.png")
    }

        # 將當日的天氣數據和穿搭建議整合，生成一個完整的 Flex Message 氣泡，並添加到 `weekend_weather_bubbles` 列表中
        weather_bubble = build_weekend_weather_flex(current_outfit_info, day_data_for_bubble, loc_name)
        if weather_bubble:
            weekend_weather_bubbles.append(weather_bubble)

    logger.info(f"✅ 週末天氣預報 Flex Messages 已生成，共 {len(weekend_weather_bubbles)} 個天氣卡片。")
    return weekend_weather_bubbles