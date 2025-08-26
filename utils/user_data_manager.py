# utils/user_data_manager.py
"""
本地端的資料庫管理模組，用於開發和測試。
使用輕量級的 SQLite 資料庫模擬雲端資料庫（如 Firestore）的功能，以便在沒有網路連線或雲端環境時，能夠在本機運行並測試應用程式的數據持久化邏輯。
主要職責：
1. 資料庫初始化：在程式啟動時，自動建立一個名為 `user_data.db` 的 SQLite 資料庫檔案和 `users` 資料表，確保資料庫環境準備就緒。
2. 數據操作封裝：提供多個函式，用於對用戶數據進行新增、更新、查詢和刪除等操作，將底層的 SQL 語句抽象化。
3. 業務邏輯支援：包含與應用程式業務邏輯相關的函式，例如設定用戶狀態、儲存預設城市、管理推播設定等。
4. 系統級數據管理：使用一個固定的用戶 ID 來儲存和讀取系統級的元數據，例如上次執行任務的時間戳。

***這個檔案僅用於本地開發，在實際部署到雲端（如 GCP Cloud Run）時，應使用更為可靠和可擴展的資料庫服務，例如 Firestore，並使用 `firestore_manager.py` 來替代本檔案。
"""
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, List, Dict, Optional
from .major_stations import ALL_TAIWAN_COUNTIES

logger = logging.getLogger(__name__)

# 建立資料庫檔案與資料表
DB_PATH = Path("user_data.db")

# --- 初始化資料庫和資料表 ---
"""
這段程式碼在檔案被載入時，會自動執行一次。
- `sqlite3.connect(DB_PATH)`: 建立一個與 SQLite 資料庫的連線；如果檔案不存在，會自動創建。
- `with ... as conn`: 這是 Python 的上下文管理器，確保在程式區塊執行完畢或發生錯誤時，資料庫連線會被正確關閉，防止資源洩漏。
- `CREATE TABLE IF NOT EXISTS`: 這個 SQL 語句是檢查 `users` 資料表是否已經存在，如果不存在才創建，避免重複創建導致錯誤。
- `PRIMARY KEY`: 確保 `user_id` 是唯一的，並用於快速查詢。
"""
with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        default_city TEXT,
        state TEXT,
        meta_json TEXT
    )
    """)
    conn.commit()

# --- 私有輔助函式，用於從資料庫中獲取指定用戶的指定欄位值 ---
def _get(conn: sqlite3.Connection, col: str, user_id: str) -> Any:
    """
    封裝基本的 SQL 查詢邏輯和錯誤處理。
    """
    try:
        cur = conn.execute(f"SELECT {col} FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        return row[0] if row else None
    except sqlite3.Error as e:
        logger.error(f"查詢用戶 {user_id} 的欄位 {col} 時發生資料庫錯誤: {e}", exc_info=True)
        return None

# --- 更新或插入用戶資料 ---
def _upsert_cols(user_id: str, **cols: Any):
    """
    如果用戶不存在則插入，否則更新指定欄位。
    使用 SQLite 的 `ON CONFLICT DO UPDATE` 功能，避免重複寫入。
    """
    keys = list(cols.keys())
    vals = list(cols.values())

    """
    這段程式碼動態的根據傳入的鍵值對（`**cols`）構建 SQL 語句。
    - `sets = ", ".join(f"{k}=excluded.{k}" for k in keys)`: 使用 `excluded` 關鍵字，這是 `ON CONFLICT` 語句的語法。
       如果發生衝突（`user_id` 已存在），就將該欄位的值更新為新傳入的值（即 `excluded.k`）。
    - `placeholders = ", ".join(["?"] * len(keys))`: 使用 `?` 作為參數佔位符是 SQLite 的最佳實踐。
       可以防止 SQL 注入攻擊，並確保數據類型被正確處理。
    """
    # 構建 SET 語句用於 ON CONFLICT DO UPDATE
    sets = ", ".join(f"{k}=excluded.{k}" for k in keys)

    # 構建 VALUES 的佔位符
    placeholders = ", ".join(["?"] * len(keys))

    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                f"""
                INSERT INTO users (user_id,{','.join(keys)})
                VALUES (?,{placeholders})
                ON CONFLICT(user_id) DO UPDATE SET {sets}
                """,
                (user_id, *vals), # `*vals` 將列表解包成獨立的參數
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"更新或插入用戶 {user_id} 資料時發生資料庫錯誤: {e}", exc_info=True)

# --- 查詢所有用戶的預設城市 ---
def get_users_by_city() -> Dict[str, List[str]]:
    """
    獲取一個字典，鍵為城市名稱，值為該城市所有用戶 ID 。
    這個函式特別用於定時推播任務，可以高效的按城市分組用戶。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # 查詢所有用戶的 user_id 和 default_city
        cursor.execute("SELECT user_id, default_city FROM users WHERE default_city IS NOT NULL")
        rows = cursor.fetchall()
    
    city_users = {}
    for user_id, city in rows:
        # 先檢查城市名稱是否已在字典中；如果沒有，就為該城市創建一個空的列表
        # 將每個用戶 ID 加入到其對應城市的列表中，最終得到一個按城市分組的字典
        if city not in city_users:
            city_users[city] = []
        city_users[city].append(user_id)
        
    return city_users

