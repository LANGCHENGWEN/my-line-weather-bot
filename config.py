# config.py
"""
集中處理所有配置：
1. 環境變數的讀取，特別是 LINE Bot 和氣象局 API 的金鑰。
2. 全局日誌 (logging) 系統的設定，確保所有日誌都有統一的格式和輸出目的地。
3. 統整中央氣象署 (CWA) 各類天氣資料的 API 端點，方便在其他模組中引用。
"""
import os # 操作作業系統環境變數
import sys
import logging
from dotenv import load_dotenv # 載入 .env 檔案中的環境變數
from logging.handlers import TimedRotatingFileHandler

# --- 載入 .env 檔案中的環境變數 ---
# load_dotenv() 會搜尋並讀取同層或父層的 .env，將其轉為系統環境變數，之後可用 os.getenv() 取得
load_dotenv()

# --- 環境變數設定 ---
# 如果環境變數不存在，使用預設值
# 控制 log 顯示的詳細程度
LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper() # .upper() 確保字串是大寫，以便與 logging 模組的等級名稱匹配
# 指定 log 儲存的檔名
LOG_FILE = os.getenv("LOG_FILE",  "main.log")

# 把字串轉成 logging 模組用的數字等級；如果字串無效，就退回 INFO 等級
"""
DEBUG (10)：詳細的除錯資訊，僅在開發或除錯階段使用。
INFO (20)：程式按預期運行，提供正常的運行資訊。
WARNING (30)：發生了意外情況，或可能發生問題，例如「磁碟空間不足」，但程式仍會繼續運行。
ERROR (40)：程式的某些功能因嚴重問題而無法正常執行。
CRITICAL (50)：非常嚴重的錯誤，可能導致程式無法繼續執行。
"""
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)

# 是否啟用 debug 模式，部署到雲端時，通常預設是 False
IS_DEBUG_MODE = os.getenv("IS_DEBUG_MODE", "False").lower() == "true" # .lower() == "true" 確保任何大小寫的 "true" 都會被正確解析
# 是否啟用每日推播
ENABLE_DAILY_NOTIFICATIONS = os.getenv("ENABLE_DAILY_NOTIFICATIONS", "False").lower() == "true"

# --- 建立全域 Logger 設定函式 ---
def setup_logging() -> None:
    """
    將所有日誌的輸出邏輯集中在一個地方。
    配置根日誌器，並添加兩個處理器 (handler)：一個輸出到終端機，另一個輸出到 log 檔案。
    避免在多個檔案中重複設定日誌系統，讓整個專案共享相同的設定。
    """
    root = logging.getLogger() # 取得根日誌器，這是所有日誌器的最高層級

    # 移除並關閉所有 handler，避免重複設定日誌
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    
    root.setLevel(LOG_LEVEL) # 設定根日誌器的最低日誌等級，會影響所有子日誌器

    # 共用的格式：時間 - logger 名稱 - 等級 - 檔案名稱:行號 - 訊息
    # 這是標準且詳細的日誌格式，有助於追蹤問題的來源
    fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )

    # console handler: 適合在開發或部署到雲端查看，日誌會直接輸出到標準輸出 (stdout) (預設是終端機)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(LOG_LEVEL)
    ch.setFormatter(fmt)

    root.addHandler(ch) # 將 console handler 添加到根日誌器

    # rotating file handler: 記錄更完整的 DEBUG 資訊到 log 檔案，可追蹤歷史紀錄
    # 這個 handler 只有在 ENABLE_FILE_LOG 環境變數設定為 "true" 時才會啟用
    if os.getenv("ENABLE_FILE_LOG", "False").lower() == "true": # 是否啟用檔案 log 輸出
        # TimedRotatingFileHandler 會在午夜 (when="midnight") 輪換檔案，並保留 7 個備份 (backupCount=7)
        fh = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7, encoding="utf-8")
        fh.setLevel(logging.DEBUG) # 設定檔案的最低日誌等級為 DEBUG，記錄最詳細的資訊
        fh.setFormatter(fmt)       # 套用格式
        root.addHandler(fh)        # 將 file handler 添加到根日誌器

setup_logging()                      # 呼叫函式以初始化 logging
logger = logging.getLogger(__name__) # 建立一個預設的 logger，供其他模組引用此檔案時使用

# --- 讀取 LINE Bot 憑證 ---
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# --- 基本檢查：若缺少憑證則顯示錯誤 ---
"""
在程式啟動時檢查必要的環境變數是否已經設定。
如果變數為 None，則發出警告並終止程式。
"""
if LINE_CHANNEL_SECRET is None:
    logger.error("環境變數 LINE_CHANNEL_SECRET 未設定。請確認已設定並重新啟動程式。")

if LINE_CHANNEL_ACCESS_TOKEN is None:
    logger.error("環境變數 LINE_CHANNEL_ACCESS_TOKEN 未設定。請確認已設定並重新啟動程式。")

# --- 交通部中央氣象署 Open Data 平台 API 設定 ---
CWA_API_KEY = os.getenv('CWA_API_KEY')
CWA_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/" # API 基本網址 (共同前綴)

# --- 各功能對應的 CWA API 端點 ---
# 現在天氣觀測報告-有人氣象站資料 (用於即時天氣)
CWA_CURRENT_WEATHER_API = CWA_BASE_URL + "O-A0003-001" # 更新頻率：10 分鐘
# 自動氣象站資料-無人自動站氣象資料 (O-A0001-001) 更新頻率：1 小時

# 一般天氣預報-今明 36 小時天氣預報 (用於每日天氣的天氣現象、最高溫度、最低溫度、降雨機率、舒適度指數)
CWA_FORECAST_36HR_API = CWA_BASE_URL + "F-C0032-001"

# 鄉鎮天氣預報-臺灣未來 3 天天氣預報 (逐 3 小時) (用於每日天氣的體感溫度、濕度、風速、風向)
CWA_FORECAST_3DAYS_API = CWA_BASE_URL + "F-D0047-089"

# 紫外線指數-每日紫外線指數最大值 (用於每日天氣的紫外線指數)
CWA_TODAY_UVINDEX_API = CWA_BASE_URL + "O-A0005-001"

# 鄉鎮天氣預報-臺灣未來 1 週天氣預報 (用於未來 7 天預報與週末天氣功能)
CWA_FORECAST_1WEEK_API = CWA_BASE_URL + "F-D0047-091"

# 颱風消息與警報-熱帶氣旋路徑 (用於颱風現況)
CWA_TYPHOON_WARNING_API = CWA_BASE_URL + "W-C0034-005"

# 天氣特報-各別天氣警特報之內容及所影響之區域 (用於地區影響預警)
CWA_TYPHOON_PROBABILITY_API = CWA_BASE_URL + "W-C0033-002"

# 天氣特報-各別縣市地區目前之天氣警特報情形 (目前沒用到，如果之後要針對不同縣市分別查詢再加入這個功能)
CWA_WEATHER_ALERTS_API = CWA_BASE_URL + "W-C0033-001"

# --- 外部連結 ---
# 中央氣象署颱風專區主頁（用於「颱風現況」功能）
CWA_TYPHOON_PORTAL_URL = "https://www.cwa.gov.tw/V8/C/P/Typhoon/TY_NEWS.html"

# 國家災害防救科技中心 (NCDR) 的颱風路徑圖連結 
NCDR_TYPHOON_PATH_URL = "https://watch.ncdr.nat.gov.tw/watch_page_typhoon_v2"

# 中央氣象署的颱風路徑圖連結 (作為備用)
CWA_TYPHOON_MAP_URL = "https://app.cwa.gov.tw/web/obsmap/typhoon.html"