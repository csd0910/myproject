"""
routers/dashboard.py - ダッシュボード用APIルーター
"""
from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse, StreamingResponse
import os
import io
import csv
import json
import random
import time
from datetime import datetime
from database import get_connection
import utils
from utils import ADMIN_TOKEN_SECRET, resolve_user_id, parse_datetime_to_timestamp, global_staff_map, global_staff_counter
from services.trend_service import get_historical_trend
from google import genai

router = APIRouter(tags=['Dashboard'])

@router.get("/api/dashboard/export_csv")
async def export_csv(user_id: str = "ALL", start_date: str = None, end_date: str = None, department: str = "ALL", x_admin_token: str = Header(None, alias="X-Admin-Token")):
    is_admin = (x_admin_token == f"Bearer {ADMIN_TOKEN_SECRET}")
    
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT c.user_id, c.app_name, c.operation_type, c.file_name, c.manual_typing_count, 
               c.copy_paste_count, c.duration_seconds, c.received_at, e.name, e.department
        FROM client_logs c
        LEFT JOIN employees e ON c.user_id = e.user_id
        WHERE 1=1
    """
    params = []
    
    resolved = resolve_user_id(user_id)
    if resolved != "ALL" and resolved:
        placeholder = "%s" if os.environ.get("DATABASE_URL") else "?"
        query += f" AND (c.user_id = {placeholder} OR e.name = {placeholder})"
        params.extend([resolved["uuid"], resolved["name"]])
        
    if department != "ALL" and department:
        query += " AND e.department = " + ("%s" if os.environ.get("DATABASE_URL") else "?")
        params.append(department)
        
    if start_date:
        query += " AND c.received_at >= " + ("%s" if os.environ.get("DATABASE_URL") else "?")
        params.append(parse_datetime_to_timestamp(start_date, 0))
    if end_date:
        query += " AND c.received_at <= " + ("%s" if os.environ.get("DATABASE_URL") else "?")
        params.append(parse_datetime_to_timestamp(end_date, 9999999999))
        
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(["日時", "部門", "担当者", "アプリ名", "操作種別", "ファイル/画面名", "手入力回数", "コピペ回数", "所要時間(秒)", "非効率フラグ"])

    
    for row in rows:
        uid, app, op, file_name, manual, copy, duration, recv, emp_name, emp_dept = row
        
        # 匿名化処理
        display_name = emp_name if (is_admin and emp_name) else utils.global_staff_map.setdefault(uid, f"Staff {len(utils.global_staff_map)+1}")
        dt_str = datetime.fromtimestamp(recv).strftime('%Y-%m-%d %H:%M:%S')
        is_inefficient = "Yes" if (manual > 0 or copy > 0) else "No"
        dept_str = emp_dept if emp_dept else "不明"
        
        writer.writerow([dt_str, dept_str, display_name, app, op, file_name, manual, copy, duration, is_inefficient])
        
    output.seek(0)
    
    # BOM付きUTF-8（Excelで文字化けしないように）
    encoded_csv = "\ufeff" + output.getvalue()
    return StreamingResponse(
        iter([encoded_csv]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=taskmining_report.csv"}
    )

@router.get("/api/dashboard/data")
async def get_dashboard_data(user_id: str = "ALL", start_date: str = None, end_date: str = None, department: str = "ALL", x_admin_token: str = Header(None, alias="X-Admin-Token")):
    is_admin = (x_admin_token == f"Bearer {ADMIN_TOKEN_SECRET}")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT c.user_id, c.app_name, c.operation_type, c.file_name, c.cpu_usage_percent, 
               c.manual_typing_count, c.copy_paste_count, c.duration_seconds, c.received_at,
               e.name, e.department, 0 as idle_time_seconds,
               c.click_count, c.scroll_count, c.mouse_distance, c.context_switch_count,
               c.right_click_count, c.shortcut_key_count, c.shortcut_details
        FROM client_logs c
        LEFT JOIN employees e ON c.user_id = e.user_id
        WHERE c.user_id != 'anonymous_user'
    """
    params = []
    
    resolved = resolve_user_id(user_id)
    if resolved != "ALL" and resolved:
        placeholder = "%s" if os.environ.get("DATABASE_URL") else "?"
        query += f" AND (c.user_id = {placeholder} OR e.name = {placeholder})"
        params.extend([resolved["uuid"], resolved["name"]])
        
    if department != "ALL" and department:
        query += " AND e.department = " + ("%s" if os.environ.get("DATABASE_URL") else "?")
        params.append(department)
        
    if start_date:
        query += " AND c.received_at >= " + ("%s" if os.environ.get("DATABASE_URL") else "?")
        params.append(parse_datetime_to_timestamp(start_date, 0))
            
    if end_date:
        query += " AND c.received_at <= " + ("%s" if os.environ.get("DATABASE_URL") else "?")
        params.append(parse_datetime_to_timestamp(end_date, 9999999999))
        
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    

    apps = {}
    ops = {"手入力": 0, "コピー＆ペースト": 0, "閲覧": 0, "待機": 0}
    work_breakdown_totals = {"基幹業務": 0, "メール(外部連絡)": 0, "チャット(内部連絡)": 0, "Web会議": 0, "AIツール操作": 0, "アイドル(操作なし)": 0, "通常作業": 0}
    bottlenecks_map = {}
    users_set = set()
    total_sec = 0
    inefficient_sec = 0
    
    total_clicks = 0
    total_scrolls = 0
    total_mouse_distance = 0
    total_context_switches = 0
    total_copy_paste = 0
    total_right_clicks = 0
    total_shortcut_keys = 0
    total_manual_typing = 0
    total_focused_time = 0
    
    total_shortcut_details = {}
    
    scatter = []
    heatmap_data = {}
    member_stats = {}
    
    details = {
        "apps": {},
        "ops": {"手入力": {}, "コピー＆ペースト": {}, "閲覧": {}, "待機": {}, "基幹PC操作": {}},
        "work_breakdown": {"メール(外部連絡)": {}, "チャット(内部連絡)": {}, "Web会議": {}, "AIツール操作": {}, "基幹業務": {}, "アイドル(操作なし)": {}, "通常作業": {}}
    }
    
    
    import random
    from datetime import datetime
    
    for row in rows:
        # DBに追加したカラムがない場合は例外で落ちないようパディング処理
        if len(row) == 16:
            row = list(row) + [0, 0, "{}"]
        elif len(row) == 18:
            row = list(row) + ["{}"]
            
        uid, app_name, op_type, file_name, cpu, manual, copy, duration, recv, emp_name, emp_dept, idle_time, click_c, scroll_c, mouse_d, context_sw, right_click, shortcut_key, shortcut_details_str = row
        
        # 匿名化処理
        if is_admin and emp_name:
            display_name = emp_name
        else:
            if uid not in utils.global_staff_map:
                utils.global_staff_map[uid] = f"Staff {utils.global_staff_counter}"
                utils.global_staff_counter += 1
            display_name = utils.global_staff_map[uid]
            
        users_set.add(display_name)
        
        # None対策
        duration = duration or 0
        idle_time = idle_time or 0
        click_c = click_c or 0
        scroll_c = scroll_c or 0
        mouse_d = mouse_d or 0
        context_sw = context_sw or 0
        right_click = right_click or 0
        shortcut_key = shortcut_key or 0
        
        # 入力がない場合はアイドル状態とみなす
        if click_c == 0 and scroll_c == 0 and mouse_d == 0 and manual == 0 and copy == 0:
            idle_time = duration
        
        app_name = app_name or "Unknown"
        file_name = file_name or "Unknown"
        op_type = op_type or ""
        
        app_lower = app_name.lower()
        title_lower = file_name.lower()
        
        # 不要なシステムプロセスの除外
        if app_lower in ["lockapp.exe", "searchhost.exe"]:
            continue
            
        # アプリ名の正規化（Office製品など）
        if "powerpnt" in app_lower: app_name = "PowerPoint"
        elif "excel" in app_lower: app_name = "Excel"
        elif "winword" in app_lower: app_name = "Word"
        
        is_meeting = "zoom" in app_lower or "teams" in app_lower or "meet" in app_lower or "meet" in title_lower or "zoom" in title_lower
        is_email = "outlook" in app_lower or "mail" in app_lower or "gmail" in title_lower or "mail" in title_lower or "outlook" in title_lower
        is_chat = "slack" in app_lower or "chatwork" in app_lower or "line" in app_lower or "slack" in title_lower or "chatwork" in title_lower or "line" in title_lower or ("teams" in title_lower and not is_meeting) or ("teams" in app_lower and not is_meeting)
        
        total_sec += duration
        total_clicks += click_c
        total_scrolls += scroll_c
        total_mouse_distance += mouse_d
        total_context_switches += context_sw
        total_copy_paste += copy
        total_right_clicks += right_click
        total_shortcut_keys += shortcut_key
        total_manual_typing += manual
        
        # 集中時間の計算 (通常作業・基幹業務・AI操作など、チャット/メール/会議/アイドル以外)
        if not is_meeting and not is_email and not is_chat and duration > 0 and idle_time == 0:
            total_focused_time += duration
        
        if shortcut_details_str:
            try:
                import json
                parsed_details = json.loads(shortcut_details_str)
                for k, v in parsed_details.items():
                    total_shortcut_details[k] = total_shortcut_details.get(k, 0) + v
            except:
                pass
        
        is_ai = False
        if "chatgpt" in app_lower or "claude" in app_lower or "copilot" in app_lower or "gemini" in app_lower or "antigravity" in app_lower:
            is_ai = True
        elif "chatgpt" in title_lower or "claude" in title_lower or "copilot" in title_lower or "gemini" in title_lower or "antigravity" in title_lower:
            is_ai = True
            
        apps[app_name] = apps.get(app_name, 0) + duration
        
        op_lower = op_type.lower()
        
        current_op = "閲覧"
        if app_lower == "基幹システム(kvm)":
            current_op = "基幹PC操作"
        elif copy > 0 or "コピー" in op_type or "ペースト" in op_type or "copy" in op_lower or "paste" in op_lower:
            current_op = "コピー＆ペースト"
        elif manual > 0 or "手入力" in op_type or "keyboard" in op_lower or "type" in op_lower or "key" in op_lower:
            current_op = "手入力"
        elif click_c == 0 and scroll_c == 0 and mouse_d == 0 and manual == 0 and copy == 0:
            current_op = "待機"
            
        ops[current_op] = ops.get(current_op, 0) + duration
        
        # 詳細集計 (apps)
        if app_name not in details["apps"]: details["apps"][app_name] = {}
        details["apps"][app_name][file_name] = details["apps"][app_name].get(file_name, 0) + duration
        
        # 詳細集計 (ops)
        details["ops"][current_op][file_name] = details["ops"][current_op].get(file_name, 0) + duration
        
        # 詳細集計 (work_breakdown) と合計
        current_bd = "通常作業"
        if app_lower == "基幹システム(kvm)": current_bd = "基幹業務"
        elif is_meeting: current_bd = "Web会議"
        elif is_email: current_bd = "メール(外部連絡)"
        elif is_chat: current_bd = "チャット(内部連絡)"
        elif is_ai: current_bd = "AIツール操作"
        elif click_c == 0 and scroll_c == 0 and mouse_d == 0 and manual == 0 and copy == 0: current_bd = "アイドル(操作なし)"
        
        work_breakdown_totals[current_bd] = work_breakdown_totals.get(current_bd, 0) + duration
        details["work_breakdown"][current_bd][file_name] = details["work_breakdown"][current_bd].get(file_name, 0) + duration
        
        is_inefficient = (current_op in ["手入力", "コピー＆ペースト"])
        if is_inefficient:
            inefficient_sec += duration
        
        if file_name:
            if file_name not in bottlenecks_map:
                bottlenecks_map[file_name] = {
                    "time": 0, "count": 0, "users": set(), "daily_counts": {},
                    "clicks": 0, "right_clicks": 0, "mouse_dist": 0, "context_switches": 0
                }
            bottlenecks_map[file_name]["time"] += duration
            bottlenecks_map[file_name]["count"] += (manual + copy)
            bottlenecks_map[file_name]["clicks"] += click_c
            bottlenecks_map[file_name]["right_clicks"] += right_click
            bottlenecks_map[file_name]["mouse_dist"] += mouse_d
            bottlenecks_map[file_name]["context_switches"] += context_sw
            bottlenecks_map[file_name]["users"].add(display_name)
            if recv:
                dt = datetime.fromtimestamp(recv)
                date_str = dt.strftime('%Y-%m-%d')
                bottlenecks_map[file_name]["daily_counts"][date_str] = bottlenecks_map[file_name]["daily_counts"].get(date_str, 0) + (manual + copy)

        if display_name not in member_stats:
            member_stats[display_name] = {"total_sec": 0, "inefficient_sec": 0}
        member_stats[display_name]["total_sec"] += duration
        if is_inefficient:
            member_stats[display_name]["inefficient_sec"] += duration
            
        if recv:
            dt = datetime.fromtimestamp(recv)
            weekday_str = ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]
            hour_str = f"{dt.hour:02d}:00"
            hm_key = f"{weekday_str}_{hour_str}"
            if hm_key not in heatmap_data:
                heatmap_data[hm_key] = {"total_sec": 0, "inefficient_sec": 0}
            heatmap_data[hm_key]["total_sec"] += duration
            if is_inefficient:
                heatmap_data[hm_key]["inefficient_sec"] += duration

                
    # ボトルネックリストの成形
    bottlenecks = []
    for k, v in bottlenecks_map.items():
        base_score = (v["count"] / max(1, total_sec)) * v["count"] * (v["time"] / 60)
        right_click_rate = (v["right_clicks"] / v["clicks"]) if v["clicks"] > 0 else 0
        penalty = (v["context_switches"] * 2) + (right_click_rate * 50) + (v["mouse_dist"] / 10000)
        score = int(base_score + penalty)
        tool = "Excel VBA" if "Excel" in k else "Python" if score > 500 else "PowerShell"
        bottlenecks.append({
            "name": k,
            "time_min": int(v["time"] / 60),
            "manual_sec": v["time"],
            "forecast_sec": int(v["time"] * 0.2), # 自動化で80%削減想定
            "weekly_trend": [v["daily_counts"].get(d, 0) for d in sorted(v["daily_counts"].keys())[-7:]] if v["daily_counts"] else [],
            "count": v["count"],
            "member_count": len(v["users"]),
            "score": score,
            "tool": tool
        })
        
        # 散布図にはファイル単位の合計値を表示
        scatter.append({
            "x": v["time"],
            "y": v["count"],
            "file": k,
            "app": "各種アプリ",
            "op": "各種操作",
            "user": "複数メンバー" if len(v["users"]) > 1 else list(v["users"])[0]
        })
        
    bottlenecks = sorted(bottlenecks, key=lambda x: x["score"], reverse=True)[:10]
    
    # ヒートマップ（実データ計算）
    weekdays = ["月", "火", "水", "木", "金"]
    slots = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00"]
    heatmap = []
    for w in weekdays:
        for s in slots:
            hm_key = f"{w}_{s}"
            rate = 0
            if hm_key in heatmap_data and heatmap_data[hm_key]["total_sec"] > 0:
                rate = round(heatmap_data[hm_key]["inefficient_sec"] / heatmap_data[hm_key]["total_sec"], 2)
            heatmap.append({"weekday": w, "time_slot": s, "inefficient_rate": rate})
            
    # メンバー比較（実データ計算）
    members = []
    dept_totals = {"total_sec": 0, "inefficient_sec": 0, "member_count": len(member_stats), "avg_total_sec": 0, "avg_ineff_sec": 0, "avg_rate": 0}
    
    if len(member_stats) > 0:
        total_ineff = sum(m["inefficient_sec"] for m in member_stats.values())
        total_dur = sum(m["total_sec"] for m in member_stats.values())
        avg_rate = (total_ineff / total_dur) if total_dur > 0 else 0
        
        dept_totals["total_sec"] = total_dur
        dept_totals["inefficient_sec"] = total_ineff
        dept_totals["avg_total_sec"] = total_dur / len(member_stats)
        dept_totals["avg_ineff_sec"] = total_ineff / len(member_stats)
        dept_totals["avg_rate"] = avg_rate
        
        for u, stats in member_stats.items():
            u_rate = (stats["inefficient_sec"] / stats["total_sec"]) if stats["total_sec"] > 0 else 0
            score = int((u_rate - avg_rate) * 100) # 非効率度が高い（悪い）とプラス
            members.append({
                "score_vs_avg": score,
                "rate": u_rate
            })
    kpi = {
        "member_count": len(users_set),
        "total_hours": round(total_sec / 3600, 1),
        "inefficient_hours": round(inefficient_sec / 3600, 1),
        "meeting_hours": round(work_breakdown_totals["Web会議"] / 3600, 1),
        "idle_hours": round(work_breakdown_totals.get("アイドル(操作なし)", 0) / 3600, 1),
        "ai_hours": round(work_breakdown_totals["AIツール操作"] / 3600, 2),
        "ai_minutes": round(work_breakdown_totals["AIツール操作"] / 60),
        "total_focused_time": total_focused_time,
        "estimated_saved_hours": round((inefficient_sec / 3600) * 0.4 * 240, 1),
        "automation_candidates": len([b for b in bottlenecks if b["score"] > 100]),
        "total_clicks": total_clicks,
        "total_scrolls": total_scrolls,
        "total_mouse_distance": total_mouse_distance,
        "total_context_switches": total_context_switches,
        "total_copy_paste": total_copy_paste,
        "total_right_clicks": total_right_clicks,
        "total_shortcut_keys": total_shortcut_keys,
        "total_manual_typing": total_manual_typing,
        "total_loss_yen": int((inefficient_sec / 3600) * 2000), # 一律2000円/時で仮計算
        "shortcut_details": dict(sorted(total_shortcut_details.items(), key=lambda x: x[1], reverse=True)[:10]),
        "result_trend": get_historical_trend(conn, user_id="ALL", department=department)
    }
    conn.close()
    
    apps_sorted = dict(sorted(apps.items(), key=lambda item: item[1], reverse=True)[:5])
    
    # detailsの整形 (上位10件のみ)
    for cat in details:
        for key in details[cat]:
            sorted_files = sorted(details[cat][key].items(), key=lambda x: x[1], reverse=True)[:10]
            details[cat][key] = [{"file": k or "Unknown", "duration": v} for k, v in sorted_files]
    
    return {
        "kpi": kpi,
        "apps": apps_sorted,
        "ops": ops,
        "heatmap": heatmap,
        "bottlenecks": bottlenecks,
        "members": members,
        "dept_totals": dept_totals,
        "work_breakdown": work_breakdown_totals,
        "scatter": scatter,
        "details": details
    }

