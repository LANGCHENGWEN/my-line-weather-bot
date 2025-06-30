import json
from utils.api_helper import get_messaging_api

def update_rich_menu_ids_config(config_path="rich_menu_ids.json"):
    line_bot_api = get_messaging_api()
    response = line_bot_api.get_rich_menu_list()
    
    # 取得所有 Rich Menu 物件（RichMenuResponse list）
    richmenus = response.richmenus  # 根據官方回傳屬性可能是 .richmenus
    
    # 假設你在 Rich Menu name 用 alias 命名規則，像 "main_menu_alias"、"settings_alias" 等
    alias_map = {}
    for menu in richmenus:
        alias_map[menu.name] = menu.rich_menu_id
    
    # 把結果存成 JSON 檔，方便你在程式讀取
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(alias_map, f, ensure_ascii=False, indent=2)
    
    print(f"已更新 Rich Menu ID 設定檔到 {config_path}")
    print(json.dumps(alias_map, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    update_rich_menu_ids_config()