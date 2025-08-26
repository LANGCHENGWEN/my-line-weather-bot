# typhoon/typhoon_parser.py
"""
主要職責是「資料轉換」，負責解析中央氣象署提供的原始颱風 JSON 數據。
因為原始數據的結構可能很複雜，且包含許多不必要的資訊，本解析器的目標是：
1. 提取關鍵資訊：只從龐大的 JSON 中篩選出我們需要顯示在 LINE Flex Message 上的數據，例如颱風名稱、位置、風速、預報點等。
2. 格式化數據：將提取出的數據進行格式化，使其更具可讀性，包括：
   - 將英文方位的縮寫（如 "NNE"）轉換為中文（「北北東」）。
   - 將時間戳記轉換為易於閱讀的日期時間格式。
   - 將七級風暴風半徑的詳細資訊整理成易於在 Flex Message 中分行顯示的格式。
3. 錯誤處理：在解析過程中，如果遇到數據缺失或格式不符的情況，能夠處理並記錄錯誤，確保程式不會崩潰，並返回 `None` 或預設值。
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Any, List, Dict, Optional

from .typhoon_constants import DIRECTION_MAP

logger = logging.getLogger(__name__)

# --- 將原始數據解析、清理並格式化為 Flex Message 可直接使用的形式 ---
class TyphoonParser:
    # --- 將英文縮寫的風暴半徑詳細資訊轉換為中文，並分割成多個字串 ---
    def _format_radius_detail_cht(self, detail_str: str) -> list[str]:
        """
        這個轉換是為了讓 Flex Message 能將多個方向的半徑資訊分行顯示，提高可讀性。
        例如，將原始字串 "(NE170公里, SE180公里)" 轉換為列表 ["東北170公里", "東南180公里"]。
        """
        if not detail_str:
            return [] # 返回空列表
        
        # 對 DIRECTION_MAP 的檢查，以防萬一變成 None
        if DIRECTION_MAP is None:
            logger.error("_format_radius_detail_cht 中的 DIRECTION_MAP 為 None。這表示存在導入問題。")
            return [detail_str] # 無法轉換，返回包含原始字串的列表

        # 使用正則表達式分割字串，去除括號和空格
        parts = re.split(r',\s*', detail_str.strip('() '))

        formatted_parts = []

        # 避免 "NNE" 被誤判為以 "N" 開頭，這裡對字典的鍵進行排序
        try:
            sorted_directions = sorted(
                [k for k in DIRECTION_MAP.keys() if k is not None],
                key=len,
                reverse=True # 降序排序，確保長度較長的鍵（如 "NNE"）先被比對
            )
        except TypeError as e:
            logger.error(f"Error sorting DIRECTION_MAP keys: {e}. DIRECTION_MAP: {DIRECTION_MAP}")
            return [detail_str] # 無法轉換，返回包含原始字串的列表
    
        # 遍歷並進行中文替換
        """
        遍歷分割後的每個部分，並嘗試將開頭的英文方向縮寫替換為中文。
        - 確保替換的準確性：透過對 `DIRECTION_MAP` 的鍵按長度進行降序排序，可以確保例如 `NNE`（北北東）這樣的長字串在 `N`（北）之前被匹配，避免將 `NNE` 錯誤的替換成「北E」。
        - 處理多個方向：即使原始數據包含多個方向，這個迴圈也能逐一處理。
        - 處理未匹配的情況：如果沒有匹配到任何方向，則保留原始字串，避免資訊丟失。
        """
        for part in parts:
            if not part:
                continue
            replaced = False
            # 遍歷排序過的方向，並進行中文替換
            for eng_dir in sorted_directions:
                if eng_dir and part.startswith(eng_dir): # 檢查部分字串是否以英文方向開頭
                    remaining_part = part[len(eng_dir):] # 擷取剩餘的半徑數值
                    formatted_parts.append(f"{DIRECTION_MAP[eng_dir]}{remaining_part}")
                    replaced = True
                    break
            if not replaced:  # 如果沒有匹配到任何方向，則保留原樣
                formatted_parts.append(part)

        # 為了讓 Flex Message 更容易處理兩行顯示，確保至少有四個元素，不足則補空字串
        while len(formatted_parts) < 4:
            formatted_parts.append("")
        return formatted_parts

    # --- 解析器的主要入口點，負責從原始 JSON 數據中提取並整理出所有關鍵資訊 ---
    def parse_typhoon_data(self, raw_typhoon_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        呼叫其他內部方法來處理不同的數據區塊（例如現況和預報），最後將所有整理好的數據合併成一個乾淨的字典。
        如果數據格式不符或有任何錯誤，會返回 None。
        """
        if not raw_typhoon_data:
            logger.warning("無原始颱風數據可供解析。")
            return None

        try:
            # 1. 安全的從 JSON 中提取主要颱風數據
            """
            - 避免 `KeyError`：使用 `.get()` 方法並提供一個空字典 `{}` 或空列表 `[]` 作為預設值，可以防止在 JSON 鍵名不存在時程式拋出 `KeyError` 而崩潰。
            - 處理數據缺失：如果整個颱風數據列表為空，程式會記錄警告並返回 `None`，讓上層呼叫者知道沒有可用數據。
            """
            tropical_cyclone_data = raw_typhoon_data \
                                    .get("records", {}) \
                                    .get("tropicalCyclones", {}) \
                                    .get("tropicalCyclone", [])
            if not tropical_cyclone_data:
                logger.warning("未找到任何颱風數據。")
                return None
            
            # 2. 只處理第一個颱風 (通常只有一個活躍颱風，或取最新的)
            typhoon_info = tropical_cyclone_data[0]

            # 3. 呼叫內部方法處理各個區塊
            current_status = self._parse_current_status(typhoon_info) # 提取並格式化現況資訊
            forecasts = self._parse_forecast_data(typhoon_info) # 提取並格式化預報點資訊 (這會返回一個列表)

            # 4. 篩選特定時效的預報點
            """
            從完整的預報列表 (`forecasts`) 中，篩選出特定時效點（24小時、48小時和72小時）。
            - 簡化上層邏輯：將篩選邏輯放在這裡，可以讓上層的 `typhoon_flex_message.py` 不再需要自己遍歷列表來尋找特定數據點，使程式碼更簡潔。
            - 提高效率：使用生成器表達式 `(f for f in forecasts if ...)` 比傳統的迴圈更有效率，因為它只在需要時才遍歷數據。
            """
            forecast_24hr = next((f for f in forecasts if f.get('tau') == 24), None)
            forecast_48hr = next((f for f in forecasts if f.get('tau') == 48), None)
            forecast_72hr = next((f for f in forecasts if f.get('tau') == 72), None)

            # 5. 合併所有數據並返回
            return {
                "currentStatus" : current_status,
                "forecasts"     : forecasts,
                "forecast_24hr" : forecast_24hr,
                "forecast_48hr" : forecast_48hr,
                "forecast_72hr" : forecast_72hr
            }

        except Exception as e:
            logger.error(f"解析颱風數據時發生錯誤: {e}", exc_info=True)
            return None

    # --- 解析颱風現況數據並格式化 ---
    def _parse_current_status(self, typhoon_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        從原始 JSON 中提取中心位置、風速、氣壓、移動方向等資訊，並進行必要的格式轉換，例如時間格式化和方位中文化，最後將結果儲存在一個字典中。
        """
        # 從 JSON 資料中提取 year 和 typhoonName
        year = typhoon_info.get("year")
        typhoon_eng_name = typhoon_info.get("typhoonName")

        # 組合年份和英文名，創建一個唯一的颱風 ID，用於在推播時檢查這個颱風 ID 是否發送推播過
        typhoon_id = f"{year}_{typhoon_eng_name}" if year and typhoon_eng_name else "無資料"

        # 1. 初始化一個包含預設值的字典
        # 提供預設值可以防止在原始數據缺失時，程式因找不到鍵而崩潰，同時保證返回的字典結構是穩定的
        current_status = {
            "typhoon_id"      : typhoon_id,
            "typhoonName"     : typhoon_info.get("cwaTyphoonName", "無資料"), # 中文颱風名
            "typhoonEngName"  : typhoon_info.get("typhoonName", "無資料"), # 英文颱風名
            "tdNo"            : typhoon_info.get("cwaTdNo", "無資料"), # 國際編號
            "dataTime"        : "未知日期", # 觀測時間
            "longitude"       : "無資料",
            "latitude"        : "無資料",
            "maxWindSpeed"    : "無資料",
            "maxGustSpeed"    : "無資料",
            "pressure"        : "無資料",
            "movingSpeed"     : "無資料",
            "movingDirection" : "無資料",
            "radiusOf7knots"  : "無資料",
            "radiusOf7knotsDetailFormatted" : ["", "", "", ""] # 預先初始化為列表，確保有四個空字串
        }

        # 2. 獲取並處理最新的實測數據 (在 analysisData.fix 裡面)
        analysis_data = typhoon_info.get("analysisData", {})
        fix_data_list = analysis_data.get("fix", [])

        # 確保有 fix 資料
        if fix_data_list: 
            latest_fix = fix_data_list[-1] # 取最後一個作為最新實測

            # 處理觀測時間
            raw_fix_time = latest_fix.get("fixTime")
            if raw_fix_time:
                try:
                    dt_object = datetime.fromisoformat(raw_fix_time)
                    # 將時間格式化為 "YYYY年MM月DD日 HH:MM"
                    current_status["dataTime"] = dt_object.strftime("%Y年%m月%d日 %H:%M")
                except ValueError:
                    logger.warning(f"解析 fixTime '{raw_fix_time}' 失敗。", exc_info=True)
                    current_status["dataTime"] = "未知日期"

            # 處理座標
            coordinate_str = latest_fix.get("coordinate")
            if coordinate_str and isinstance(coordinate_str, str):
                coords = coordinate_str.split(',')
                if len(coords) == 2:
                    current_status["longitude"] = coords[0].strip() # 經度在第一個
                    current_status["latitude"] = coords[1].strip() # 緯度在第二個
                else:
                    logger.warning(f"現況座標字串格式不符預期: {coordinate_str}")
            
            # 處理風速和氣壓
            current_status["maxWindSpeed"] = latest_fix.get("maxWindSpeed", "無資料")
            current_status["maxGustSpeed"] = latest_fix.get("maxGustSpeed", "無資料")
            current_status["pressure"] = latest_fix.get("pressure", "無資料")

            # 處理移動速度和方向
            current_status["movingSpeed"] = latest_fix.get("movingSpeed", "無資料")
            raw_moving_direction = latest_fix.get("movingDirection")
            if raw_moving_direction and raw_moving_direction in DIRECTION_MAP: # 轉換移動方向為中文
                current_status["movingDirection"] = DIRECTION_MAP[raw_moving_direction]
            else:
                current_status["movingDirection"] = raw_moving_direction if raw_moving_direction else "無資料"
            
            # 處理七級風暴風半徑
            radius_7knots_data = latest_fix.get("circleOf15Ms", {})
            current_status["radiusOf7knots"] = radius_7knots_data.get("radius", "無資料")
            
            # 處理暴風半徑詳細方向 (例如：東北100公里, 西南80公里)
            """
            從複雜的 JSON 結構中提取詳細的暴風半徑資訊，並格式化。
            - 處理複雜結構：原始 JSON 的詳細半徑資訊可能嵌套在多層字典和列表中，需要層層深入才能取到正確的數據。
            - 呼叫輔助函式：將提取到的原始字串傳遞給 `_format_radius_detail_cht` 輔助函式，專注於數據的提取，而將格式化的工作交給專門的函式來處理。
            """
            quadrant_radii_7knots = radius_7knots_data.get("quadrantRadii", {}).get("radius")
            
            detail_str_for_formatting = ""
            if isinstance(quadrant_radii_7knots, list):
                dir_info = []
                for r_dir in quadrant_radii_7knots:
                    if isinstance(r_dir, dict):
                        direction = r_dir.get('dir')
                        value = r_dir.get('value')
                        if direction and value is not None: # 確保有值
                            dir_info.append(f"{direction}{value}公里")
                detail_str_for_formatting = f"({', '.join(dir_info)})" if dir_info else ""

            # 呼叫格式化函式，將結果儲存到 radiusOf7knotsDetailFormatted
            current_status["radiusOf7knotsDetailFormatted"] = self._format_radius_detail_cht(detail_str_for_formatting)

        else:
            logger.warning("未找到任何颱風實測 (fix) 數據，現況資訊將為無資料。")
            current_status["radiusOf7knotsDetailFormatted"] = ["", "", "", ""]
        
        return current_status

    # --- 解析颱風預報點數據 ---
    def _parse_forecast_data(self, typhoon_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        遍歷所有預報點，提取每個點的關鍵資訊，並進行時間計算和格式化，最終返回一個包含所有預報點的列表。
        """
        forecast_data_list = typhoon_info.get("forecastData", {}).get("fix", [])
        parsed_forecasts = []

        # 遍歷所有預報點
        for forecast_point in forecast_data_list:
            tau_hours = forecast_point.get("tau")

            # 確保預報時效（tau）有效
            if not tau_hours or not tau_hours.isdigit() or int(tau_hours) == 0:
                logger.debug(f"跳過無效或為0的預報時效 (tau): {tau_hours}")
                continue

            tau_hours_int = int(tau_hours)
            
            # 處理預報時間的計算和格式化
            """
            - 精確的時間計算：原始數據只提供發布時間 (`initTime`) 和預報時效 (`tau`)，需要手動將兩者相加才能得到精確的預報時間點。
              這裡使用 `datetime` 和 `timedelta` 進行嚴謹的日期時間運算。
              CWA 的 dataTime 是 UTC+8，tau 是小時數。
            - 錯誤防護：使用 `try...except` 區塊來處理時間格式不正確時可能拋出的 `ValueError`，避免程式崩潰。
            """
            raw_init_time = forecast_point.get("initTime")
            forecast_time_formatted = "無資料"

            if raw_init_time:
                try:
                    init_dt_object = datetime.fromisoformat(raw_init_time)
                    # 計算預報時間 (initTime + tau 小時)
                    calculated_forecast_time = init_dt_object + timedelta(hours=tau_hours_int)
                    # 格式化為 MM/DD HH:MM
                    forecast_time_formatted = calculated_forecast_time.strftime("%m/%d %H:%M")
                except ValueError:
                    logger.warning(f"解析 initTime '{raw_init_time}' 或計算預報時間失敗。", exc_info=True)

            # 處理經緯度格式
            coordinate_str_forecast = forecast_point.get("coordinate")
            longitude_forecast = "無資料"
            latitude_forecast = "無資料"
            
            if coordinate_str_forecast and isinstance(coordinate_str_forecast, str):
                coords_forecast = coordinate_str_forecast.split(',')
                if len(coords_forecast) == 2:
                    longitude_forecast = coords_forecast[0].strip() # 經度在第一個
                    latitude_forecast = coords_forecast[1].strip() # 緯度在第二個
                else:
                    logger.warning(f"預報點座標格式不符預期: {coordinate_str_forecast}")

            # 提取預報點的風速、氣壓
            max_wind_speed_forecast = forecast_point.get("maxWindSpeed", "無資料")
            max_gust_speed_forecast = forecast_point.get("maxGustSpeed", "無資料")
            pressure_forecast = forecast_point.get("pressure", "無資料")

            # 提取預報點的七級風暴風半徑
            radius_7knots_forecast = forecast_point.get("circleOf15Ms", {}).get("radius", "無資料")

            # 提取預報點的 70% 機率半徑
            radius_70_percent_prob_forecast = forecast_point.get("radiusOf70PercentProbability", "無資料")

            # 將所有整理好的數據加入列表
            parsed_forecasts.append({
                "tau": tau_hours_int,
                "forecastTime"   : forecast_time_formatted,
                "longitude"      : longitude_forecast,
                "latitude"       : latitude_forecast,
                "maxWindSpeed"   : max_wind_speed_forecast,
                "maxGustSpeed"   : max_gust_speed_forecast,
                "pressure"       : pressure_forecast,
                "radiusOf7knots" : radius_7knots_forecast,
                "radiusOf70PercentProbability" : radius_70_percent_prob_forecast
            })
            
        # 確保預報點按時效（tau）從小到大排序
        parsed_forecasts.sort(key=lambda x: x["tau"])

        return parsed_forecasts