# -*- coding: utf-8 -*-
"""
🌲 Forest WorkFlow System - Flask API Backend (PostgreSQL版)
Flask + HTML/JS 構成。
Google Cloud SQL (PostgreSQL) を pg8000 で接続し、JSON APIとして返却します。
"""

import os
import json
import csv
import io
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, Response
import pg8000.dbapi

# ==========================================
# ⚙️ 設定値（定数）
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_HOST = "34.146.122.39"
DB_PORT = 5432
DB_NAME = "forest-workflow-app-001-database"
DB_USER = "postgres"
DB_PASS = "Forest0720@"

app = Flask(__name__, static_folder=".")
app.secret_key = "super_secret_key_for_forest_pg"


# ==========================================
# 🔌 DB接続ヘルパー
# ==========================================
def get_db():
    """毎リクエストごとに接続を取得（シンプルな逐次接続方式）"""
    return pg8000.dbapi.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        timeout=15
    )


def fetchall_as_dict(cursor):
    """カーソルの結果を辞書リストに変換する"""
    cols = [desc[0] for desc in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def fetchone_as_dict(cursor):
    """カーソルの結果を辞書1件に変換する"""
    cols = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip(cols, row))


# ==========================================
# ⚙️ 認証チェックデコレータ
# ==========================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            if request.path.startswith('/api/'):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


# ==========================================
# 📄 ルーティング (HTML/CSS/JS静的ファイル配信)
# ==========================================
@app.route('/')
def index():
    if 'email' not in session:
        return redirect(url_for('login_page'))
    return send_from_directory(".", "index.html")


@app.route('/login')
def login_page():
    if 'email' in session:
        return redirect(url_for('index'))
    return """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
      <meta charset="UTF-8">
      <title>Forest WF - ログイン</title>
      <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    </head>
    <body class="bg-slate-900 text-slate-100 h-screen flex items-center justify-center">
      <div class="bg-white text-slate-800 p-8 rounded-2xl shadow-2xl max-w-sm w-full text-center">
        <span class="text-4xl">🌲</span>
        <h2 class="text-xl font-black mt-4 mb-1">Forest WorkFlow</h2>
        <p class="text-xs text-slate-400 mb-6">メールアドレスでログイン</p>

        <form action="/auth/login" method="POST" class="space-y-4">
          <input type="email" name="email" required placeholder="メールアドレス"
                 class="w-full border p-2.5 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500">
          <button type="submit"
                  style="background-color: #1e293b; color: #ffffff; width: 100%; font-weight: bold; padding: 10px; border-radius: 8px; font-size: 14px; cursor: pointer; border: none; display: block;"
                  onmouseover="this.style.backgroundColor='#0f172a'"
                  onmouseout="this.style.backgroundColor='#1e293b'">
            ログイン
          </button>
        </form>

        <div class="mt-6 border-t pt-4 text-left">
          <p class="text-[10px] text-slate-500 font-bold mb-1">【接続先】</p>
          <p class="text-[9px] text-slate-400 leading-relaxed">
            Google Cloud SQL (PostgreSQL) に接続しています。
          </p>
        </div>
      </div>
    </body>
    </html>
    """


@app.route('/auth/login', methods=['POST'])
def auth_login():
    email = request.form.get('email', '').strip().lower()
    if not email:
        return "メールアドレスを入力してください", 400

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT email, name FROM users WHERE email = %s", (email,))
        user = fetchone_as_dict(cur)

        if user is None:
            # DBに存在しない場合は自動登録（開発・テスト用）
            default_name = email.split('@')[0].replace('.', ' ').title()
            cur.execute("""
                INSERT INTO users (email, name, dept, title, is_admin, is_allowed_user)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING;
            """, (email, default_name, "システム統括部", "管理者", True, True))
            conn.commit()

        session['email'] = email
        return redirect(url_for('index'))
    except Exception as e:
        return f"ログインエラー: {e}", 500
    finally:
        conn.close()


@app.route('/auth/logout')
def auth_logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(".", path)


# ==========================================
# 📡 JSON API エンドポイント
# ==========================================

# 1. ログイン中のユーザープロファイル取得
@app.route('/api/profile')
@login_required
def api_profile():
    email = session['email']
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT email, name, dept, title, is_admin FROM users WHERE email = %s", (email,))
        user = fetchone_as_dict(cur)
        if user:
            return jsonify({
                "email": user["email"],
                "name": user["name"],
                "dept": user["dept"],
                "title": user.get("title", ""),
                "isAdmin": bool(user["is_admin"])
            })
        return jsonify({"error": "User not found"}), 404
    finally:
        conn.close()


