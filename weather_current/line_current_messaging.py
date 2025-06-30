# line_current_messaging.py
# 專門處理即時天氣訊息的格式化 (O-A0003-001 有人氣象站資料)
import logging
from datetime import datetime, timedelta, timezone
from config import setup_logging

# 導入 Flex Message 模板
from .weather_flex_message import build_weather_flex

# from linebot.v3.messaging.models import TextMessage, FlexMessage, FlexContainer
# from line_common_messaging import send_line_reply_message, send_api_error_message

logger = setup_logging(__name__)

# 台灣時區設定
TAIPEI_TZ = timezone(timedelta(hours=8))

# --- 格式化即時觀測天氣訊息 ---
def format_current_weather_message(formatted_weather_data: dict, location_name: str) -> dict | None:
    """
    格式化即時天氣觀測資訊為 LINE Flex Message 字典。
    接收一個已完全格式化好的字典，直接填充模板。
    
    Args:
        formatted_weather_data (dict): 已經完全解析並格式化好的天氣數據字典
                                       (由 weather_current_parser.py 提供)。
        location_name (str): 用戶查詢的地點名稱，用於 Flex Message 的標題。
        
    Returns:
        dict: 填充好數據的 LINE Flex Message 字典。如果輸入數據無效，返回 None。
    """
    if not formatted_weather_data:
        logger.warning("沒有提供即時天氣數據供格式化，返回 None。")
        return None # 返回 None 讓上層 (handler) 處理錯誤回覆
    
    # 複製一份原始 Flex Message 模板，避免修改原始模板
    flex_message = build_weather_flex().copy()

    try:
        # 填充 Flex Message 模板
        # 這裡的鍵名必須與 weather_current_parser.py 中返回的字典鍵名完全一致。
        flex_message["body"]["contents"][0]["text"] = f"📍 {location_name} 即時天氣"

        # 定位到包含所有天氣數據的 Box (在您模板中的 body.contents[2])
        # 這個 Box 的 contents 列表現在包含了所有天氣數據行
        data_contents = flex_message["body"]["contents"][2]["contents"]

        # 觀測時間 (索引 0)
        data_contents[0]["contents"][1]["text"] = formatted_weather_data.get('observation_time', 'N/A')
        # 天氣描述 (索引 1)
        data_contents[1]["contents"][1]["text"] = formatted_weather_data.get('weather_description', 'N/A')

        # 溫度行 (現在是索引 2)
        # 由於 weather_current_parser.py 已經把體感溫度合併到 temp_display，這裡直接填充即可
        # data_contents[2]["contents"][1]["text"] = formatted_weather_data.get('temp_display', 'N/A')
        
        # --- 溫度行 (索引 2) ---
        # 溫度行本身是一個 Box，其 contents 裡面有兩個小 Box (一個用於主溫度，一個用於體感溫度)
        temp_main_box = data_contents[2]["contents"][0] # 主溫度 Box
        temp_sensation_box = data_contents[2]["contents"][1] # 體感溫度 Box

        temp_main_box["contents"][1]["text"] = formatted_weather_data.get('current_temp', 'N/A').split('(')[0].strip() # 假設 temp_display 是 "28°C (體感: 29°C)"，取前面部分
        
        sensation_temp_text = formatted_weather_data.get('sensation_temp_display', 'N/A')
        temp_sensation_box["contents"][1]["text"] = f"{sensation_temp_text})"

        # 濕度 (索引 3)
        data_contents[3]["contents"][1]["text"] = formatted_weather_data.get('humidity', 'N/A')
        # 降雨量 (索引 4)
        data_contents[4]["contents"][1]["text"] = formatted_weather_data.get('precipitation', 'N/A')

        # 風速風向行 (現在是索引 5)
        # 由於 weather_current_parser.py 已經把風向合併到 wind_display，這裡直接填充即可
        # data_contents[5]["contents"][1]["text"] = formatted_weather_data.get('wind_display', 'N/A')

        # --- 風速/風向行 (索引 5) ---
        # 風速/風向行本身是一個 Box，其 contents 裡面有兩個小 Box (一個用於風速，一個用於風向)
        wind_speed_box = data_contents[5]["contents"][0] # 風速 Box
        wind_direction_box = data_contents[5]["contents"][1] # 風向 Box

        # 從 formatted_weather_data 中獲取 'wind_display'
        wind_display_data = formatted_weather_data.get('wind_display', 'N/A (風向: N/A)')
        
        # 拆分 wind_display 數據為風速和風向
        wind_speed_value = "N/A"
        wind_direction_value = "N/A"

        if " (" in wind_display_data and wind_display_data != "無風":
            # 如果格式是 "X.X m/s (風向: 方向)"
            parts = wind_display_data.split(' (')
            wind_speed_value = parts[0].strip()
            if len(parts) > 1:
                wind_direction_value = parts[1].replace('風向:', '').replace(')', '').strip()
        elif wind_display_data == "無風":
            # 處理 "無風" 的情況
            wind_speed_value = "無"
            wind_direction_value = "無"
        else:
            # 作為備用，如果格式不符合預期
            wind_speed_value = wind_display_data.strip()
            wind_direction_value = "N/A"
        
        wind_speed_box["contents"][1]["text"] = wind_speed_value
        wind_direction_box["contents"][1]["text"] = f"{wind_direction_value})" # 填充風向，並補上 ')'

        # 氣壓 (索引 6)
        data_contents[6]["contents"][1]["text"] = formatted_weather_data.get('pressure', 'N/A')
        # 紫外線指數 (索引 7)
        data_contents[7]["contents"][1]["text"] = formatted_weather_data.get('uv_index', 'N/A')

        logger.info("即時天氣 Flex Message 已格式化。") # #007BFF # #1E90FF # #4169E1 # #8A2BE2
        return flex_message
    except KeyError as e:
        logger.error(f"填充 Flex Message 模板時缺少鍵: {e}。請檢查 weather_current_parser.py 的輸出。", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"格式化即時天氣 Flex Message 時發生未知錯誤: {e}", exc_info=True)
        return None

# 如果您想讓 send_api_error_message 顯示 location_name, 可以在這裡定義一個版本
# def send_current_api_error_message(line_bot_api_instance, user_id: str, location_name: str = ""):
#     message = f"抱歉，目前無法取得{' ' + location_name if location_name else ''}的即時天氣資訊，請稍後再試。"
#     send_line_message(line_bot_api_instance, user_id, message)
#     logger.warning(f"已發送即時 API 錯誤訊息給用戶 ID: {user_id}")