# --- 設定指定用戶的狀態，並儲存相關的額外數據 ---
def set_user_state(user_id: str, state: str, data: Dict[str, Any] = None):
    """
    這個函式用於管理多步驟對話的狀態，例如在詢問用戶預設城市時，將狀態設定為「等待城市輸入」。
    """
    # 載入現有的 meta_json，以便合併新的 data
    current_meta_json = get_user_metadata(user_id, "all_meta", {})
    
    # 將狀態相關數據存儲在 metadata 的 'state_data' 鍵下
    current_meta_json['state_data'] = data if data is not None else {}
    
    # 將更新後的 meta_json 轉換為字串
    # SQLite 的 TEXT 欄位無法直接儲存 Python 字典；因此需要將字典序列化為 JSON 字串後再存入資料庫
    meta_json_str = json.dumps(current_meta_json, ensure_ascii=False)

    # 呼叫底層的 `_upsert_cols` 函式來更新數據庫
    _upsert_cols(user_id, state=state, meta_json=meta_json_str)
    logger.debug(f"已設定用戶狀態: user_id={user_id}, state={state}, data={data}")

# --- 取得指定用戶的當前狀態及相關數據 ---
def get_user_state(user_id: str) -> Dict[str, Any]:
    """
    這個函式是 `set_user_state` 的反向操作，用於在每次收到用戶訊息時，查詢用戶當前所處的對話狀態。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT state, meta_json FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()

    if row:
        state = row[0]
        meta_json_str = row[1]
        
        data_from_meta = {}
        if meta_json_str:
            # 如果儲存的 `meta_json` 字串格式不正確，`json.loads()` 會拋出異常
            # 捕獲這個異常並重置該欄位防止程式崩潰，並清除錯誤資料
            try:
                full_meta = json.loads(meta_json_str)
                data_from_meta = full_meta.get('state_data', {}) # 從 'state_data' 鍵中獲取數據
            except json.JSONDecodeError:
                logger.warning(f"用戶 {user_id} 的 meta_json 解析失敗，已重置。", exc_info=True)
                _upsert_cols(user_id, meta_json=None) # 清除錯誤的 JSON
        
        return {"state": state if state is not None else "idle", "data": data_from_meta}
    else:
        # 如果用戶不存在，返回預設的閒置狀態
        return {"state": "idle", "data": {}}

# --- 清除指定用戶的狀態和相關數據 ---
def clear_user_state(user_id: str) -> None:
    """
    在對話結束時重置用戶狀態。
    """
    current_meta_json = get_user_metadata(user_id, "all_meta", {})
    if 'state_data' in current_meta_json:
        del current_meta_json['state_data'] # 如果存在，則刪除 `state_data` 鍵
    meta_json_str = json.dumps(current_meta_json, ensure_ascii=False)
    
    # 將 `state` 欄位設定為 `None` 來清除它
    _upsert_cols(user_id, state=None, meta_json=meta_json_str)

# --- 儲存指定用戶的預設城市 ---
def save_default_city(user_id: str, city_name: str) -> None:
    _upsert_cols(user_id, default_city=city_name)

# --- 從資料庫中取得指定用戶的預設城市 ---
def get_default_city(user_id: str) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        return _get(conn, "default_city", user_id)
    
# --- 設定指定用戶的任意 metadata ---
def set_user_metadata(user_id: str, **kwargs: Any) -> None:
    """
    這是一個通用的函式，用於在 `meta_json` 欄位下儲存任意的鍵值對。
    從資料庫讀取現有的 metadata，轉換為字典，與新傳入的數據合併，再將結果寫回資料庫。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur_json = _get(conn, "meta_json", user_id)
        # 確保如果 cur_json 是 None 或無效，能正確初始化為空字典
        try:
            meta: Dict[str, Any] = json.loads(cur_json) if cur_json else {}
        except json.JSONDecodeError:
            logger.warning(f"用戶 {user_id} 的現有 meta_json 無效，將重新初始化。", exc_info=True)
            meta = {}
        meta.update(kwargs) # 使用 `.update()` 方法來合併新的數據到現有的 metadata 字典中

    _upsert_cols(user_id, meta_json=json.dumps(meta, ensure_ascii=False))

