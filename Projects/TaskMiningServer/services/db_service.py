"""
services/db_service.py - DB保守サービス
=========================================
役割:
  - 古いログのロールアップ（圧縮・集計）
  - DB再構築
  - SQL直接実行（管理者専用）
  - DBフルダンプ

依存: database.get_connection, os, time
"""

import os
import time
from database import get_connection, init_db


def rollup_old_logs(days_old: int = 30) -> dict:
    """
    指定日数より古い詳細ログを1時間単位に集計し、
    client_logs_summary に保存後、元レコードを削除する。

    Args:
        days_old: 圧縮対象とする日数 (デフォルト30日)

    Returns:
        {"status": "success"|"error", "message": str}
    """
    conn = get_connection()
    cursor = conn.cursor()
    cutoff = time.time() - (days_old * 24 * 3600)
    is_postgres = bool(os.environ.get("DATABASE_URL"))

    try:
        if is_postgres:
            insert_sql = """
                INSERT INTO client_logs_summary (
                    user_id, app_name, operation_type,
                    manual_typing_count, copy_paste_count, click_count,
                    scroll_count, mouse_distance, right_click_count,
                    shortcut_key_count, duration_seconds, idle_time_seconds,
                    context_switch_count, record_date, record_hour
                )
                SELECT
                    user_id, app_name, operation_type,
                    SUM(manual_typing_count), SUM(copy_paste_count), SUM(click_count),
                    SUM(scroll_count), SUM(mouse_distance), SUM(right_click_count),
                    SUM(shortcut_key_count), SUM(duration_seconds), SUM(idle_time_seconds),
                    SUM(context_switch_count),
                    DATE(to_timestamp(received_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tokyo')),
                    EXTRACT(HOUR FROM to_timestamp(received_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tokyo'))::INTEGER
                FROM client_logs
                WHERE received_at < %s
                GROUP BY
                    user_id, app_name, operation_type,
                    DATE(to_timestamp(received_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tokyo')),
                    EXTRACT(HOUR FROM to_timestamp(received_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Tokyo'))::INTEGER
            """
            cursor.execute(insert_sql, (cutoff,))
            cursor.execute("DELETE FROM client_logs WHERE received_at < %s", (cutoff,))
        else:
            insert_sql = """
                INSERT INTO client_logs_summary (
                    user_id, app_name, operation_type,
                    manual_typing_count, copy_paste_count, click_count,
                    scroll_count, mouse_distance, right_click_count,
                    shortcut_key_count, duration_seconds, idle_time_seconds,
                    context_switch_count, record_date, record_hour
                )
                SELECT
                    user_id, app_name, operation_type,
                    SUM(manual_typing_count), SUM(copy_paste_count), SUM(click_count),
                    SUM(scroll_count), SUM(mouse_distance), SUM(right_click_count),
                    SUM(shortcut_key_count), SUM(duration_seconds), SUM(idle_time_seconds),
                    SUM(context_switch_count),
                    date(datetime(received_at, 'unixepoch', 'localtime')),
                    cast(strftime('%H', datetime(received_at, 'unixepoch', 'localtime')) as integer)
                FROM client_logs
                WHERE received_at < ?
                GROUP BY
                    user_id, app_name, operation_type,
                    date(datetime(received_at, 'unixepoch', 'localtime')),
                    cast(strftime('%H', datetime(received_at, 'unixepoch', 'localtime')) as integer)
            """
            cursor.execute(insert_sql, (cutoff,))
            cursor.execute("DELETE FROM client_logs WHERE received_at < ?", (cutoff,))

        deleted_count = cursor.rowcount
        conn.commit()
        return {"status": "success", "message": f"{deleted_count} rows aggregated and deleted."}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def clean_old_logs_by_count(max_rows: int = 50000) -> dict:
    """
    client_logsが max_rows を超えた場合、古いレコードを削除する。

    Args:
        max_rows: 保持する最大行数 (デフォルト50000)

    Returns:
        {"status": str, "deleted": int, "remaining": int}
    """
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = "%s" if os.environ.get("DATABASE_URL") else "?"
    try:
        cursor.execute("SELECT COUNT(*) FROM client_logs")
        total = cursor.fetchone()[0]
        deleted = 0
        if total > max_rows:
            excess = total - max_rows
            if os.environ.get("DATABASE_URL"):
                cursor.execute(
                    "DELETE FROM client_logs WHERE id IN (SELECT id FROM client_logs ORDER BY received_at ASC LIMIT %s)",
                    (excess,)
                )
            else:
                cursor.execute(
                    "DELETE FROM client_logs WHERE rowid IN (SELECT rowid FROM client_logs ORDER BY received_at ASC LIMIT ?)",
                    (excess,)
                )
            deleted = cursor.rowcount
            conn.commit()
        return {"status": "ok", "deleted": deleted, "remaining": total - deleted}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def rebuild_database() -> dict:
    """
    client_logs・employeesテーブルをDROPし、init_dbで再構築する。
    【警告】全データが失われます。管理者のみ実行可。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS client_logs")
    cursor.execute("DROP TABLE IF EXISTS employees")
    conn.commit()
    conn.close()
    init_db()
    return {"status": "rebuilt"}


def dump_all_data() -> dict:
    """
    client_logs・client_logs_summary・employeesの全データを返す（デバッグ用）。
    """
    conn = get_connection()
    cursor = conn.cursor()

    def fetch_table(name: str) -> list[dict]:
        try:
            cursor.execute(f"SELECT * FROM {name} LIMIT 500")
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except Exception as e:
            return [{"error": str(e)}]

    result = {
        "client_logs":         fetch_table("client_logs"),
        "client_logs_summary": fetch_table("client_logs_summary"),
        "employees":           fetch_table("employees"),
    }
    conn.close()
    return result
