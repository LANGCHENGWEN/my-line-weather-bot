# solar_terms/solar_terms_calculator.py
import logging
from datetime import datetime, date, timedelta
import lunarcalendar
# from LunarCalendar import Converter # 導入 LunarCalendar 的 Converter
# from LunarCalendar.solarterm import SolarTerm # 導入 SolarTerm 類別來獲取節氣列表
# from lunarcalendar import Converter
# from lunarcalendar.solarterm import solarTerm
# from lunarcalendar.solarterm import SolarTerm #取得所有節氣的名稱和索引
# from lunarcalendar import SolarTerm
# from lunarcalendar.solarterm import get_solar_terms
# from lunarcalendar.solarterm import get_solar_terms  # 正確用法
# from lunarcalendar._calc import specified_solar_term # 搭配節氣的索引和年份，來計算出精確的日期和時間
from .solar_terms_data import SOLAR_TERMS_INFO

logger = logging.getLogger(__name__)

# 新增一個函式來將日期轉換成包含星期幾的格式
def format_date_with_weekday(d: date) -> str:
    """
    將 datetime.date 物件格式化為 "YYYY年MM月DD日 (星期幾)" 的字串。
    """
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    weekday_index = d.weekday() # 0 = 星期一, 6 = 星期日
    weekday_str = weekdays[weekday_index]
    return f"{d.year}年{d.month:02d}月{d.day:02d}日 ({weekday_str})"

def get_solar_terms_for_year(year: int) -> list[dict]:
    """
    使用 lunarcalendar 獲取指定年份的所有 24 個節氣。
    直接使用 zh_solarterms 列表來獲取名稱和日期。
    
    Args:
        year (int): 要查詢的年份。
        
    Returns:
        list[dict]: 一個包含字典的列表，每個字典包含節氣名稱和發生的精確時間。
    """
    solar_terms = []

    # 遍歷 lunarcalendar 主套件中預定義的節氣列表
    for term_object in lunarcalendar.zh_solarterms:
        # 在 try 塊之前初始化 term_name，以避免 UnboundLocalError
        term_name = "Unknown"
        try:
            # 獲取節氣名稱 (使用繁體中文)
            term_name = term_object.get_lang('zh_hans')

            # 獲取節氣的精確日期 (datetime.date 物件)
            # 這裡的 term_object 內部有一個函式會根據年份計算日期
            term_date = term_object(year)

            # LunarCalendar 庫的 SolarTerm 類別定義了所有節氣的順序和名稱
            # 它們的內部索引是從 0 到 23

            solar_terms.append({
                "name": term_name,
                "date": term_date
            })

        except Exception as e:
            logger.error(f"無法取得 {year} 年 {term_name} 節氣資訊: {e}")

    # 根據日期對節氣列表進行排序
    solar_terms.sort(key=lambda x: x['date'])

    return solar_terms

# 範例：取得 2025 年的所有節氣
# all_terms_2025 = get_solar_terms_for_year(2025)

"""
for term in all_terms_2025:
    print(f"節氣：{term['name']:<4}，日期：{term['date']}")
"""

def get_today_solar_term_info(check_date: date = None) -> dict | None:
    """
    檢查指定日期（或今天）是否是某個節氣的開始日。
    使用 LunarCalendar 獲取節氣精確時間點。
    
    Args:
        check_date (date): 要檢查的日期。如果為 None，則使用今天的日期。
        
    Returns:
        dict | None: 如果指定日期是節氣的開始日，則返回該節氣的資訊字典；否則返回 None。
    """
    if check_date is None:
        check_date = datetime.now().date() # 只取日期部分
    
    logger.debug(f"正在檢查日期 {check_date} 是否為節氣開始日 (使用 LunarCalendar)。")

    # 獲取當前年份和下一年的節氣列表，以確保處理跨年節氣
    # 我們需要檢測的是精確到日期的匹配
    solar_terms_this_year = get_solar_terms_for_year(check_date.year)
    solar_terms_next_year = get_solar_terms_for_year(check_date.year + 1)
    
    # 合併並過濾出與今天日期匹配的節氣
    all_relevant_solar_terms = []
    for term in solar_terms_this_year + solar_terms_next_year:
        if term["date"] == check_date: # 比較日期部分
            all_relevant_solar_terms.append(term)
            
    # 通常一天只有一個節氣。如果有，返回時間最早的那個
    if all_relevant_solar_terms:
        all_relevant_solar_terms.sort(key=lambda x: x["date"])

        # --- 這裡開始合併詳細資訊 ---
        current_term_name = all_relevant_solar_terms[0]['name']
        term_details = SOLAR_TERMS_INFO.get(current_term_name, {})
        
        final_term_info = all_relevant_solar_terms[0].copy()
        final_term_info.update(term_details)
        # --- 這裡結束合併詳細資訊 ---

        final_term_info['formatted_date'] = format_date_with_weekday(final_term_info['date'])

        logger.info(f"日期 {check_date} 是節氣 【{final_term_info['name']}】 的開始日，精確時間：{final_term_info['date']}.")
        return final_term_info
    
    logger.debug(f"日期 {check_date} 不是任何節氣的開始日。")
    return None

def get_current_solar_term_info_for_display(target_dt: datetime = None) -> dict | None:
    """
    獲取當前日期時間所在的節氣資訊 (用於用戶手動查詢)。
    """
    if target_dt is None:
        target_dt = datetime.now()

    # 獲取去年、今年、明年的節氣，以確保判斷範圍足夠
    all_solar_terms_extended = []
    for year_offset in [-1, 0, 1]:
        all_solar_terms_extended.extend(get_solar_terms_for_year(target_dt.year + year_offset))
    
    all_solar_terms_extended.sort(key=lambda x: x["date"])

    current_solar_term = None
    for term in all_solar_terms_extended:
        if term["date"] <= target_dt.date():
            current_solar_term = term
        else:
            # 找到第一個在未來時間的節氣，即可停止
            break 
        
    if current_solar_term:
        # --- 這裡開始合併詳細資訊 ---
        term_details = SOLAR_TERMS_INFO.get(current_solar_term['name'], {})
        current_solar_term.update(term_details)
        # --- 這裡結束合併詳細資訊 ---

        # 新增：將日期物件轉換為包含星期幾的格式化字串
        # 並將其儲存到字典中，以供 flex_builder 使用
        current_solar_term['formatted_date'] = format_date_with_weekday(current_solar_term['date'])

        logger.info(f"用戶手動查詢：當前節氣為 {current_solar_term['name']} (發生於 {current_solar_term['date']})")
    else:
        logger.warning(f"用戶手動查詢：未能找到 {target_dt} 的當前節氣。")
    
    return current_solar_term