@router.get("/api/dashboard/user_data")
async def get_user_data(user_id: str = "ALL", start_date: str = None, end_date: str = None):
    resolved = resolve_user_id(user_id)
    conn = get_connection()
    cursor = conn.cursor()
    
    # ユーザー部門を取得
    department = "ALL"
    placeholder = "%s" if os.environ.get("DATABASE_URL") else "?"
    if user_id != "ALL":
        cursor.execute(f"SELECT department FROM employees WHERE user_id = {placeholder}", (user_id,))
        dept_row = cursor.fetchone()
        if dept_row:
            department = dept_row[0]
            
    # トレンドの取得
    trend_res = get_historical_trend(conn, user_id=user_id, department=department)
    
    
    benchmarks = {
        "my_shortcut_rate": 0,
        "my_rightclick_rate": 0,
        "my_switch_per_hr": 0,
        "avg_shortcut_rate": 0,
        "avg_rightclick_rate": 0,
        "avg_switch_per_hr": 0,
        "top_shortcut_rate": 0,
        "top_rightclick_rate": 0,
        "top_switch_per_hr": 0
    }
    
    # 過去7日間の自分の平均を計算
    if trend_res and "shortcut_rate" in trend_res and len(trend_res["shortcut_rate"]) > 0:
        benchmarks["avg_shortcut_rate"] = round(sum(trend_res["shortcut_rate"]) / len(trend_res["shortcut_rate"]), 1)
        
    query_files = "SELECT file_name, sum(duration_seconds), sum(manual_typing_count + copy_paste_count) FROM client_logs WHERE file_name IS NOT NULL AND file_name != '' "
    params = []
    if user_id != "ALL":
        query_files += f" AND user_id = {placeholder}"
        params.append(user_id)
        
    if start_date:
        query_files += f" AND received_at >= {placeholder}"
        params.append(parse_datetime_to_timestamp(start_date, 0))
    if end_date:
        query_files += f" AND received_at <= {placeholder}"
        params.append(parse_datetime_to_timestamp(end_date, 9999999999))
    query_files += " GROUP BY file_name ORDER BY sum(duration_seconds) DESC LIMIT 30"
    
    cursor.execute(query_files, tuple(params))
    top_files = cursor.fetchall()
    
    dynamic_flows = {
        "all": {
            "label": "全体フロー (すべて)",
            "manual": "graph TD\n A[\"作業開始\"] --> B[\"各種ファイルの検索・展開\"]\n B --> C[\"手動でのデータ転記・入力\"]\n C --> D[\"作業終了\"]",
            "auto": "graph TD\n A[\"自動トリガー開始\"] --> B[\"関連ファイルを自動取得・展開\"]\n B --> C[\"スクリプトによる一括データ処理\"]\n C --> D[\"自動保存・終了\"]"
        }
    }
    
    for i, row in enumerate(top_files):
        fname, dur, ops = row
        dur = dur or 0
        
        # ファイルごとの主要なアプリと操作を取得
        q_steps = f"SELECT app_name, operation_type, SUM(duration_seconds) FROM client_logs WHERE file_name = {placeholder} "
        q_params = [fname]
        if resolved != "ALL" and user_id != "CURRENT_USER" and resolved:
            q_steps += f" AND (user_id = {placeholder} OR user_id IN (SELECT user_id FROM employees WHERE name = {placeholder}))"
            q_params.extend([resolved["uuid"], resolved["name"]])
        if start_date:
            q_steps += f" AND received_at >= {placeholder}"
            q_params.append(parse_datetime_to_timestamp(start_date, 0))
        if end_date:
            q_steps += f" AND received_at <= {placeholder}"
            q_params.append(parse_datetime_to_timestamp(end_date, 9999999999))
            
        q_steps += " GROUP BY app_name, operation_type ORDER BY SUM(duration_seconds) DESC LIMIT 4"
        
        cursor.execute(q_steps, tuple(q_params))
        steps = cursor.fetchall()
        
        manual_flow = "graph TD\n A[\"作業開始\"]"
        auto_flow = "graph TD\n A[\"スクリプト自動起動\"]"
        
        last_node = "A"
        for idx, step in enumerate(steps):
            app = (step[0] or "アプリ").replace('"', '').replace('\n', ' ')
            op = (step[1] or "操作").replace('"', '').replace('\n', ' ')
            
            app_clean = app.replace('.EXE', '').replace('.exe', '').capitalize()
            op_clean = op
            op_lower = op_clean.lower()
            if "macro" in op_lower or "script" in op_lower:
                op_clean = "定型作業"
            elif "copy" in op_lower or "paste" in op_lower or "コピペ" in op_lower:
                op_clean = "転記・コピペ"
            elif "type" in op_lower or "手入力" in op_lower:
                op_clean = "手動入力"
            elif "read" in op_lower or "view" in op_lower or "閲覧" in op_lower:
                op_clean = "内容の確認・閲覧"
                
            if len(app_clean) > 12: app_clean = app_clean[:12] + "..."
            if len(op_clean) > 12: op_clean = op_clean[:12] + "..."
            
            dur_step = step[2] or 0
            time_str = f"{int(dur_step/60)}分{dur_step%60}秒" if dur_step >= 60 else f"{dur_step}秒"
            
            node_id = chr(66 + idx) # B, C, D...
            manual_flow += f" -->|{time_str}| {node_id}[\"{app_clean} を使用<br>して {op_clean}\"]"
            auto_flow += f" -->|自動化| {node_id}[\"{app_clean} 連携<br>で一括処理\"]"
            last_node = node_id
            
        manual_flow += f" --> Z[\"完了 (手作業: 約{int(dur/60)}分)\"]"
        auto_flow += f" --> Z[\"完了 (自動: 数秒)\"]"
        
        dynamic_flows[fname] = {
            "label": fname[:20] + ("..." if len(fname)>20 else ""),
            "manual": manual_flow,
            "auto": auto_flow
        }
        
    timeline_query = f"SELECT app_name, file_name, operation_type, duration_seconds, received_at, manual_typing_count, copy_paste_count FROM client_logs WHERE duration_seconds > 0 "
    timeline_params = []
    if resolved != "ALL" and user_id != "CURRENT_USER" and resolved:
        timeline_query += f" AND (user_id = {placeholder} OR user_id IN (SELECT user_id FROM employees WHERE name = {placeholder}))"
        timeline_params.extend([resolved["uuid"], resolved["name"]])
    if start_date:
        timeline_query += f" AND received_at >= {placeholder}"
        timeline_params.append(parse_datetime_to_timestamp(start_date, 0))
    if end_date:
        timeline_query += f" AND received_at <= {placeholder}"
        timeline_params.append(parse_datetime_to_timestamp(end_date, 9999999999))
    
    timeline_query += " ORDER BY received_at DESC LIMIT 300"
    cursor.execute(timeline_query, tuple(timeline_params))
    raw_timeline = cursor.fetchall()
    
    raw_timeline.reverse() 
    
    raw_timeline_data = []
    current_block = None
    
    for row in raw_timeline:
        t_app, t_file, t_op, t_dur, t_recv, t_man, t_copy = row
        t_dur = t_dur or 0
        t_man = t_man or 0
        t_copy = t_copy or 0
        
        if current_block and current_block['app'] == t_app and current_block['file'] == t_file:
            current_block['duration_sec'] += t_dur
            current_block['end_recv'] = t_recv
            current_block['man'] += t_man
            current_block['copy'] += t_copy
            if t_op and t_op not in current_block['ops']:
                current_block['ops'].append(t_op)
        else:
            if current_block:
                raw_timeline_data.append(current_block)
            current_block = {
                'app': t_app,
                'file': t_file,
                'ops': [t_op] if t_op else [],
                'duration_sec': t_dur,
                'start_recv': max(0, t_recv - t_dur),
                'end_recv': t_recv,
                'man': t_man,
                'copy': t_copy
            }
            
    if current_block:
        raw_timeline_data.append(current_block)

    timeline_data = []
    for b in raw_timeline_data:
        start_dt = datetime.fromtimestamp(b['start_recv'])
        end_dt = datetime.fromtimestamp(b['end_recv'])
        
        is_ineff = b['man'] > 0 or b['copy'] > 0
        app_clean = (b['app'] or "不明").replace('.EXE', '').replace('.exe', '').capitalize()
        ops_str = "、".join(b['ops'])
        desc = f"【要約】{app_clean} を使用し、{b['file'] or '名称未設定ファイル'} での作業 ({ops_str})"
        if is_ineff:
            desc += f" ⚠️手入力{b['man']}回 / コピペ{b['copy']}回の単純作業を検出"
            
        timeline_data.append({
            "start": start_dt.strftime("%H:%M:%S"),
            "end": end_dt.strftime("%H:%M:%S"),
            "duration_sec": b['duration_sec'],
            "app": app_clean,
            "file": b['file'] or "",
            "description": desc,
            "inefficient_flag": is_ineff
        })
        
    conn.close()

    forecast_steps = []
    for row in top_files:
        fname, dur, ops = row
        dur = dur or 0
        step_name = (fname or "不明")[:10]
        forecast_steps.append({
            "step_name": step_name,
            "manual_sec": dur,
            "forecast_sec": max(5, int(dur * 0.2))
        })
    if not forecast_steps:
        forecast_steps = [{"step_name": "データなし", "manual_sec": 0, "forecast_sec": 0}]

    return {
        "benchmarks": benchmarks,
        "timeline": timeline_data,
        "forecast_steps": forecast_steps,
        "result_trend": trend_res,
        "automation_steps": [
            { "title": "データ収集とファイル整理の自動化", "tool": "Python / PowerShell", "reason": "社内ネットワークとローカルPC間のファイル走査・移動を一元管理するため", "before_after": "現状1分11秒 → 自動化後10秒" }
        ],
        "kpi_extra": {
            "meeting_hours": 2.5,
            "idle_hours": 1.2
        },
        "dynamic_flows": dynamic_flows
    }