# --- 獲取指定用戶的某個 metadata ---
def get_user_metadata(user_id: str, key: str, default: Any = None) -> Any:
    """
    從資料庫中讀取 `meta_json` 字串，將其解析為字典，然後從字典中查找指定鍵的值。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur_json = _get(conn, "meta_json", user_id)
    
    # 處理用戶不存在的情況
    if not cur_json:
        return {} if key == "all_meta" else default
    
    try:
        full_meta = json.loads(cur_json)
        if key == "all_meta":
            return full_meta
        # 獲取特定鍵的值，如果不存在則返回預設值
        return full_meta.get(key, default)
    except json.JSONDecodeError:
        logger.warning(f"用戶 {user_id} 的 meta_json 解析失敗，已重置。", exc_info=True)
        _upsert_cols(user_id, meta_json=None)
        return {} if key == "all_meta" else default

# --- 驗證給定的城市名稱是否在有效城市列表中 ---
def is_valid_city(city_name: str) -> bool:
    return city_name in ALL_TAIWAN_COUNTIES

# --- 獲取指定用戶的推播設定 ---
def get_user_push_settings(user_id: str) -> Dict[str, bool]:
    """
    在發送推播前，為每個用戶單獨查詢，確認他們是否開啟了 FEATURE_ID (推播功能名稱)。
    """
    return get_user_metadata(user_id, "push_settings", {})

# --- 更新指定用戶的單個推播設定 ---
def update_user_push_setting(user_id: str, feature_id: str, is_enabled: bool):
    # 先讀取現有的設定，更新單個鍵值，然後再寫入回去
    # 確保只更新指定的推播功能，而不會覆蓋用戶的其他推播設定
    current_push_settings = get_user_push_settings(user_id) # 讀取
    current_push_settings[feature_id] = is_enabled # 更新
    set_user_metadata(user_id, push_settings=current_push_settings) # 寫回
    logger.info(f"用戶 {user_id} 的 {feature_id} 推播已設定為: {is_enabled}")

# --- 獲取所有開啟特定推播功能的用戶 ID ---
def get_users_with_push_enabled(feature_id: str) -> List[str]:
    """
    資料庫查詢，尋找 meta_json.push_settings.feature_id 為 true 的用戶。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # 查詢所有用戶的 user_id 和 meta_json
        cursor.execute("SELECT user_id, meta_json FROM users")
        rows = cursor.fetchall()
    
    enabled_users = []
    for user_id, meta_json_str in rows:
        try:
            meta = json.loads(meta_json_str) if meta_json_str else {}
            # 檢查 'push_settings' 字典中是否開啟了指定的 feature_id
            if meta.get('push_settings', {}).get(feature_id):
                enabled_users.append(user_id)
        except json.JSONDecodeError:
            logger.warning(f"用戶 {user_id} 的 meta_json 解析失敗，已跳過。")
    return enabled_users

SYSTEM_USER_ID = "system_metadata" # 使用更明確的ID

# --- 獲取系統級的元數據 ---
def get_system_metadata(key: str, default: Any = None) -> Any:
    """
    讀取上次推播的颱風 ID。
    這個函式和 `get_user_metadata` 共享底層邏輯，但使用一個固定的 `SYSTEM_USER_ID` 來存取系統級的設定。
    """
    return get_user_metadata(SYSTEM_USER_ID, key, default)

# --- 設定系統級的元數據 ---
def set_system_metadata(**kwargs: Any) -> None:
    """
    寫入這次推播的颱風 ID。
    這個函式和 `set_user_metadata` 共享底層邏輯，同樣使用 `SYSTEM_USER_ID` 來存取系統級的設定。
    """
    set_user_metadata(SYSTEM_USER_ID, **kwargs)