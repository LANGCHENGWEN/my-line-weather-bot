# solar_terms/solar_terms_calculator.py
"""
計算和查詢農曆二十四節氣的相關資訊。
整合 `lunarcalendar` 函式庫，並提供多個函式，讓其他模組能方便使用。
主要職責：
1. `format_date_with_weekday`：將日期物件格式化為帶有星期幾的字串。
2. `get_solar_terms_for_year`：獲取指定年份的所有節氣及精確日期。
3. `get_today_solar_term_info`：檢查今天（或指定日期）是否為某個節氣的開始日，並返回詳細資訊。
4. `get_current_solar_term_info_for_display`：查詢並返回當前日期時間所在的節氣資訊，用於用戶手動查詢。
"""
import logging
import lunarcalendar # 直接將一個年份傳入節氣物件中，會自動計算出該年份對應的節氣日期，避免手動複雜的農曆計算
from datetime import date, datetime
from .solar_terms_data import SOLAR_TERMS_INFO

logger = logging.getLogger(__name__)

# --- 將日期轉換成包含星期幾的格式 ---
def format_date_with_weekday(d: date) -> str:
    """
    Args:
        d (date): 要格式化的日期物件。
     
    Returns:
        str: 格式化後的日期字串，例如 "2025年08月14日 (四)"。
    """
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    weekday_index = d.weekday() # 0 = 星期一, 6 = 星期日
    weekday_str = weekdays[weekday_index]
    return f"{d.year}年{d.month:02d}月{d.day:02d}日 ({weekday_str})"

# --- 使用 lunarcalendar 獲取指定年份的所有 24 個節氣 ---
def get_solar_terms_for_year(year: int) -> list[dict]:
    """
    遍歷 `lunarcalendar` 內建的節氣列表，並為每一年份計算出每個節氣的精確日期，最後返回一個包含這些節氣資訊的列表。
    
    Args:
        year (int): 要查詢的年份。
        
    Returns:
        list[dict]: 一個包含字典的列表，每個字典包含節氣名稱和發生的精確時間。
    """
    solar_terms = []

    # 遍歷 `lunarcalendar.zh_solarterms` 列表來獲取名稱和日期
    # 這個列表包含了 `lunarcalendar` 函式庫中預定義的所有 24 個節氣物件
    for term_object in lunarcalendar.zh_solarterms:
        # 在 try 區塊之前初始化 term_name，避免 UnboundLocalError (試圖在函式內部使用一個區域變數，但這個變數還沒有被賦予一個值，就會出現這樣的錯誤)
        term_name = "Unknown"
        
        # `try...except` 區塊確保即使在獲取個別節氣資訊時出錯，整個函式也不會崩潰，而是會記錄錯誤並跳過該節氣，提高函式的健壯性
        try:
            # 獲取節氣名稱
            term_name = term_object.get_lang('zh_hans')

            # 獲取節氣的精確日期
            term_date = term_object(year)

            # 為一個特定的節氣建立包含名稱和日期的字典，並將這個字典加到 solar_terms 列表
            solar_terms.append({
                "name": term_name,
                "date": term_date
            })

        except Exception as e:
            logger.error(f"無法取得 {year} 年 {term_name} 節氣資訊: {e}")

    # 根據日期對節氣列表進行排序
    solar_terms.sort(key=lambda x: x['date'])

    return solar_terms

