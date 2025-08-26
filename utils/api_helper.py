# utils/api_helper.py
"""
統一管理和提供 LINE Messaging API 的客戶端實例。
通過將 API 客戶端實例化為「全局單例」，避免在程式運作期間重複創建，提高效能和資源利用率。
主要職責：
1. 單例模式：在檔案載入時就創建好 `ApiClient`, `MessagingApi`, `Configuration` 和 `MessagingApiBlob` 的實例。
2. 依賴注入：提供簡單的函式 (`get_line_bot_apis`, `get_messaging_api`)，讓其他模組可以輕鬆獲取這些實例，而不需要自己處理實例化的細節和設定。
3. 優化效能：避免每個請求都重新建立 API 連線，特別是在處理高流量時，能顯著減少延遲和資源消耗。
"""
from linebot.v3.messaging import ApiClient, MessagingApi, Configuration, MessagingApiBlob

from config import LINE_CHANNEL_ACCESS_TOKEN

# --- 全局實例的初始化，避免重複建立 ---
# 這些變數會在檔案被載入時只執行一次
_conf = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
_api_client = ApiClient(_conf)

# --- MessagingApi 實例：用於傳送訊息，如 TextMessage, FlexMessage ---
_messaging_api = MessagingApi(_api_client)

# --- MessagingApiBlob 實例：用於處理檔案相關操作，如上傳 Rich Menu 圖片 ---
_messaging_api_blob = MessagingApiBlob(_api_client)

# --- 獲取 Line Bot Messaging API 和 Blob API 的實例 ---
def get_line_bot_apis():
    """
    用於需要同時操作訊息和檔案（如 Rich Menu 圖片）的場景。
    """
    return _messaging_api, _messaging_api_blob # 直接返回兩個預先創建好的全局實例

# --- 取得共用的 MessagingApi 實例 ---
def get_messaging_api():
    """
    主要供大多數只發送訊息的模組使用。
    """
    return _messaging_api