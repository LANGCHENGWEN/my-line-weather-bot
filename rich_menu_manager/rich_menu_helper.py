# rich_menu_helper.py
# 記錄了所有的「Rich Menu 別名」和「Rich Menu ID」
# 當其他部分需要使用某個 Rich Menu 時，只要告訴這個模組 Rich Menu 別名，它就能查到對應的 Rich Menu ID，然後 Line Bot 就可以用這個 Rich Menu ID 去對 Line 平台發出指令
import json
from pathlib import Path

_JSON_PATH = Path("rich_menu_ids.json")

def load_alias_map() -> dict: # 載入別名與 ID 的對應關係
    """
    回傳 {'main_menu_alias': 'richmenu-xxx', ...}
    若檔案不存在則回傳空 dict。
    """
    if not _JSON_PATH.exists():
        return {}
    try:
        with _JSON_PATH.open(encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}

def get_rich_menu_id(alias: str) -> str | None: # 根據別名獲取 Rich Menu ID
    """依 alias 取 Rich Menu ID；找不到則回傳 None"""
    return load_alias_map().get(alias)