# --- 檢查指定日期（或今天）是否是某個節氣的開始日 ---
def get_today_solar_term_info(check_date: date = None) -> dict | None:
    """
    用於定時推播的函式，只檢查日期是否匹配，不判斷當前處於哪個節氣。
    
    Args:
        check_date (date): 要檢查的日期；如果為 None，則使用當前的日期。
        
    Returns:
        dict | None: 如果指定日期是節氣的開始日，則返回該節氣的資訊字典；否則返回 None。
    """
    if check_date is None: # 如果日期為 None，使用當前的日期
        check_date = datetime.now().date()
    
    logger.debug(f"正在檢查日期 {check_date} 是否為節氣開始日。")

    # 獲取當前年份和下一年的所有節氣列表，並將它們合併和排序
    """
    - 處理跨年節氣：節氣的日期通常在每年的固定時間範圍內，但由於年份的差異，有些節氣（如大寒）可能在當年的年底或下年初發生。
      獲取下一年的節氣可以確保在年底檢查時，不會錯過屬於當年的、但精確日期在隔年的節氣。
    - 篩選匹配日期：迴圈會遍歷所有相關節氣，精確比對 `term["date"]` 是否等於 `check_date`。
      一旦找到匹配項，就將其加入 `all_relevant_solar_terms` 列表。
    """
    solar_terms_this_year = get_solar_terms_for_year(check_date.year)
    solar_terms_next_year = get_solar_terms_for_year(check_date.year + 1)
    
    # 檢查與今天日期匹配的節氣
    all_relevant_solar_terms = []
    for term in solar_terms_this_year + solar_terms_next_year:
        if term["date"] == check_date: # 精確比對 `term["date"]` 是否等於 `check_date`
            all_relevant_solar_terms.append(term)
            
    # 根據日期對節氣列表進行排序
    if all_relevant_solar_terms:
        all_relevant_solar_terms.sort(key=lambda x: x["date"])

        # 從 `solar_terms_data.py` 中獲取的節氣詳細資訊，合併到從 `lunarcalendar` 函式庫計算出的日期資訊中
        """
        - 數據整合：`lunarcalendar` 庫主要提供節氣的名稱和日期，但需要更多額外的資訊（例如節氣習俗、養生建議等）。
          透過這個步驟，將兩種數據來源的資訊合併到一個字典中，形成一個完整的節氣資訊物件。
        - 數據準備：呼叫 `format_date_with_weekday` 函式來為日期添加星期幾的資訊，方便在 Flex Message 中直接使用，而不需要在調用處再次進行格式化。
        """
        current_term_name = all_relevant_solar_terms[0]['name'] # 取得最接近的節氣名稱
        term_details = SOLAR_TERMS_INFO.get(current_term_name, {}) # 尋找詳細的節氣資訊
        
        # 合併資訊
        final_term_info = all_relevant_solar_terms[0].copy()
        final_term_info.update(term_details)

        final_term_info['formatted_date'] = format_date_with_weekday(final_term_info['date'])

        logger.info(f"日期 {check_date} 是節氣 【{final_term_info['name']}】 的開始日，精確時間：{final_term_info['date']}.")
        return final_term_info
    
    logger.debug(f"日期 {check_date} 不是任何節氣的開始日。")
    return None

# --- 獲取當前日期時間所在的節氣資訊 (用於用戶手動查詢) ---
def get_current_solar_term_info_for_display(target_dt: datetime = None) -> dict | None:
    """
    判斷一個日期位於哪兩個節氣之間，並返回前面那個節氣的資訊。
     
    Args:
        target_dt (datetime): 要查詢的日期；如果為 None，則使用當前的日期。
     
    Returns:
        dict | None: 包含當前節氣所有資訊的字典；如果找不到則返回 None。
    """
    if target_dt is None: # 如果日期為 None，使用當前的日期
        target_dt = datetime.now()

    # 獲取去年、今年、明年的節氣列表，並將它們合併和排序
    """
    - 確保時間區間完整：為了判斷一個給定的日期位於哪個節氣期間，需要一個連續且完整的節氣時間點序列。
      只獲取當年份的節氣是不夠的，因為如果用戶在年初或年底查詢，可能需要用到去年或明年的節氣資訊來進行判斷。
    - 判斷邏輯：程式碼會遍歷這個排序好的節氣列表，找到第一個日期比 `target_dt` 晚的節氣，上一個節氣就是要找的「當前節氣」。
    """
    all_solar_terms_extended = []
    for year_offset in [-1, 0, 1]: # 獲取去年、今年、明年的節氣列表
        all_solar_terms_extended.extend(get_solar_terms_for_year(target_dt.year + year_offset))
    
    # 根據日期對節氣列表進行排序
    all_solar_terms_extended.sort(key=lambda x: x["date"])

    # 找出離目標日期（target_dt）最近的，且日期在目標日期或之前的一個節氣
    current_solar_term = None
    for term in all_solar_terms_extended:
        if term["date"] <= target_dt.date():
            current_solar_term = term
        else:
            break # 找到第一個日期比目標日期晚的節氣時，即可停止
        
    # 從 `solar_terms_data.py` 中獲取的節氣詳細資訊，合併到從 `lunarcalendar` 函式庫計算出的日期資訊中
    if current_solar_term:
        """
        這段程式碼與 `get_today_solar_term_info` 中的邏輯類似。
        - 數據一致性：確保無論是推播還是手動查詢，返回給上層的數據結構都是一致且完整的。
        - 數據豐富：將名稱、日期、習俗、養生等所有相關資訊整合到一個字典中，方便上層的 Flex Message 構建函式使用，提高程式碼的整潔度。
        """
        term_details = SOLAR_TERMS_INFO.get(current_solar_term['name'], {})
        current_solar_term.update(term_details)

        # 呼叫 `format_date_with_weekday` 函式來為日期添加星期幾的資訊，並儲存到字典中，供 Flex Message 使用
        current_solar_term['formatted_date'] = format_date_with_weekday(current_solar_term['date'])

        logger.info(f"用戶手動查詢：當前節氣為 {current_solar_term['name']} (發生於 {current_solar_term['date']})")
    else:
        logger.warning(f"用戶手動查詢：未能找到 {target_dt} 的當前節氣。")
    
    return current_solar_term