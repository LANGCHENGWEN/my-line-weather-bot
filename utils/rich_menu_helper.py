import json
from pathlib import Path

_JSON_PATH = Path("rich_menu_ids.json")

def load_alias_map() -> dict:
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

def get_rich_menu_id(alias: str) -> str | None:
    """依 alias 取 Rich Menu ID；找不到則回傳 None"""
    return load_alias_map().get(alias)