# 2. マスタデータのロード (Forms & Users)
@app.route('/api/initial-data')
@login_required
def api_initial_data():
    conn = get_db()
    try:
        cur = conn.cursor()

        # フォーム一覧
        cur.execute("SELECT id, name, description, folder_id, routes, sort_order FROM forms ORDER BY sort_order ASC NULLS LAST")
        forms_raw = fetchall_as_dict(cur)
        forms = []
        for f in forms_raw:
            routes_val = f.get("routes") or "[]"
            try:
                routes_parsed = json.loads(routes_val)
            except Exception:
                routes_parsed = []
            forms.append({
                "id": f["id"],
                "name": f["name"],
                "description": f.get("description", ""),
                "folderId": f.get("folder_id", ""),
                "routes": routes_parsed,
                "sortOrder": f.get("sort_order", 99)
            })

        # ユーザー一覧
        cur.execute("SELECT email, name, dept, title, is_admin, is_allowed_user FROM users ORDER BY name")
        users_raw = fetchall_as_dict(cur)
        users = []
        for u in users_raw:
            users.append({
                "email": u["email"],
                "name": u["name"],
                "dept": u.get("dept", ""),
                "title": u.get("title", ""),
                "isAdmin": bool(u.get("is_admin", False)),
                "isAllowedUser": bool(u.get("is_allowed_user", True))
            })

        return jsonify({"forms": forms, "users": users})
    finally:
        conn.close()


# 3. 申請一覧の取得
@app.route('/api/applications')
@login_required
def api_applications():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT app_number, form_name, title, applicant, applicant_email,
                   date, global_status, current_step, pdf_name, pdf_url, routes,
                   created_at
            FROM applications
            ORDER BY date DESC
            LIMIT 50
        """)
        apps_raw = fetchall_as_dict(cur)
        apps = []
        for a in apps_raw:
            routes_val = a.get("routes") or "[]"
            try:
                routes_parsed = json.loads(routes_val)
            except Exception:
                routes_parsed = []
            created_at = a.get("created_at")
            apps.append({
                "id": a["app_number"],
                "appNumber": a["app_number"],
                "formName": a["form_name"],
                "title": a["title"],
                "applicant": a["applicant"],
                "applicantEmail": a["applicant_email"],
                "date": a["date"],
                "globalStatus": a["global_status"],
                "currentStep": a["current_step"],
                "pdfName": a.get("pdf_name", ""),
                "pdfUrl": a.get("pdf_url", "#"),
                "routes": routes_parsed,
                "createdAt": {"seconds": int(created_at.timestamp())} if created_at else None
            })
        return jsonify(apps)
    finally:
        conn.close()


# 3.5 申請データのCSVエクスポート
@app.route('/api/applications/export-csv')
@login_required
def api_export_csv():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT app_number, form_name, title, applicant, date, global_status, current_step
            FROM applications
            ORDER BY date DESC
        """)
        apps = fetchall_as_dict(cur)

        output = io.StringIO()
        output.write('\ufeff')  # BOM（Excelで文字化けを防ぐ）
        writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["申請番号", "申請種別", "標題", "申請者", "申請日", "状況", "現在の工程"])
        for a in apps:
            writer.writerow([
                a.get("app_number", ""),
                a.get("form_name", ""),
                a.get("title", ""),
                a.get("applicant", ""),
                a.get("date", ""),
                a.get("global_status", ""),
                a.get("current_step", "")
            ])

        response = Response(output.getvalue(), mimetype='text/csv')
        response.headers.set("Content-Disposition", "attachment", filename="applications_export.csv")
        return response
    finally:
        conn.close()


# 4. 新規申請の提出
@app.route('/api/applications/submit', methods=['POST'])
@login_required
def api_submit_application():
    data = request.json
    form_id = data.get('formId')
    title = data.get('title')
    custom_routes = data.get('routes')

    if not title or not form_id:
        return jsonify({"error": "必須項目が不足しています"}), 400

    email = session['email']
    conn = get_db()
    try:
        cur = conn.cursor()

        # ユーザー情報取得
        cur.execute("SELECT name FROM users WHERE email = %s", (email,))
        user = fetchone_as_dict(cur)
        if not user:
            return jsonify({"error": "ユーザーが見つかりません"}), 404
        current_user_name = user["name"]

        # 申請番号発行（YYYYMMの後に3桁連番）
        cur.execute("SELECT COUNT(*) as cnt FROM applications")
        count_row = fetchone_as_dict(cur)
        apps_count = count_row["cnt"] if count_row else 0
        app_number = f"{datetime.now().strftime('%Y%m')}{int(apps_count):03d}"

        # ルート処理
        if custom_routes:
            custom_routes[0]['name'] = current_user_name
            custom_routes[0]['status'] = '承認'
            custom_routes[0]['comment'] = '起案しました'
            custom_routes[0]['time'] = datetime.now().strftime('%m/%d %H:%M')
            if len(custom_routes) > 1:
                custom_routes[1]['status'] = '進行中'

        routes_json = json.dumps(custom_routes or [], ensure_ascii=False)
        now_str = datetime.now().strftime('%Y/%m/%d %H:%M')
        current_step = 2 if custom_routes and len(custom_routes) > 1 else 1

        cur.execute("""
            INSERT INTO applications (
                app_number, form_name, title, applicant, applicant_email,
                date, global_status, current_step, pdf_name, pdf_url, routes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (app_number) DO NOTHING;
        """, (
            app_number,
            data.get('formName', '申請'),
            title,
            current_user_name,
            email,
            now_str,
            '進行中',
            current_step,
            data.get('pdfName', '未添付'),
            '#',
            routes_json
        ))
        conn.commit()
        return jsonify({"success": True, "appNumber": app_number})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# 5. 承認・差し戻し・却下のアクション処理
