# weekend_weather/weekend_forecast_converter.py
import logging
import datetime
from typing import List, Dict, Tuple
from linebot.v3.messaging.models import FlexBubble

# 導入穿搭建議邏輯
from outfit_suggestion.forecast_outfit_logic import get_outfit_suggestion_for_forecast_weather
# 導入 build_weekend_weather_flex 函數，用於生成週末天氣卡片
from weekend_weather.weekend_weather_flex import build_weekend_weather_flex
# 導入 build_forecast_outfit_card 函數，用於生成穿搭卡片
from outfit_suggestion.forecast_outfit_flex_messages import build_forecast_outfit_card
# 從 forecast_flex_converter 導入內部輔助函數
from weather_forecast.forecast_flex_converter import _aggregate_parsed_forecast_data

logger = logging.getLogger(__name__)

def get_weekend_forecast_flex_messages(
    parsed_full_forecast_data: Dict
    # include_outfit_suggestions: bool = False
) -> List[FlexBubble]:
    """
    獲取週末天氣預報的 Flex Message 氣泡列表。
    此函數會利用 forecast_flex_converter._aggregate_parsed_forecast_data 獲取所有日期的聚合數據，
    然後篩選出週末的數據並生成對應的 Flex Message。

    Args:
        parsed_full_forecast_data (Dict): 來自 weather_forecast_parser.parse_forecast_weather()
                                          的原始七天預報數據。
        include_outfit_suggestions (bool): 是否包含穿搭建議卡片。

    Returns:
        Tuple[List[FlexBubble], List[FlexBubble]]:
            包含兩個列表的元組：
            - 第一個列表是週末天氣預報的 FlexBubble 物件。
            - 第二個列表是週末穿搭建議的 FlexBubble 物件 (如果 include_outfit_suggestions 為 True)。
    """
    logger.info("開始處理週末天氣預報。")

    # 1. 使用 forecast_flex_converter 的內部輔助函數來獲取所有預報日的聚合數據
    all_aggregated_data = _aggregate_parsed_forecast_data(parsed_full_forecast_data)

    weekend_aggregated_data: List[Dict] = []

    for day_data in all_aggregated_data:
        # 篩選出週末數據 (星期六和星期日)
        # 這裡直接使用 parser 提供的 'is_weekend' 旗標
        logger.debug(f"📅 日期: {day_data.get('date_formatted')}, is_weekend: {day_data.get('is_weekend')}, 氣象資料：{day_data.get('display_weather_desc')}")
        if day_data.get("is_weekend"):
            weekend_aggregated_data.append(day_data)
        
        # 我們只關心週末，通常是兩天，一旦找到兩天就可以停止了
        if len(weekend_aggregated_data) >= 2:
            break

    logger.debug(f"✅ 週末預報數據已從完整預報中篩選完畢。總計 {len(weekend_aggregated_data)} 天數據。")

    weekend_weather_bubbles: List[FlexBubble] = []
    # weekend_outfit_bubbles: List[FlexBubble] = []

    loc_name = parsed_full_forecast_data.get("county_name", "無資料")
    for i, day_data_for_bubble in enumerate(weekend_aggregated_data):
        day_data_for_bubble['loc_name'] = loc_name
        day_data_for_bubble['day_index'] = i + 1 # 新增第幾天 (週末中的第一天/第二天)
        day_data_for_bubble["forecast_date"] = day_data_for_bubble.get("date_formatted", "未知日期")

        outfit_suggestion_data = get_outfit_suggestion_for_forecast_weather(day_data_for_bubble["raw_period_data_for_outfit"])

        current_outfit_info = {
        "suggestion_text": outfit_suggestion_data.get("suggestion_text", ["目前無法提供穿搭建議。"]),
        "suggestion_image_url": outfit_suggestion_data.get("suggestion_image_url", "https://i.imgur.com/default_forecast_outfit.png")
    }

        # 2. 將篩選出的週末數據用 build_single_weekend_weather_bubble 呈現
        # 這裡調用修改後的函數，它返回單個 FlexBubble
        weather_bubble = build_weekend_weather_flex(current_outfit_info, day_data_for_bubble, loc_name)
        if weather_bubble: # 檢查是否成功生成
            weekend_weather_bubbles.append(weather_bubble)

        """
        # 如果需要包含穿搭建議
        if include_outfit_suggestions:
            outfit_suggestion = get_outfit_suggestion_for_forecast_weather(day_data_for_bubble["raw_period_data_for_outfit"])

            outfit_info_for_card = {
                **day_data_for_bubble, # 包含所有 display_xxx 鍵
                **outfit_suggestion # 包含 outfit_description, outfit_image_url, outfit_tags
            }
        """

        """
        # 將 set 轉換為 list，以防 json.dumps 遇到問題
        if "raw_period_data_for_outfit" in outfit_info_for_card and \
            "weather_phenomena" in outfit_info_for_card["raw_period_data_for_outfit"] and \
            isinstance(outfit_info_for_card["raw_period_data_for_outfit"]["weather_phenomena"], set):
            outfit_info_for_card["raw_period_data_for_outfit"]["weather_phenomena"] = \
                list(outfit_info_for_card["raw_period_data_for_outfit"]["weather_phenomena"])
        """
        """
        # 建立穿搭建議卡片
        outfit_bubble_obj = build_forecast_outfit_card(outfit_info_for_card, loc_name, i)
        if outfit_bubble_obj: # 檢查是否成功生成
            weekend_outfit_bubbles.append(outfit_bubble_obj)
        """

    logger.info(f"✅ 週末天氣預報 Flex Messages 已生成，共 {len(weekend_weather_bubbles)} 個天氣卡片。")
    return weekend_weather_bubbles