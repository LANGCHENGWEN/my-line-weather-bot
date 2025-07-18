# user_data_manager.py
import json
import sqlite3
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 建立資料庫檔案與資料表
DB_PATH = Path("user_data.db")
conn = sqlite3.connect(DB_PATH)
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

# ---------- 工具 ----------
def _get(conn: sqlite3.Connection, col: str, user_id: str) -> Any:
    """從資料庫中獲取指定用戶的指定欄位值。"""
    cur = conn.execute(f"SELECT {col} FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None

def _upsert_cols(user_id: str, **cols: Any):
    """
    更新或插入用戶資料。
    如果用戶不存在則插入，否則更新指定欄位。
    """
    # keys, vals = zip(*cols.items())
    keys = list(cols.keys())
    vals = list(cols.values())

    # 構建 SET 語句用於 ON CONFLICT DO UPDATE
    sets = ", ".join(f"{k}=excluded.{k}" for k in keys)

    # 構建 VALUES 的佔位符
    placeholders = ", ".join(["?"] * len(keys))

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"""
            INSERT INTO users (user_id,{','.join(keys)})
            VALUES (?,{placeholders})
            ON CONFLICT(user_id) DO UPDATE SET {sets}
            """,
            (user_id, *vals), # user_id 和其他值
        )
        conn.commit()

# ---- 狀態管理 ----
def set_user_state(user_id: str, state: str, data: Dict[str, Any] = None):
    """
    設定指定使用者的狀態，並可儲存相關的額外數據。
    :param user_id: 使用者的 LINE ID。
    :param state: 要設定的新狀態字串。
    :param data: (可選) 與該狀態相關的額外數據，以字典形式儲存。
    """
    """
    logger.debug(f"Executing set_user_state: user_id={user_id}, state={state}")
    with sqlite3.connect(DB_PATH) as conn:
        _upsert_cols(user_id, state=state)
    logger.debug(f"After set_user_state, retrieved state: {get_user_state(user_id)}")
    """
    # 載入現有的 meta_json，以便合併新的 data
    current_meta_json = get_user_metadata(user_id, "all_meta", {}) # 獲取所有 metadata
    
    # 更新或設定 'state_data' 鍵，用於儲存與當前狀態相關的數據
    current_meta_json['state_data'] = data if data is not None else {}
    
    # 將更新後的 meta_json 轉換為字串
    meta_json_str = json.dumps(current_meta_json, ensure_ascii=False)

    _upsert_cols(user_id, state=state, meta_json=meta_json_str)
    logger.debug(f"已設定使用者狀態: user_id={user_id}, state={state}, data={data}")

def get_user_state(user_id: str) -> Dict[str, Any]:
    """
    取得指定使用者的當前狀態及其相關數據。
    :param user_id: 使用者的 LINE ID。
    :return: 包含 'state' 和 'data' 鍵的字典。如果沒有數據，'data' 為空字典。
             如果用戶不存在，返回 {'state': 'idle', 'data': {}}。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT state, meta_json FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()

        if row:
            state = row[0]
            meta_json_str = row[1]
            
            data_from_meta = {}
            if meta_json_str:
                try:
                    full_meta = json.loads(meta_json_str)
                    data_from_meta = full_meta.get('state_data', {}) # 從 'state_data' 鍵中獲取數據
                except json.JSONDecodeError:
                    logger.warning(f"用戶 {user_id} 的 meta_json 解析失敗，已重置。")
                    _upsert_cols(user_id, meta_json=None) # 清除錯誤的 JSON
            
            return {"state": state if state is not None else "idle", "data": data_from_meta}
        else:
            # 如果用戶不存在，返回預設狀態
            return {"state": "idle", "data": {}}

def clear_user_state(user_id: str) -> None:
    """清除指定使用者的狀態和相關數據。"""
    current_meta_json = get_user_metadata(user_id, "all_meta", {})
    if 'state_data' in current_meta_json:
        del current_meta_json['state_data']
    meta_json_str = json.dumps(current_meta_json, ensure_ascii=False)
    _upsert_cols(user_id, state=None, meta_json=meta_json_str)

# ---- 預設城市管理 ----
def save_default_city(user_id: str, city_name: str) -> None:
    """儲存指定使用者的預設城市。"""
    _upsert_cols(user_id, default_city=city_name)

def get_default_city(user_id: str) -> Optional[str]:
    with sqlite3.connect(DB_PATH) as conn:
        return _get(conn, "default_city", user_id)
    
# ---------- 任意 metadata ----------
def set_user_metadata(user_id: str, **kwargs: Any) -> None:
    """
    設定指定使用者的任意 metadata。
    會把 meta_json 轉成 dict 後 merge，再寫回。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur_json = _get(conn, "meta_json", user_id)
        meta: Dict[str, Any] = json.loads(cur_json) if cur_json else {}
        meta.update(kwargs)

    _upsert_cols(user_id, meta_json=json.dumps(meta, ensure_ascii=False))

def get_user_metadata(user_id: str, key: str, default: Any = None) -> Any:
    """
    獲取指定使用者的某個 metadata。
    如果 key 為 "all_meta"，則返回整個 metadata 字典。
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur_json = _get(conn, "meta_json", user_id)
    if not cur_json:
        return {} if key == "all_meta" else default # 如果沒有 meta_json，返回空字典給 all_meta
    try:
        full_meta = json.loads(cur_json)
        if key == "all_meta":
            return full_meta
        return full_meta.get(key, default)
    except json.JSONDecodeError:
        logger.warning(f"用戶 {user_id} 的 meta_json 解析失敗，已重置。")
        _upsert_cols(user_id, meta_json=None)
        return {} if key == "all_meta" else default

# ---- 驗證城市名稱 ----
def is_valid_city(city_name: str) -> bool:
    # 可改成讀取實際縣市資料庫或 API 驗證
    valid_cities = [
        "台北市", "新北市", "桃園市", "台中市", "台南市",
        "高雄市", "基隆市", "新竹市", "新竹縣", "苗栗縣",
        "彰化縣", "南投縣", "雲林縣", "嘉義市", "嘉義縣",
        "屏東縣", "宜蘭縣", "花蓮縣", "台東縣", "澎湖縣", "金門縣", "連江縣"
    ]
    return city_name in valid_cities