@app.route('/api/applications/action', methods=['POST'])
@login_required
def api_application_action():
    data = request.json
    app_number = data.get('appNumber')
    action_type = data.get('action')  # 'approve', 'return', 'reject'
    comment = data.get('comment', '')

    if not app_number or not action_type:
        return jsonify({"error": "パラメータ不足"}), 400

    email = session['email']
    conn = get_db()
    try:
        cur = conn.cursor()

        # ユーザー名取得
        cur.execute("SELECT name FROM users WHERE email = %s", (email,))
        user = fetchone_as_dict(cur)
        if not user:
            return jsonify({"error": "ユーザーが見つかりません"}), 404

        # 申請データ取得
        cur.execute("""
            SELECT app_number, global_status, current_step, routes
            FROM applications WHERE app_number = %s
        """, (app_number,))
        app_data = fetchone_as_dict(cur)
        if not app_data:
            return jsonify({"error": "申請データが見つかりません"}), 404

        if app_data["global_status"] != '進行中':
            return jsonify({"error": "ステータスが進行中ではありません"}), 400

        routes_val = app_data.get("routes") or "[]"
        try:
            routes = json.loads(routes_val)
        except Exception:
            routes = []

        current_step = app_data["current_step"]
        step_idx = next((i for i, r in enumerate(routes) if r.get('step') == current_step), None)
        if step_idx is None:
            return jsonify({"error": "現在の進行ステップが見つかりません"}), 400

        # アクション反映
        if action_type == 'approve':
            is_kessai = '決裁' in routes[step_idx].get('role', '')
            routes[step_idx]['status'] = '決裁' if is_kessai else '承認'
        elif action_type == 'return':
            routes[step_idx]['status'] = '差し戻し'
        elif action_type == 'reject':
            routes[step_idx]['status'] = '却下'

        routes[step_idx]['actionAt'] = datetime.now().strftime('%Y/%m/%d %H:%M')
        routes[step_idx]['comment'] = comment

        # 次ステータス計算
        if action_type == 'reject':
            new_global_status = '却下'
        elif action_type == 'return':
            new_global_status = '差し戻し'
            for i, r in enumerate(routes):
                if i == 0:
                    r['status'] = '承認'
                elif i == 1:
                    r['status'] = '進行中'
                else:
                    r['status'] = '未到達'
            current_step = 2
        else:  # approve
            if step_idx < len(routes) - 1:
                routes[step_idx + 1]['status'] = '進行中'
                current_step += 1
                new_global_status = '進行中'
            else:
                new_global_status = '決裁'

        routes_json = json.dumps(routes, ensure_ascii=False)
        cur.execute("""
            UPDATE applications
            SET global_status = %s, current_step = %s, routes = %s
            WHERE app_number = %s
        """, (new_global_status, current_step, routes_json, app_number))
        conn.commit()
        return jsonify({"success": True, "newStatus": new_global_status})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# 6. 管理者向け：フォームマスタの新規作成・更新
@app.route('/api/admin/forms/save', methods=['POST'])
@login_required
def api_admin_save_form():
    email = session['email']
    conn = get_db()
    try:
        cur = conn.cursor()

        cur.execute("SELECT is_admin FROM users WHERE email = %s", (email,))
        user = fetchone_as_dict(cur)
        if not user or not user.get("is_admin"):
            return jsonify({"error": "Forbidden"}), 403

        data = request.json
        form_id = data.get('id')
        form_name = data.get('name')
        description = data.get('description', '')
        routes = data.get('routes', [])

        if not form_id or not form_name:
            return jsonify({"error": "必須入力項目不足"}), 400

        routes_json = json.dumps(routes, ensure_ascii=False)
        cur.execute("""
            INSERT INTO forms (id, name, description, routes, sort_order)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                routes = EXCLUDED.routes,
                sort_order = EXCLUDED.sort_order;
        """, (form_id, form_name, description, routes_json, data.get('sortOrder', 99)))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


# 7. 管理者向け：フォームマスタの削除
@app.route('/api/admin/forms/delete/<form_id>', methods=['POST'])
@login_required
def api_admin_delete_form(form_id):
    email = session['email']
    conn = get_db()
    try:
        cur = conn.cursor()

        cur.execute("SELECT is_admin FROM users WHERE email = %s", (email,))
        user = fetchone_as_dict(cur)
        if not user or not user.get("is_admin"):
            return jsonify({"error": "Forbidden"}), 403

        cur.execute("DELETE FROM forms WHERE id = %s", (form_id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(port=8082, debug=True)