@router.post("/api/dashboard/analyze")
async def analyze_dashboard_data(
    user_id: str = "ALL",
    start_date: str = None,
    end_date: str = None,
    department: str = "ALL",
    file_name: str = None
):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT l.operation_type, l.file_name, l.duration_seconds, l.manual_typing_count, l.copy_paste_count, l.app_name, l.click_count, l.right_click_count, l.context_switch_count
        FROM client_logs l
        LEFT JOIN employees e ON l.user_id = e.user_id
        WHERE 1=1
    """
    params = []
    
    placeholder = "%s" if os.environ.get("DATABASE_URL") else "?"
    
    resolved = resolve_user_id(user_id)
    if resolved != "ALL" and user_id != "CURRENT_USER" and resolved:
        query += f" AND (l.user_id = {placeholder} OR e.name = {placeholder})"
        params.extend([resolved["uuid"], resolved["name"]])
    if department != "ALL":
        query += f" AND e.department = {placeholder}"
        params.append(department)
    if start_date:
        query += f" AND l.received_at >= {placeholder}"
        params.append(parse_datetime_to_timestamp(start_date, 0))
    if end_date:
        query += f" AND l.received_at <= {placeholder}"
        params.append(parse_datetime_to_timestamp(end_date, 9999999999))
    if file_name and file_name != "all":
        query += f" AND l.file_name = {placeholder}"
        params.append(file_name)
        
    query += " ORDER BY duration_seconds DESC LIMIT 50"
    
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    
    summary = f"対象: {user_id}\n合計 {len(rows)} 件のサンプルログデータ\n" + str(rows)
    
    if user_id != "ALL":
        prompt = f"""
        あなたはユーザーをサポートする優しいアシスタントです。以下のPC操作ログ概要を読み、今日のユーザーの頑張りを労いつつ、業務フローの改善策を提案してください。
        【必須要件】
        1. トーン＆マナー: 「ご担当者様」のような監査報告書・評価的な文体は絶対に避け、「お疲れ様です！今日のあなたは〜」といった一人称・語りかけ調（親しみやすくサポートするトーン）にすること。
        2. RPAやPowerQueryは禁止。Python, Excel VBA, GAS, PowerShellのいずれかを提案すること。
        3. 自動化優先度スコアが高いものを抽出し、以下のタグをつけて提案すること。
           - Excel内完結の定型転記 → 【VBA】
           - Googleフォーム/スプレッドシート連携 → 【GAS】
           - PC操作の自動化・ファイル整理・監視系 → 【PowerShell】
           - 複数システムを跨ぐ分析・レポート自動生成 → 【Python】
        4. 各個人の具体的なミクロの作業（現状）と、効率化後のフローを比較し、各工程ごとの「短縮時間」を明記したHTMLベースの視覚的なフローチャート（矢印やカード形式）を出力すること。
        5. 【超重要】出力するHTMLの各タグ行の先頭には、絶対にスペースやタブのインデントを付けないでください（Markdownのコードブロックとしてパースされるのを防ぐためです）。また、```html などの装飾も一切含めないでください。行頭は必ず < 記号から始まるようにしてください。
        6. 【超重要】入力されたクリック数、右クリック数、画面切替数などの生データを**絶対にそのまま出力しないでください**。「右クリックが多い」といった具体的な数値への言及は避け、代わりに「ショートカットキーの活用でさらに楽になりますよ」といったポジティブで定性的な行動変容の提案に変換してください。
        
        【ログ概要】\n{summary}
        """
    else:
        prompt = f"""
        あなたはDXコンサルタントです。以下のPC操作ログ概要を読み、現在の業務フローの改善策を提案してください。
        【必須要件】
        1. RPAやPowerQueryは禁止。Python, Excel VBA, GAS, PowerShellのいずれかを提案すること。
        2. 自動化優先度スコアが高いものを抽出し、以下のタグをつけて提案すること。
           - Excel内完結の定型転記 → 【VBA】
           - Googleフォーム/スプレッドシート連携 → 【GAS】
           - PC操作の自動化・ファイル整理・監視系 → 【PowerShell】
           - 複数システムを跨ぐ分析・レポート自動生成 → 【Python】
        3. 各個人の具体的なミクロの作業（現状）と、効率化後のフローを比較し、各工程ごとの「短縮時間」を明記したHTMLベースの視覚的なフローチャート（矢印やカード形式）を出力すること。
        4. 【超重要】効率化の効果や将来予測については、「〜になる」「確実に削減できる」といった断定的な表現を絶対に避け、「〜となる可能性があります」「〜を見込める推算です」といった、期待値を上げすぎない控えめな（濁した）表現を徹底すること。
        5. 【超重要】出力するHTMLの各タグ行の先頭には、絶対にスペースやタブのインデントを付けないでください（Markdownのコードブロックとしてパースされるのを防ぐためです）。また、```html などの装飾も一切含めないでください。行頭は必ず < 記号から始まるようにしてください。
        6. 【超重要】入力されたクリック数、右クリック数、画面切替数などの生データを**絶対にそのまま出力しないでください**。「右クリック〇〇回」といった監視的な報告は避け、これらを特徴量としてのみ解釈し、「ショートカット活用による時短」「コンテキストスイッチ（画面切替）の削減」といった定性的な業務プロセス改善の提案に変換してください。
        
        【ログ概要】\n{summary}
        """
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    try:
        res = client.models.generate_content(model='gemini-3.5-flash', contents=prompt)
        return {"report": res.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"report": f"AI分析中にエラーが発生しました: {str(e)}"}

@router.get("/api/dashboard/salary_status")
async def get_salary_status(user_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = "%s" if os.environ.get("DATABASE_URL") else "?"
    cursor.execute(f"SELECT base_salary FROM employees WHERE user_id = {placeholder}", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0] and row[0] > 0:
        return {"has_salary": True}
    return {"has_salary": False}

@router.post("/api/dashboard/set_salary")
async def set_salary(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    base_salary = int(data.get("base_salary", 0))
    # 20日稼働 * 8時間 = 160時間で時給計算
    hourly_wage = int(base_salary / 160) if base_salary > 0 else 0
    
    conn = get_connection()
    cursor = conn.cursor()
    placeholder = "%s" if os.environ.get("DATABASE_URL") else "?"
    cursor.execute(f"UPDATE employees SET base_salary = {placeholder}, hourly_wage = {placeholder} WHERE user_id = {placeholder}", 
                  (base_salary, hourly_wage, user_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@router.get("/api/dashboard/trend_data")
async def get_trend_data(
    user_id: str = "ALL",
    start_date: str = None,
    end_date: str = None,
    department: str = "ALL"
):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        from datetime import datetime, timezone, timedelta
        JST = timezone(timedelta(hours=9))
        
        # parse dates
        start_dt = datetime.strptime(start_date[:10], "%Y-%m-%d") if start_date else datetime.now() - timedelta(days=7)
        end_dt = datetime.strptime(end_date[:10], "%Y-%m-%d") if end_date else datetime.now()
        
        # Fetch ALL data in this range in one query
        day_start_ts = start_dt.replace(hour=0, minute=0, second=0).timestamp()
        day_end_ts = end_dt.replace(hour=23, minute=59, second=59).timestamp()
        
        q = """
            SELECT c.received_at, c.duration_seconds, c.manual_typing_count, c.copy_paste_count, 
                   c.shortcut_key_count, c.click_count, c.scroll_count, c.mouse_distance, c.context_switch_count, 
                   c.app_name, c.file_name, c.operation_type, c.right_click_count
            FROM client_logs c
            LEFT JOIN employees e ON c.user_id = e.user_id
            WHERE c.received_at >= %s AND c.received_at <= %s
        """ if os.environ.get("DATABASE_URL") else """
            SELECT c.received_at, c.duration_seconds, c.manual_typing_count, c.copy_paste_count, 
                   c.shortcut_key_count, c.click_count, c.scroll_count, c.mouse_distance, c.context_switch_count, 
                   c.app_name, c.file_name, c.operation_type, c.right_click_count
            FROM client_logs c
            LEFT JOIN employees e ON c.user_id = e.user_id
            WHERE c.received_at >= ? AND c.received_at <= ?
        """
        
        params = [day_start_ts, day_end_ts]
        
        if user_id != "ALL":
            q += " AND c.user_id = " + ("%s" if os.environ.get("DATABASE_URL") else "?")
            params.append(user_id)
        elif department != "ALL":
            q += " AND e.department = " + ("%s" if os.environ.get("DATABASE_URL") else "?")
            params.append(department)
            
        cursor.execute(q, tuple(params))
        rows = cursor.fetchall()
        
        # Group data by date
        from collections import defaultdict
        
        # Define structures
        daily_stats = {}
        days = (end_dt - start_dt).days + 1
        labels = []
        for i in range(days):
            current_dt = start_dt + timedelta(days=i)
            day_label = current_dt.strftime("%m/%d")
            labels.append(day_label)
            daily_stats[day_label] = {
                "dur": 0, "man": 0, "cpy": 0, "shortcut": 0, "clicks": 0,
                "scrolls": 0, "dist": 0, "switch": 0, "right": 0, "focused": 0,
                "apps": defaultdict(int),
                "work_breakdown": defaultdict(int)
            }
            
        app_total_hours = defaultdict(int)

        for row in rows:
            if len(row) == 13:
                recv, dur, man, cpy, shortcut, clicks, scrolls, dist, switch, app_name, file_name, op_type, right = row
            else:
                recv = row[0]
                dur = row[1] or 0
                man = row[2] or 0
                cpy = row[3] or 0
                shortcut = row[4] or 0
                clicks = row[5] or 0
                scrolls = row[6] or 0
                dist = row[7] or 0
                switch = row[8] or 0
                app_name = row[9]
                file_name = row[10]
                op_type = row[11]
                right = row[12] if len(row) > 12 else 0
                
            if not recv: continue
            
            dt = datetime.fromtimestamp(recv)
            day_label = dt.strftime("%m/%d")
            
            if day_label not in daily_stats:
                continue
                
            dur = dur or 0
            man = man or 0
            cpy = cpy or 0
            shortcut = shortcut or 0
            clicks = clicks or 0
            scrolls = scrolls or 0
            dist = dist or 0
            switch = switch or 0
            right = right or 0
            app_name = app_name or "Unknown"
            file_name = file_name or "Unknown"
            op_type = op_type or ""
            
            stats = daily_stats[day_label]
            stats["dur"] += dur
            stats["man"] += man
            stats["cpy"] += cpy
            stats["shortcut"] += shortcut
            stats["clicks"] += clicks
            stats["scrolls"] += scrolls
            stats["dist"] += dist
            stats["switch"] += switch
            stats["right"] += right
            
            app_lower = app_name.lower()
            title_lower = file_name.lower()
            
            if "powerpnt" in app_lower: app_name = "PowerPoint"
            elif "excel" in app_lower: app_name = "Excel"
            elif "winword" in app_lower: app_name = "Word"
            
            stats["apps"][app_name] += dur
            app_total_hours[app_name] += dur
            
            # Work Breakdown logic
            is_meeting = "zoom" in app_lower or "teams" in app_lower or "meet" in app_lower or "meet" in title_lower or "zoom" in title_lower
            is_email = "outlook" in app_lower or "mail" in app_lower or "gmail" in title_lower or "mail" in title_lower or "outlook" in title_lower
            is_chat = "slack" in app_lower or "chatwork" in app_lower or "line" in app_lower or "slack" in title_lower or "chatwork" in title_lower or "line" in title_lower or ("teams" in title_lower and not is_meeting) or ("teams" in app_lower and not is_meeting)
            
            is_ai = False
            if "chatgpt" in app_lower or "claude" in app_lower or "copilot" in app_lower or "gemini" in app_lower or "antigravity" in app_lower:
                is_ai = True
            elif "chatgpt" in title_lower or "claude" in title_lower or "copilot" in title_lower or "gemini" in title_lower or "antigravity" in title_lower:
                is_ai = True
                
            current_bd = "通常作業"
            if app_lower == "基幹システム(kvm)": current_bd = "基幹業務"
            elif is_meeting: current_bd = "Web会議"
            elif is_email: current_bd = "メール(外部連絡)"
            elif is_chat: current_bd = "チャット(内部連絡)"
            elif is_ai: current_bd = "AIツール操作"
            elif clicks == 0 and scrolls == 0 and dist == 0 and man == 0 and cpy == 0: current_bd = "アイドル(操作なし)"
            
            if clicks == 0 and scrolls == 0 and dist == 0 and man == 0 and cpy == 0:
                idle_time = dur
            else:
                idle_time = 0
                
            if not is_meeting and not is_email and not is_chat and dur > 0 and idle_time == 0:
                stats["focused"] += dur
                
            stats["work_breakdown"][current_bd] += dur

        # Find top 5 apps overall
        top_apps = [k for k, v in sorted(app_total_hours.items(), key=lambda x: x[1], reverse=True)[:5]]
        
        # Prepare arrays for frontend
        work_hours = []
        inefficient_time = []
        inefficient_ops = []
        ai_ratio = []
        manual_ratio = []
        shortcut_rate = []
        type_input = []
        type_copy = []
        type_view = []
        focused_time = []
        
        mouse_dist = []
        context_switches = []
        clicks_trend = []
        right_clicks_trend = []
        
        apps_trend = {app: [] for app in top_apps}
        apps_trend["その他"] = []
        
        bd_categories = ["基幹業務", "メール(外部連絡)", "チャット(内部連絡)", "Web会議", "AIツール操作", "アイドル(操作なし)", "通常作業"]
        breakdown_trend = {cat: [] for cat in bd_categories}
        
        for label in labels:
            stats = daily_stats[label]
            dur = stats["dur"]
            man = stats["man"]
            cpy = stats["cpy"]
            shortcut = stats["shortcut"]
            clicks = stats["clicks"]
            dist = stats["dist"]
            switch = stats["switch"]
            right = stats["right"]
            
            # Simple KPIs
            w_h = round(dur / 3600, 1)
            i_t = round((man + cpy) * 5 / 60, 1) # assumed 5 seconds per inefficient op
            
            work_hours.append(w_h)
            inefficient_time.append(i_t)
            inefficient_ops.append(man + cpy)
            focused_time.append(round(stats["focused"] / 3600, 1))
            
            # Mouse / Clicks
            mouse_dist.append(dist)
            context_switches.append(switch)
            clicks_trend.append(clicks)
            right_clicks_trend.append(right)
            
            # AI ratio simple calculation
            ai_dur = stats["work_breakdown"]["AIツール操作"]
            ai_r = round((ai_dur / max(1, dur)) * 100, 1) if dur > 0 else 0
            man_r = round(((dur - ai_dur) / max(1, dur)) * 100, 1) if dur > 0 else 0
            ai_ratio.append(ai_r)
            manual_ratio.append(man_r)
            
            # Shortcut rate
            s_rate = round((shortcut / max(1, clicks + shortcut + right)) * 100, 1) if (clicks + shortcut + right) > 0 else 0
            shortcut_rate.append(s_rate)
            
            # Type ratio (heuristic)
            total_ops = max(1, man + cpy + clicks)
            t_in = round(man / total_ops * 100, 1) if total_ops > 0 else 0
            t_cp = round(cpy / total_ops * 100, 1) if total_ops > 0 else 0
            t_vw = round(max(0, 100 - t_in - t_cp), 1) if total_ops > 0 else 0
            type_input.append(t_in)
            type_copy.append(t_cp)
            type_view.append(t_vw)
            
            # Apps
            other_app_dur = 0
            for app_name, app_dur in stats["apps"].items():
                if app_name in top_apps:
                    apps_trend[app_name].append(round(app_dur / 3600, 2))
                else:
                    other_app_dur += app_dur
                    
            for app in top_apps:
                if len(apps_trend[app]) < len(labels):
                    # In case the app wasn't in this day's dict at all, pad it
                    apps_trend[app].append(0)
            apps_trend["その他"].append(round(other_app_dur / 3600, 2))
            
            # Breakdown
            for cat in bd_categories:
                breakdown_trend[cat].append(round(stats["work_breakdown"].get(cat, 0) / 3600, 2))
                
        return {
            "labels": labels,
            "work_hours": work_hours,
            "focused_time": focused_time,
            "inefficient_time": inefficient_time,
            "inefficient_ops": inefficient_ops,
            "ai_ratio": ai_ratio,
            "manual_ratio": manual_ratio,
            "shortcut_rate": shortcut_rate,
            "type_input": type_input,
            "type_copy": type_copy,
            "type_view": type_view,
            "mouse_dist": mouse_dist,
            "context_switches": context_switches,
            "clicks_trend": clicks_trend,
            "right_clicks_trend": right_clicks_trend,
            "apps_trend": apps_trend,
            "breakdown_trend": breakdown_trend,
            "top_apps": top_apps
        }
        
    except Exception as e:
        print(f"Error generating trend data: {e}")
        return {
            "labels": []
        }
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
