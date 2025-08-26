# rich_menu_manager/rich_menu_configs.py
"""
所有 LINE Rich Menu 設定的中央配置中心。
儲存所有與 Rich Menu 相關的靜態資訊：
1. 用於程式碼內部識別的別名常數（`_ALIAS`）。
2. 在部署時需要上傳的 Rich Menu 圖片路徑。
3. 用於生成 Rich Menu 結構的函式引用。
4. 預設綁定給新用戶的 Rich Menu 別名。

把這些靜態資訊全部集中到一個單一、易於管理的地方。
這樣設計的好處是當需要新增、修改或刪除 Rich Menu 時，只需要更新這個檔案，而無需修改程式碼中其他處理 Rich Menu 邏輯的部分。
提高整個系統的靈活性、可維護性和可讀性。
"""
from .rich_menu_definitions import (
    get_main_menu_rich_menu, get_weather_query_rich_menu,
    get_typhoon_zone_rich_menu, get_lifestyle_reminders_rich_menu, get_settings_rich_menu
)

# --- 定義所有 Rich Menu 的別名常數 ---
"""
這些別名是程式碼中用來識別不同 Rich Menu 的字串 ID。
1. 避免硬編碼：將字串 `main_menu_alias` 等定義為常數，可以避免在程式碼中到處使用魔術字串。
2. 提高可讀性：在程式碼中使用 `MAIN_MENU_ALIAS` 比直接使用 `richmenu-xxx` 或字串 `'main_menu_alias'` 更能清楚表達其意圖。
3. 便於維護：如果未來需要更改別名，只需要在一個地方修改這個常數，而不需要搜尋和替換所有檔案中的字串。
"""
MAIN_MENU_ALIAS     = "main_menu_alias"
WEATHER_QUERY_ALIAS = "weather_query_alias"
TYPHOON_ZONE_ALIAS  = "typhoon_zone_alias"
LIFE_REMINDER_ALIAS = "life_reminder_alias"
SETTINGS_ALIAS      = "settings_alias"

# --- 將 Rich Menu 別名與實際的 LINE Rich Menu ID 進行映射的字典 ---
"""
這個字典提供一個快速查詢的機制，讓程式碼可以根據一個易於閱讀的別名（例如 `MAIN_MENU_ALIAS`），快速找到對應的實際 Rich Menu ID。
雖然在理想的部署流程中，這些 ID 會由程式碼自動生成並綁定，但在一些特定的手動管理或測試情境下，這個映射表仍然非常有用，它能作為一個中央參考點，確保所有部分都使用正確的 ID。
"""
RICH_MENU_ALIAS_MAP = {
    MAIN_MENU_ALIAS     : "richmenu-8d2c295204caff1289fee7d421c10397",
    WEATHER_QUERY_ALIAS : "richmenu-c4923c799f3bf211c57b091b56b7064d",
    TYPHOON_ZONE_ALIAS  : "richmenu-481b92eb23081bb6ca9bc5d49bb8d434",
    LIFE_REMINDER_ALIAS : "richmenu-8a17578a9c3ee9af0e579795ee0bd402",
    SETTINGS_ALIAS      : "richmenu-7fd1fc84a4a253c645f1790d538b04cb"
}

# --- 預設綁定給新加入用戶的 Rich Menu 別名 ---
# 為新用戶提供一個統一的入口點，確保每次有新用戶時，都能自動將他們綁定到一個預設的 Rich Menu，實現自動化和一致性
DEFAULT_RICH_MENU_ALIAS = MAIN_MENU_ALIAS

# --- Rich Menu 管理的核心配置，每個字典都代表一個完整的 Rich Menu ---
"""
這種結構將一個 Rich Menu 的所有相關資訊組織在一起。
包括：
- `get_menu_obj_func`：指向一個用來動態生成 Rich Menu 結構的函式。
- `image_path`：指向用於該 Rich Menu 的圖片檔案路徑。
- `alias`：與該 Rich Menu 相關聯的別名常數。

這種設計使得部署工具（例如 `rich_menu_deployer.py`）可以簡單的遍歷這個列表。
為每一個配置項執行一整套完整的部署流程：
1. 呼叫 `get_menu_obj_func` 創建 Rich Menu 物件。
2. 根據 `image_path` 上傳圖片。
3. 使用 `alias` 創建或更新別名。
這種高度模組化的配置方式，讓整個 Rich Menu 的管理和部署變得非常簡潔和自動化。
"""
ALL_RICH_MENU_CONFIGS = [
    {
        'get_menu_obj_func' : get_main_menu_rich_menu,
        'image_path'        : 'rich_menu_manager/rich_menus/main_menu_image.png',
        'alias'             : MAIN_MENU_ALIAS
    },
    {
        'get_menu_obj_func' : get_weather_query_rich_menu,
        'image_path'        : 'rich_menu_manager/rich_menus/weather_query_menu_image.png',
        'alias'             : WEATHER_QUERY_ALIAS
    },
    {
        'get_menu_obj_func' : get_typhoon_zone_rich_menu,
        'image_path'        : 'rich_menu_manager/rich_menus/typhoon_zone_menu_image.png',
        'alias'             : TYPHOON_ZONE_ALIAS
    },
    {
        'get_menu_obj_func' : get_lifestyle_reminders_rich_menu,
        'image_path'        : 'rich_menu_manager/rich_menus/life_reminder_menu_image.png',
        'alias'             : LIFE_REMINDER_ALIAS
    },
    {
        'get_menu_obj_func' : get_settings_rich_menu,
        'image_path'        : 'rich_menu_manager/rich_menus/settings_menu_image.png',
        'alias'             : SETTINGS_ALIAS
    }
]