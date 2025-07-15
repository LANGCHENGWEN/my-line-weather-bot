# line_forecast_messaging.py
# 專門處理「未來天氣」FlexMessage 的格式化
import logging
from typing import List

from linebot.v3.messaging.models import (
    FlexMessage, FlexBubble, FlexBox, FlexText
)

from .forecast_flex_converter import (
    convert_forecast_to_bubbles, build_flex_carousel
)

# from .forecast_builder_flex import make_kv_row, build_observe_weather_flex
# from outfit_advisor import generate_outfit_suggestion # 假設您有這個模組
# from line_common_messaging import send_line_reply_message, send_api_error_message

logger = logging.getLogger(__name__)

# --- 格式化預報天氣訊息 ---
def build_forecast_weather_flex(parsed_weather_data, num_days) -> FlexMessage:
    """
    將解析後的天氣字典轉成 FlexMessage Carousel。
    Args:
        parsed_weather_data (dict): {
            'location_name': '西屯區',
            'county_name': '臺中市',
            'forecast_periods': [ {...}, {...}, ... ]
        }
        num_days (int): 3 / 5 / 7
    Returns:
        FlexMessage
    """
    if not parsed_weather_data or not parsed_weather_data.get("forecast_periods"):
        logger.warning("沒有提供預報天氣數據或數據不完整供格式化。")
        location = parsed_weather_data.get("location_name", "該地區") if parsed_weather_data else "該地區"
        return FlexMessage(
            alt_text=f"{location} 未來天氣預報",
            contents=FlexBubble(
                body=FlexBox(type="box", layout="vertical", contents=[
                    FlexText(text=f"⚠️ 抱歉，暫時無法取得 {location} 的預報資料。", wrap=True)
                ])
            )
        )
    
    # ✅ 正確流程：轉換為 bubble list 並組成 Carousel
    bubble_list = convert_forecast_to_bubbles(parsed_weather_data, num_days)
    alt_txt = f"{parsed_weather_data['county_name']} 未來 {num_days} 天氣預報"
    # carousel = FlexCarousel(contents=build_observe_weather_flex)
    flex_msg = build_flex_carousel(bubble_list, alt_text=alt_txt)
    logger.info("預報 FlexMessage 已建立，共 %d 張 bubble。", len(bubble_list))
    return flex_msg
    
    """
    return FlexMessage(alt_text=f"{location} 未來天氣預報", contents=FlexBubble(
            body=FlexBox(type="box", layout="vertical", contents=[
                FlexText(text=f"⚠️ 抱歉，暫時無法取得 {location} 的預報資料。", wrap=True)
            ])
        ))
    """
    
    county_name = parsed_weather_data.get('county_name', '未知縣市')
    # township_name = parsed_weather_data.get('location_name', '未知鄉鎮')
    forecast_periods: List[dict] = parsed_weather_data['forecast_periods']

    message_parts = [f"📍 **{county_name} 未來 {num_days} 天天氣預報**\n"]

    # 計算要顯示的時段數量。F-D0047-091 通常提供 7 天預報，可能每 6 小時或每 12 小時一個時段。
    # 這裡我們根據請求的天數來篩選數據，每天可能有多個時段。
    
    # 用來追蹤已經顯示了多少個獨立的「天」
    build_observe_weather_flex: List[FlexCarousel] = []
    displayed_days_count = 0
    last_displayed_date = None

    for period_info in forecast_periods:
        current_period_date = period_info.get('forecast_date')

        # 如果日期發生變化，並且尚未達到請求的天數
        if current_period_date and current_period_date != last_displayed_date:
            if displayed_days_count >= num_days:
                break
            displayed_days_count += 1
            message_parts.append(f"\n🗓️ **{current_period_date}**")
            last_displayed_date = current_period_date

        if displayed_days_count > num_days: # 額外防護，雖然上面已經有判斷
            break

        # 獲取安全的值，如果不存在則使用 'N/A'
        obs_time   = period_info.get("obs_time", "N/A")
        weather_desc = period_info.get('weather_desc', 'N/A')
        max_temp = period_info.get('max_temp', 'N/A')
        max_feel = period_info.get('max_feel', 'N/A')
        min_temp = period_info.get('min_temp', 'N/A')
        min_feel = period_info.get('min_feel', 'N/A')
        humidity = period_info.get('humidity', 'N/A')
        pop = period_info.get('pop', 'N/A')
        wind_speed = period_info.get('wind_speed', 'N/A')
        wind_dir = period_info.get('wind_dir', 'N/A')
        comfort_max = period_info.get('comfort_max', 'N/A')
        comfort_min = period_info.get('comfort_min', 'N/A')
        uv_index = period_info.get('uv_index', 'N/A')

        # 組合溫度訊息
        temp_info = ""
        if min_temp != 'N/A' and max_temp != 'N/A':
            temp_info = f"{min_temp}°C ~ {max_temp}°C"
        elif period_info.get('temp') != 'N/A': # 如果沒有 MinT/MaxT 但有 T (單一溫度)
            temp_info = f"{period_info['temp']}°C"
        else:
            temp_info = "N/A"

        message_parts.append(f"時段: {period_info.get('forecast_period_str', 'N/A')}")
        message_parts.append(f"☁️ 天氣: {weather_desc}")
        message_parts.append(f"🌡️ 氣溫: {temp_info}")
        message_parts.append(f"☔ 降雨機率: {pop}%")

        if comfort_max != 'N/A' and comfort_min != 'N/A':
            message_parts.append(f"🚶 體感: {comfort_min}°C ~ {comfort_max}°C")
        if wind_speed != 'N/A' and wind_dir != 'N/A':
            message_parts.append(f"🌬️ 風向/風速: {wind_dir} {wind_speed} m/s")
        
        message_parts.append("-" * 15) # 分隔線
        
    # 修正：在循環結束後檢查總顯示天數
    final_message = "\n".join(message_parts)
    # 修正最後的備註，確保顯示實際的天數
    final_message += f"\nℹ️ 備註：此預報資料為未來 {displayed_days_count} 天資訊。"
    if displayed_days_count < num_days:
        final_message += f"\n您請求了 {num_days} 天預報，但目前僅能提供 {displayed_days_count} 天數據。"

    logger.info("預報天氣訊息已格式化。")
    # 如果實際張數 < num_days，仍照實回傳

    

# 這裡不包含 send_hello_message, send_unrecognized_message, send_api_error_message
# 因為它們通常被視為通用訊息，可以放到一個共同的檔案，或者在 handlers.py 中處理
# 為了嚴格分開，如果這些訊息只在預報場景下需要，才放這裡。
# 但通常它們是通用的。我會把這些通用的放到 line_common_messaging.py，如果你想這樣的話。
# 這裡先只放 forecast 相關的。

# 如果您想讓 send_api_error_message 顯示 location_name, 可以在這裡定義一個版本
# def send_forecast_api_error_message(line_bot_api_instance, user_id: str, location_name: str = ""):
#     message = f"抱歉，目前無法取得{' ' + location_name if location_name else ''}的天氣預報資訊，請稍後再試。"
#     send_line_message(line_bot_api_instance, user_id, message)
#     logger.warning(f"已發送預報 API 錯誤訊息給用戶 ID: {user_id}")