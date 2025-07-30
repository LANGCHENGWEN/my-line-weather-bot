# typhoon/area_hazard_parser.py
# 這個檔案負責接收 area_hazard_api.py 獲取到的原始 JSON 數據，並將其解析、整理成更容易在 Flex Message 中使用的格式
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class AreaHazardParser:
    """
    解析中央氣象署地區影響預警 API (W-C0033-002) 的原始 JSON 數據。
    負責將原始數據解析、清理並格式化為 Flex Message 可直接使用的形式。
    """
    def parse_area_hazard_data(self, raw_hazard_data: Dict[str, Any], target_city: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        從原始地區影響預警數據中提取並整理出用於顯示的關鍵資訊。
        
        Args:
            raw_hazard_data (Dict[str, Any]): 從 CWA API 獲取的原始 JSON 數據。
            target_city (Optional[str]): 可選參數，用於篩選特定城市的預警。
                                         例如 "臺北市", "高雄市"。

        Returns:
            Optional[List[Dict[str, Any]]]: 解析後的預警資訊列表，每個元素是一個字典。
                                             如果沒有有效數據或無符合條件的預警，返回 None。
        """
        if not raw_hazard_data:
            logger.warning("無原始地區影響預警數據可供解析。")
            return None

        parsed_warnings = []

        try:
            # 地區預警數據位於 records.record 列表中
            records = raw_hazard_data.get("records", {}).get("record", [])

            if not records:
                logger.info("原始地區影響預警數據中未找到任何 'record'。")
                return None

            for record in records:
                dataset_info = record.get("datasetInfo", {})
                contents_data = record.get("contents", {}).get("content", {})
                hazard_conditions = record.get("hazardConditions", {})

                # 1. 提取原始數據並設定預設值
                issue_time_raw = dataset_info.get("issueTime")
                valid_time = dataset_info.get("validTime", {})
                start_time_raw = valid_time.get("startTime")
                end_time_raw = valid_time.get("endTime")

                # 先獲取原始描述
                description = contents_data.get("contentText", "無詳細說明").strip()

                # 從 hazardConditions 獲取現象、意義和受影響區域
                phenomena = "N/A"
                significance = "N/A"
                affected_areas_list = []

                # CWA 的 W-C0033-002 結構中，hazard 是一個列表
                hazards = hazard_conditions.get("hazards", {}).get("hazard", [])
                if hazards:
                    # 假設我們主要關心第一個 hazard 資訊 (通常只有一個)
                    first_hazard_info = hazards[0].get("info", {})
                    phenomena = first_hazard_info.get("phenomena", "N/A")
                    significance = first_hazard_info.get("significance", "N/A")
                    
                    locations_data = first_hazard_info.get("affectedAreas", {}).get("location", [])
                    # 提取 locationName
                    affected_areas_list = [loc.get("locationName") for loc in locations_data if loc.get("locationName")]

                # 2. 數據清洗與格式化
                # 清理描述字串
                description_formatted = description.strip()
                # 如果需要限制描述長度，在這裡處理：
                # if len(description_formatted) > 150:
                #     description_formatted = description_formatted[:150] + "..."

                # 格式化時間
                issue_time_formatted = self._format_time(issue_time_raw)
                start_time_formatted = self._format_time(start_time_raw)
                end_time_formatted = self._format_time(end_time_raw)
                
                # 將起訖時間合併為單一字串
                effective_period_formatted = f"{start_time_formatted} ~ {end_time_formatted}"

                # 移除重複的地區並排序，以便顯示
                affected_areas_list = sorted(list(set(affected_areas_list)))
                affected_areas_formatted = ", ".join(affected_areas_list) if affected_areas_list else "無"

                # 構建完整的標題字串
                # 這裡使用 _raw 值，因為這是原始 API 提供的，並用於拼接。如果想用 N/A 替換，前面就處理好了。
                title_formatted = f"【{phenomena}{significance}】" if phenomena != "N/A" else "地區預警"

                """
                # 格式化時間為 "YYYY-MM-DD HH:MM:SS" (原始格式) 到 "YYYY-MM-DD HH:MM"
                time_format_in = '%Y-%m-%d %H:%M:%S'
                time_format_out = '%Y-%m-%d %H:%M'
                
                issue_time_formatted = "N/A"
                start_time_formatted = "N/A"
                end_time_formatted = "N/A"

                if issue_time_raw:
                    try:
                        dt_obj = datetime.strptime(issue_time_raw, time_format_in)
                        issue_time_formatted = dt_obj.strftime(time_format_out)
                    except ValueError:
                        logger.warning(f"解析地區預警發布時間 '{issue_time_raw}' 失敗。")

                if start_time_raw:
                    try:
                        dt_obj = datetime.strptime(start_time_raw, time_format_in)
                        start_time_formatted = dt_obj.strftime(time_format_out)
                    except ValueError:
                        logger.warning(f"解析地區預警開始時間 '{start_time_raw}' 失敗。")
                
                if end_time_raw:
                    try:
                        dt_obj = datetime.strptime(end_time_raw, time_format_in)
                        end_time_formatted = dt_obj.strftime(time_format_out)
                    except ValueError:
                        logger.warning(f"解析地區預警結束時間 '{end_time_raw}' 失敗。")
                """

                # 3. 執行過濾邏輯
                # 如果現象是 "N/A" 且沒有影響地區，則跳過這個預警
                if phenomena == "N/A" and not affected_areas_list:
                    logger.debug(f"跳過無效預警 (無現象且無影響地區): {record.get('id', '未知ID')}")
                    continue # 跳過當前循環，處理下一個 record
                
                # 根據 target_city 進行篩選
                if target_city:
                    # 檢查目標城市是否在受影響地區列表中
                    target_found = False
                    for area in affected_areas_list:
                        if target_city.lower() in area.lower():
                            target_found = True
                            break

                    if not target_found:
                        logger.debug(f"跳過不影響 '{target_city}' 的預警: {phenomena} - {affected_areas_list}")
                        continue # 跳過不符合篩選條件的預警

                # 4. 將處理好的數據加入列表
                parsed_warnings.append({
                    "title": title_formatted,
                    "issue_time_formatted": issue_time_formatted,
                    "effective_period_formatted": effective_period_formatted,
                    "affected_areas_formatted": affected_areas_formatted,
                    "description_formatted": description_formatted
                })

                """
                # 構建單個預警的字典
                warning_data = {
                    "phenomena": phenomena,
                    "significance": significance,
                    "description": description,
                    "affected_areas": affected_areas_list,
                    "issue_time": issue_time_formatted, # 新增 issue_time
                    "start_time": start_time_formatted,
                    "end_time": end_time_formatted
                }
                """

            if not parsed_warnings:
                logger.info(f"解析後，無符合 '{target_city if target_city else '所有'}' 條件的地區影響預警。")
                return None

            logger.info(f"成功解析 {len(parsed_warnings)} 條地區影響預警數據。")
            return parsed_warnings

        except (KeyError, IndexError) as e:
            logger.error(f"解析地區影響預警數據時，鍵或索引錯誤: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"解析地區影響預警數據時發生未預期的錯誤: {e}", exc_info=True)
            return None

    def _format_time(self, iso_time_str: Optional[str]) -> str:
        """
        將原始 ISO 格式的時間字串 (e.g., "YYYY-MM-DD HH:MM:SS") 轉換為指定格式。
        """
        if not iso_time_str:
            return "N/A"
        try:
            # 注意：CWA API 的時間格式通常是 'YYYY-MM-DD HH:MM:SS'
            dt_object = datetime.strptime(iso_time_str, '%Y-%m-%d %H:%M:%S')
            return dt_object.strftime("%Y/%m/%d %H:%M") # 轉換為 YYYY/MM/DD HH:MM
        except ValueError:
            logger.warning(f"解析時間字串 '{iso_time_str}' 失敗。", exc_info=True)
            return "N/A"