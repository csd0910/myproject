"""
utils.py - TaskMining Server 共通ユーティリティ
====================================================
役割:
  - 日時文字列 → Unixタイムスタンプ変換
  - ユーザーID解決 (UUID / 名前 / 匿名化)
  - 匿名化マッピング管理 (global_staff_map)
  - 管理者トークン定数

依存: database.get_connection, os, datetime
"""

import os
from datetime import datetime, timezone, timedelta
from database import get_connection

# ===========================
# 定数
# ===========================
JST = timezone(timedelta(hours=9))
ADMIN_TOKEN_SECRET = "super_secret_admin_token"

# ===========================
# 匿名化マッピング (メモリ上で保持)
# 同一UIDは常に同じ番号に対応させる
# ===========================
global_staff_map: dict[str, str] = {}
global_staff_counter: int = 1


# ===========================
# 日時ユーティリティ
# ===========================

def parse_datetime_to_timestamp(dt_str: str, default_val: float) -> float:
    """
    ISO8601形式の日時文字列をUnixタイムスタンプに変換する。
    タイムゾーン未指定の場合はJSTとして扱う。

    Args:
        dt_str: ISO8601形式の日時文字列 (例: "2026-08-14T09:00:00")
        default_val: 変換失敗時に返すデフォルト値

    Returns:
        Unixタイムスタンプ (float)
    """
    if not dt_str:
        return default_val
    try:
        dt_str = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=JST)
        return dt.timestamp()
    except Exception as e:
        print(f"[utils] Error parsing date '{dt_str}': {e}")
        return default_val


# ===========================
# ユーザーID解決
# ===========================

def resolve_user_id(user_id: str) -> "str | dict":
    """
    user_id文字列を実際のUUIDと名前の辞書に解決する。
    "ALL" または空文字の場合は "ALL" を返す。
    "Staff N" 形式の場合は global_staff_map からUUIDを逆引きする。

    Args:
        user_id: URLパラメータから受け取るユーザー識別子

    Returns:
        "ALL" または {"uuid": str, "name": str}
    """
    if not user_id or user_id == "ALL":
        return "ALL"

    global global_staff_map
    actual_name_or_id = user_id

    # "Staff N" → UUID 逆引き
    if user_id.startswith("Staff "):
        for uid, s_name in global_staff_map.items():
            if s_name == user_id:
                actual_name_or_id = uid
                break

    placeholder = "%s" if os.environ.get("DATABASE_URL") else "?"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT user_id, name FROM employees WHERE user_id = {placeholder} OR name = {placeholder}",
        (actual_name_or_id, actual_name_or_id)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return {"uuid": row[0], "name": row[1]}
    else:
        return {"uuid": actual_name_or_id, "name": actual_name_or_id}
