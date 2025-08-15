# typhoon/area_hazard_parser.py
"""
將「中央氣象署地區影響預警」API (W-C0033-002) 獲取到的原始 JSON 數據，轉換為結構化且易於使用的 Python 列表。
主要職責：
1. 數據清洗與提取：從巢狀的原始 JSON 結構中，精準的提取出預警的標題、時間、受影響區域和詳細描述等關鍵資訊。
2. 格式化處理：將原始的時間字串（如 `YYYY-MM-DD HH:MM:SS`）轉換為更適合閱讀的格式。
3. 過濾無效數據：忽略那些內容不完整或不符合顯示條件的無效預警記錄。
4. 輸出統一格式：將每個預警記錄整理成一個標準化的字典，並以列表的形式返回。
   這個標準化的格式讓建構 Flex Message 的模組可以直接使用，實現「數據處理」與「UI 呈現」的職責分離。

這個模組的設計讓整個系統的數據流變得清晰：API 模組負責獲取原始數據，Parser 模組負責將數據轉換為可用格式，而 Flex Message 模組則專注於如何顯示這些數據。
"""
import logging
from datetime import datetime
from typing import Any, List, Dict, Optional

logger = logging.getLogger(__name__)

# --- 將原始數據解析、清理並格式化為 Flex Message 可直接使用的形式 ---
class AreaHazardParser:
    # --- 從原始地區影響預警數據中提取並整理出用於顯示的關鍵資訊 ---
    def parse_area_hazard_data(self, raw_hazard_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        執行流程：
        1. 執行基本的數據有效性檢查。
        2. 遍歷每一個預警記錄，並從中提取、清洗和格式化所需的資訊。
        3. 執行過濾邏輯，跳過無效的預警記錄。
        4. 將處理好的數據儲存為字典，並添加到列表中。
        5. 返回最終的解析結果列表。
        
        Args:
            raw_hazard_data (Dict[str, Any]): 從 CWA API 獲取的原始 JSON 數據。

        Returns:
            Optional[List[Dict[str, Any]]]: 解析後的預警資訊列表，每個元素是一個字典。
                                            如果沒有有效數據或無符合條件的預警，返回 None。
        """
        if not raw_hazard_data:
            logger.warning("無原始地區影響預警數據可供解析。")
            return None

        parsed_warnings = []

        try:
            # 1. 地區預警數據位於 records.record 列表中
            records = raw_hazard_data.get("records", {}).get("record", [])
            if not records:
                logger.info("原始地區影響預警數據中未找到任何 'record'。")
                return None
            
            # 2. 遍歷每一個預警記錄並處理
            for record in records:
                """
                遍歷 API 返回的每一個預警記錄。
                - 逐一處理：中央氣象署的 API 可能會返回多個預警，將每個預警視為一個獨立的記錄，讓程式可以逐一進行解析和格式化，確保每個預警都能被正確處理。
                - 防禦性程式設計：使用 `.get()` 方法來安全的訪問 JSON 字典中的鍵。
                  即使某些鍵不存在（例如 `datasetInfo`），也不會引發 `KeyError`，而是返回一個預設值（例如 `{}` 或 `[]`），避免程式崩潰。
                """
                dataset_info = record.get("datasetInfo", {})
                contents_data = record.get("contents", {}).get("content", {})
                hazard_conditions = record.get("hazardConditions", {})

                # 獲取原始時間
                issue_time_raw = dataset_info.get("issueTime")
                valid_time = dataset_info.get("validTime", {})
                start_time_raw = valid_time.get("startTime")
                end_time_raw = valid_time.get("endTime")

                # 獲取原始描述
                description = contents_data.get("contentText", "無詳細說明").strip()

                affected_areas_list = []

                # 獲取原始數據
                # CWA 的 W-C0033-002 結構中，hazard 是一個列表
                hazards = hazard_conditions.get("hazards", {}).get("hazard", [])
                if hazards:
                    first_hazard_info = hazards[0].get("info", {})
                    phenomena = first_hazard_info.get("phenomena", "無資料")
                    significance = first_hazard_info.get("significance", "無資料")
                    
                    locations_data = first_hazard_info.get("affectedAreas", {}).get("location", [])
                    affected_areas_list = [loc.get("locationName") for loc in locations_data if loc.get("locationName")]

                # 數據清洗與格式化
                description_formatted = description.strip() # 清理描述字串

                # 格式化時間
                issue_time_formatted = self._format_time(issue_time_raw)
                start_time_formatted = self._format_time(start_time_raw)
                end_time_formatted = self._format_time(end_time_raw)
                
                # 將起訖時間合併為單一字串
                effective_period_formatted = f"{start_time_formatted} ~ {end_time_formatted}"

                # 移除重複的地區並排序，以便顯示
                affected_areas_list = sorted(list(set(affected_areas_list)))
                affected_areas_formatted = ", ".join(affected_areas_list) if affected_areas_list else "無資料"

                # 構建完整的標題字串
                title_formatted = f"【{phenomena}{significance}】" if phenomena != "無資料" else "地區預警"

                # 3. 執行過濾邏輯
                # 如果現象是 "無資料" 且沒有影響地區，則跳過這個預警
                if phenomena == "無資料" and not affected_areas_list:
                    logger.debug(f"跳過無效預警 (無現象且無影響地區): {record.get('id', '未知ID')}")
                    continue # 跳過當前循環，處理下一個 record

                # 4. 將前面提取和格式化的所有資訊組合成字典，並加到列表中
                parsed_warnings.append({
                    "title"                      : title_formatted,
                    "issue_time_formatted"       : issue_time_formatted,
                    "effective_period_formatted" : effective_period_formatted,
                    "affected_areas_formatted"   : affected_areas_formatted,
                    "description_formatted"      : description_formatted
                })

            if not parsed_warnings:
                logger.info("解析後，無任何地區影響預警。")
                return None

            # 5. 返回最終的解析結果列表
            logger.info(f"成功解析 {len(parsed_warnings)} 條地區影響預警數據。")
            return parsed_warnings

        except (KeyError, IndexError) as e:
            logger.error(f"解析地區影響預警數據時，鍵或索引錯誤: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"解析地區影響預警數據時發生未預期的錯誤: {e}", exc_info=True)
            return None

    # --- 輔助函式：將原始 ISO 格式的時間字串轉換為指定格式 ---
    def _format_time(self, iso_time_str: Optional[str]) -> str:
        """
        將時間格式化的邏輯獨立出來，而不是在主函式中重複寫多次。
        這使得主函式的程式碼更清晰，也方便未來修改時間格式時，只需修改這個函式即可。
        """
        if not iso_time_str:
            return "未知日期"
        try:
            # CWA API 的時間格式通常是 'YYYY-MM-DD HH:MM:SS'
            dt_object = datetime.strptime(iso_time_str, '%Y-%m-%d %H:%M:%S')
            return dt_object.strftime("%Y/%m/%d %H:%M") # 轉換為 YYYY/MM/DD HH:MM
        except ValueError:
            logger.warning(f"解析時間字串 '{iso_time_str}' 失敗。", exc_info=True)
            return "未知日期"