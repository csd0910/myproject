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
        
        total_sec += duration
        total_clicks += click_c
        total_scrolls += scroll_c
        total_mouse_distance += mouse_d
        total_context_switches += context_sw
        total_copy_paste += copy
        total_right_clicks += right_click
        total_shortcut_keys += shortcut_key
        total_manual_typing += manual
        
        if shortcut_details_str:
            try:
                import json
                parsed_details = json.loads(shortcut_details_str)
                for k, v in parsed_details.items():
                    total_shortcut_details[k] = total_shortcut_details.get(k, 0) + v
            except:
                pass
        
        is_meeting = "zoom" in app_lower or "teams" in app_lower or "meet" in app_lower or "meet" in title_lower or "zoom" in title_lower
        is_email = "outlook" in app_lower or "mail" in app_lower or "gmail" in title_lower or "mail" in title_lower or "outlook" in title_lower
        is_chat = "slack" in app_lower or "chatwork" in app_lower or "line" in app_lower or "slack" in title_lower or "chatwork" in title_lower or "line" in title_lower or ("teams" in title_lower and not is_meeting) or ("teams" in app_lower and not is_meeting)
        
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
                bottlenecks_map[file_name] = {"time": 0, "count": 0, "users": set(), "daily_counts": {}}
            bottlenecks_map[file_name]["time"] += duration
            bottlenecks_map[file_name]["count"] += (manual + copy)
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
        score = int((v["count"] / max(1, total_sec)) * v["count"] * (v["time"] / 60))
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
                "name": u, 
                "score_vs_avg": score,
                "total_sec": stats["total_sec"],
                "inefficient_sec": stats["inefficient_sec"],
                "rate": u_rate
            })
    
    kpi = {
        "member_count": len(users_set),
        "total_hours": round(total_sec / 3600, 1),
        "inefficient_hours": round(inefficient_sec / 3600, 1),
        "meeting_hours": round(work_breakdown_totals["Web会議"] / 3600, 1),
        "idle_hours": round(work_breakdown_totals["アイドル(操作なし)"] / 3600, 1),
        "ai_hours": round(work_breakdown_totals["AIツール操作"] / 3600, 2),
        "ai_minutes": round(work_breakdown_totals["AIツール操作"] / 60),
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
    
    query_files = "SELECT file_name, sum(duration_seconds), sum(manual_typing_count + copy_paste_count) FROM client_logs WHERE file_name IS NOT NULL AND file_name != '' "
    params = []
    if user_id != "ALL":
        query_files += f" AND user_id = {placeholder}"
        params.append(user_id)
        
    import dateutil.parser
    if start_date:
        query_files += f" AND received_at >= {placeholder}"
        try:
            params.append(dateutil.parser.parse(start_date).timestamp())
        except:
            params.append(0)
            
    if end_date:
        query_files += f" AND received_at <= {placeholder}"
        try:
            params.append(dateutil.parser.parse(end_date).timestamp())
        except:
            params.append(9999999999)
    query_files += " GROUP BY file_name ORDER BY sum(duration_seconds) DESC LIMIT 5"
    
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
    import dateutil.parser
    if start_date:
        timeline_query += f" AND received_at >= {placeholder}"
        try:
            timeline_params.append(dateutil.parser.parse(start_date).timestamp())
        except:
            timeline_params.append(0)
    if end_date:
        timeline_query += f" AND received_at <= {placeholder}"
        try:
            timeline_params.append(dateutil.parser.parse(end_date).timestamp())
        except:
            timeline_params.append(9999999999)
    
    timeline_query += " ORDER BY received_at DESC LIMIT 50"
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
        SELECT l.operation_type, l.file_name, l.duration_seconds, l.manual_typing_count, l.copy_paste_count, l.app_name 
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
    
    【ログ概要】\n{summary}
    """
    
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    try:
        res = client.models.generate_content(model='gemini-3.5-flash', contents=prompt)
        return {"report": res.text.replace("```html", "").replace("```", "")}
    except Exception as e:
        return {"report": f"AI分析中にエラーが発生しました: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
