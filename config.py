# config.py
# 這個檔案將負責配置你的 API 金鑰和 logging 系統
import os # 引入 os 模組，用於操作作業系統環境變數
import sys
import logging
from dotenv import load_dotenv # 從 dotenv 模組引入 load_dotenv 函數，用於加載 .env 檔案中的環境變數
from logging.handlers import TimedRotatingFileHandler

# --- 載入 .env 檔案中的環境變數 ---
# load_dotenv() 會搜尋並讀取同層或父層的 .env，將其轉為系統環境變數，之後可用 os.getenv() 取得
load_dotenv()

# --- 日誌等級與檔案名稱設定 ---
# 從環境變數讀取 LOG_LEVEL 與 LOG_FILE，預設值為 "INFO" 與 "main.log"
LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE",  "main.log")

# 把字串轉成 logging 模組用的數字等級，找不到就退回 INFO
LOG_LEVEL = getattr(logging, LOG_LEVEL_NAME, logging.INFO)

# 本機開發請設 True，部署到雲端請改 False
IS_DEBUG_MODE = os.getenv("IS_DEBUG_MODE", "False").lower() == "true"
# 先關閉；部署到雲端想推播再改 True
ENABLE_DAILY_NOTIFICATIONS = os.getenv("ENABLE_DAILY_NOTIFICATIONS", "False").lower() == "true"

# --- 建立全域 Logger 設定函式 ---
def setup_logging() -> None:
    """
    這段將所有日誌輸出邏輯集中到一個地方：
    避免在多個檔案重複撰寫 handler 與 formatter。
    只要呼叫一次即可，全專案共享相同設定。
    """
    """
    設定全局的 logging 配置。
    日誌會輸出到文件並在午夜輪換。
    """
    root = logging.getLogger() # 為整個應用程式配置一次根日誌器，方便集中管理日誌和全域配置
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    
    root.setLevel(LOG_LEVEL) # 設定根日誌器的最低日誌等級

    # 共用的格式：時間 - logger 名稱 - 等級 - 訊息
    fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )

    # console : 適合在開發或部署到雲端查看，預設 INFO
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(LOG_LEVEL)
    ch.setFormatter(fmt)

    """
    # 重新用 UTF-8 編碼打開 sys.stdout 的檔案描述符，避免編碼錯誤
    if sys.platform.startswith("win"):
        try:
            ch.stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
        except Exception as e:
            root.error(f"重設 Console Handler 編碼失敗: {e}")
    """

    root.addHandler(ch)

    # rotating file：記錄更完整的 DEBUG 資訊到檔案，可追蹤歷史
    if os.getenv("ENABLE_FILE_LOG", "False").lower() == "true":
        fh = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        root.addHandler(fh)

setup_logging() # 呼叫函式以初始化 logging
logger = logging.getLogger(__name__) # 供其他模組引用此檔案時使用的預設 logger

# --- 讀取 LINE Bot 憑證 ---
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# --- 基本檢查：若缺少憑證則顯示錯誤 ---
# 如果變數為 None，則發出警告並終止程式
if LINE_CHANNEL_SECRET is None:
    logger.error("環境變數 LINE_CHANNEL_SECRET 未設定。請確認已設定並重新啟動程式。")

if LINE_CHANNEL_ACCESS_TOKEN is None:
    logger.error("環境變數 LINE_CHANNEL_ACCESS_TOKEN 未設定。請確認已設定並重新啟動程式。")

# --- 交通部中央氣象署 Open Data 平台 API 設定 ---
CWA_API_KEY = os.getenv('CWA_API_KEY')
CWA_BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/" # API 基本網址 (共同前綴)
LOCATION_NAME = "臺中市"
DEFAULT_COUNTY = "臺中市"  # 查詢資料的城市名稱

YOUR_LINE_USER_ID = os.getenv("YOUR_LINE_USER_ID")

# --- 各功能對應的 CWA API 端點 ---
# 1. 即時天氣查詢 (Current Weather Observations)
# 資料集名稱：自動氣象站-氣象觀測資料 (Automated Weather Station - Meteorological Observation Data)
# 提供氣溫、濕度、風速等即時資料。
CWA_CURRENT_WEATHER_API = CWA_BASE_URL + "O-A0003-001" # O-A0001-001(1小時更新)

# 2. 未來天氣預報 (Future Weather Forecasts)
# 2.1 鄉鎮天氣預報-臺灣未來3天天氣預報 (包含未來36小時詳細預報)
# 提供天氣現象、降雨機率、最高/最低溫度、風速等。
CWA_FORECAST_36HR_API = CWA_BASE_URL + "F-C0032-001" # ***F‑C0032‑001(適合找城市) # ***F-D0047-089(適合找城市+區域) # F-C0032-005

# 2.2 鄉鎮天氣預報-臺灣未來1週天氣預報 (包含未來7天預報)
# 提供天氣現象、最高/最低溫度等，降雨機率通常只到前三天。
CWA_FORECAST_1WEEK_API = CWA_BASE_URL + "F-D0047-091" # ***F-D0047-091 # F-D0047-093

# 3. 颱風資訊 (Typhoon Information)
# 3.1 颱風消息與警報-颱風警報
# 提供目前颱風名稱、位置、移動、風速、半徑等基本資訊。
CWA_TYPHOON_WARNING_API = CWA_BASE_URL + "W-C0034-005"

# 3.2 颱風消息與警報-颱風侵襲機率
# 提供各地區受颱風侵襲的機率。
CWA_TYPHOON_PROBABILITY_API = CWA_BASE_URL + "W-C0033-002"

# 4. 天氣特報 (Weather Alerts/Warnings)
# 資料集名稱：天氣特報-各別縣市地區目前之天氣警特報情形
# 提供豪大雨、強風、低溫等警特報資訊。
CWA_WEATHER_ALERTS_API = CWA_BASE_URL + "W-C0033-001"

# 中央氣象署颱風專區主頁（用於「颱風現況」功能）
CWA_TYPHOON_PORTAL_URL = "https://www.cwa.gov.tw/V8/C/P/Typhoon/TY_NEWS.html"

# --- 颱風路徑圖連結 ---
NCDR_TYPHOON_PATH_URL = "https://watch.ncdr.nat.gov.tw/watch_page_typhoon_v2"

# --- 颱風路徑圖連結 (非API，直接提供官方網頁連結) ---
# 您可以引導使用者前往此網址查看最新颱風路徑圖。
# CWA_TYPHOON_MAP_URL = "https://app.cwa.gov.tw/web/obsmap/typhoon.html"