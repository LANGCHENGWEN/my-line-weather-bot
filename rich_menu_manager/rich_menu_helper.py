# rich_menu_manager/rich_menu_helper.py
"""
作為一個輔助工具，專門處理 Rich Menu 別名（alias）與其對應 ID 的映射關係。
主要作用有兩點：
1. 提供單一數據源：集中處理從 `rich_menu_ids.json` 檔案讀取數據的邏輯，這個檔案是由 `rich_menu_deployer.py` 腳本在部署時自動生成的。
2. 簡化查詢操作：提供一個簡單的 `get_rich_menu_id` 函式，讓其他程式模組可以透過一個易於理解的「別名」來獲取實際的 Rich Menu ID，而不需要自己去讀取和解析 JSON 檔案。

這樣設計的好處是將資料存取邏輯與業務邏輯分離，提高程式碼的模組化和可維護性。
當需要切換 Rich Menu 時，上層程式碼只需知道別名，底層的具體 ID 查詢由這個模組負責。
"""
import json
from pathlib import Path

# 將 rich_menu_ids.json 的完整路徑儲存到 _JSON_PATH 這個變數裡
_JSON_PATH = Path(__file__).parent / "rich_menu_ids.json"

def load_alias_map() -> dict:
    """
    載入所有 Rich Menu ID。
    從 `rich_menu_ids.json` 檔案中讀取並解析 Rich Menu 別名與 ID 的對應關係。
    整個模組的數據存取層，所有對 alias-ID 映射數據的讀取操作都應該透過這個函式進行。
    成功時返回一個包含所有映射關係的字典；若檔案不存在或解析失敗，則返回一個空字典，確保函式在任何情況下都能安全的執行。
    """
    # 檢查 JSON 檔案是否存在
    if not _JSON_PATH.exists():
        return {} # 返回一個空字典
    try:
        with _JSON_PATH.open(encoding="utf-8") as fp:
            return json.load(fp) # 返回一個包含所有映射關係的字典
    except Exception:
        return {} # 返回一個空字典

def get_rich_menu_id(alias: str) -> str | None:
    """
    查詢單一 Rich Menu ID。
    提供一個簡單的介面，讓其他模組能夠根據一個別名（alias）來獲取對應的 Rich Menu ID。
    呼叫 `load_alias_map()` 來獲取完整的映射字典，然後使用字典的 `.get()` 方法進行查詢。
    這種設計將「如何獲取數據」的細節（讀取 JSON 檔案）與「如何使用數據」的邏輯（查詢 ID）分開，使得程式碼更加清晰和解耦。
    如果找不到對應的 ID，`get()` 方法會安全的返回 `None`。
    """
    return load_alias_map().get(alias)