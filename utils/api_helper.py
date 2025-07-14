# utils/api_helper.py
from linebot.v3.messaging import MessagingApi, ApiClient, Configuration

# 讀取環境變數或你現有的 config
from config import LINE_CHANNEL_ACCESS_TOKEN

_conf = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
_api_client = ApiClient(_conf)  # 避免重複建立
_messaging_api = MessagingApi(_api_client)

def get_api():
    """
    用 `with get_api() as api:` 取得 MessagingApi 實例
    """
    return _api_client

def get_messaging_api():
    """取得共用的 MessagingApi 實例"""
    return _messaging_api