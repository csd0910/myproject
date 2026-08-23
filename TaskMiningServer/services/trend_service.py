"""
services/trend_service.py - 個人・部門トレンド集計サービス
============================================================
役割:
  - client_logs (生データ) と client_logs_summary (圧縮済み) から
    日別の非効率操作回数を集計し、折れ線グラフ用データを返す

依存: database.get_connection, os, time, datetime
"""

import os
import time
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


def get_historical_trend(conn, user_id: str = "ALL", department: str = "ALL") -> dict:
    """
    直近60日分の生データと圧縮サマリを結合し、
    日別非効率操作（手入力＋コピペ）件数を返す。

    Args:
        conn:       DB接続オブジェクト (呼び出し元で管理・クローズすること)
        user_id:    特定ユーザーを絞り込む場合はUUID文字列、全体は "ALL"
        department: 部門絞り込みの場合は部門名文字列、全体は "ALL"

    Returns:
        {
            "period_labels":        ["08/01", "08/02", ...],  # 直近30日
            "cumulative_saved_min": [12, 8, 25, ...]          # 対応する件数
        }
    """
    cursor = conn.cursor()
    placeholder = "%s" if os.environ.get("DATABASE_URL") else "?"
    sixty_days_ago = time.time() - (60 * 24 * 3600)
    daily_inefficient: dict[str, int] = {}

    # ── 1. 生データ (client_logs) を集計 ──────────────────────────
    q_raw = (
        f"SELECT received_at, manual_typing_count, copy_paste_count "
        f"FROM client_logs WHERE received_at >= {placeholder}"
    )
    params_raw: list = [sixty_days_ago]

    if user_id != "ALL":
        q_raw += f" AND user_id = {placeholder}"
        params_raw.append(user_id)
    elif department != "ALL":
        q_raw += f" AND user_id IN (SELECT user_id FROM employees WHERE department = {placeholder})"
        params_raw.append(department)

    cursor.execute(q_raw, tuple(params_raw))
    for recv_at, man, copy in cursor.fetchall():
        if recv_at:
            day = datetime.fromtimestamp(recv_at, tz=JST).strftime('%Y-%m-%d')
            daily_inefficient[day] = daily_inefficient.get(day, 0) + (man or 0) + (copy or 0)

    # ── 2. 圧縮サマリ (client_logs_summary) を集計 ────────────────
    q_sum = (
        "SELECT record_date, SUM(manual_typing_count + copy_paste_count) "
        "FROM client_logs_summary WHERE 1=1"
    )
    params_sum: list = []

    if user_id != "ALL":
        q_sum += f" AND user_id = {placeholder}"
        params_sum.append(user_id)
    elif department != "ALL":
        q_sum += f" AND user_id IN (SELECT user_id FROM employees WHERE department = {placeholder})"
        params_sum.append(department)

    q_sum += " GROUP BY record_date"
    cursor.execute(q_sum, tuple(params_sum))
    for r_date, r_count in cursor.fetchall():
        day = r_date[:10] if isinstance(r_date, str) else r_date.strftime('%Y-%m-%d')
        daily_inefficient[day] = daily_inefficient.get(day, 0) + (r_count or 0)

    # ── 3. 直近30日に絞り込み、グラフ用データに整形 ──────────────
    sorted_days = sorted(daily_inefficient.items(), key=lambda x: x[0])
    recent_days = sorted_days[-30:]

    if recent_days:
        period_labels = [datetime.strptime(k, '%Y-%m-%d').strftime('%m/%d') for k, _ in recent_days]
        trend_data    = [v for _, v in recent_days]
    else:
        period_labels = ["データなし"]
        trend_data    = [0]

    return {
        "period_labels":        period_labels,
        "cumulative_saved_min": trend_data,
    }
