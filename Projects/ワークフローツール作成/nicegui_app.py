# -*- coding: utf-8 -*-
"""
🌲 Forest WorkFlow System - Flask API Backend
Flask + HTML/JS 構成で、ローディング時間とコードの可読性を大幅に向上させたシステム。
Firebase Admin SDK を経由してデータを取得し、ブラウザ（app.js）へJSON APIとして返却します。
"""

import os
os.environ["GRPC_DNS_RESOLVER"] = "native" # IPv6ハング回避

from flask import Flask, request, jsonify, render_template, send_from_directory, session, redirect, url_for
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

app = Flask(__name__, static_folder=".")
app.secret_key = "super_secret_key_for_forest"

# ==========================================
# 🔌 Firebase 初期化
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_KEY_PATH = os.path.join(BASE_DIR, "firebase_credential.json")

if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# ==========================================
# ⚙️ 認証チェックデコレータ
# ==========================================
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            return jsonify({"error": "Unauthorized"}), 401
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
        <p class="text-xs text-slate-400 mb-6">Google Workspace でログイン</p>
        
        <form action="/auth/login" method="POST" class="space-y-4">
          <input type="email" name="email" required placeholder="メールアドレス" class="w-full border p-2.5 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500">
          <button type="submit" 
                  style="background-color: #1e293b; color: #ffffff; width: 100%; font-weight: bold; padding: 10px; border-radius: 8px; font-size: 14px; cursor: pointer; border: none; display: block;"
                  onmouseover="this.style.backgroundColor='#0f172a'" 
                  onmouseout="this.style.backgroundColor='#1e293b'">
            Googleアカウントでログイン (Mock)
          </button>
        </form>
        
        <div class="mt-6 border-t pt-4 text-left">
          <p class="text-[10px] text-slate-500 font-bold mb-1">【本番環境（GWS連携）への切り替え方法】</p>
          <p class="text-[9px] text-slate-400 leading-relaxed">
            Google Cloud Console で OAuth クライアントID を発行し、クライアント認証情報を連携することで、本物の Google Workspace サインイン画面へ遷移させることができます。
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
    
    # ユーザー存在確認
    user_doc = db.collection("users").document(email).get()
    if not user_doc.exists:
        # テスト用に、Firestoreに存在しないアドレスの場合はデフォルトユーザーを自動作成して救済
        default_user = {
            "name": email.split('@')[0].replace('.', ' ').title(),
            "dept": "システム統括部",
            "title": "管理者",
            "isAdmin": True,
            "isAllowedUser": True
        }
        db.collection("users").document(email).set(default_user)
        
    session['email'] = email
    return redirect(url_for('index'))


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
    user_doc = db.collection("users").document(email).get()
    if user_doc.exists:
        data = user_doc.to_dict()
        return jsonify({
            "email": email,
            "name": data.get("name"),
            "dept": data.get("dept"),
            "title": data.get("title", ""),
            "isAdmin": data.get("isAdmin", False)
        })
    return jsonify({"error": "User not found"}), 404

# 2. マスタデータのロード (Forms & Users)
@app.route('/api/initial-data')
@login_required
def api_initial_data():
    forms_ref = db.collection("forms").stream()
    forms = [f.to_dict() | {"id": f.id} for f in forms_ref]
    forms = sorted(forms, key=lambda x: x.get("sortOrder", 999))
    
    users_ref = db.collection("users").stream()
    users = [u.to_dict() | {"email": u.id} for u in users_ref]
    
    return jsonify({
        "forms": forms,
        "users": users
    })

# 3. 申請一覧の取得 (定期的にポーリングされる想定)
@app.route('/api/applications')
@login_required
def api_applications():
    apps_ref = db.collection("applications").stream()
    apps = []
    for doc in apps_ref:
        app_data = doc.to_dict()
        app_data['id'] = doc.id
        # Convert Timestamp to dictionary compatible representation
        if 'createdAt' in app_data and hasattr(app_data['createdAt'], 'timestamp'):
            app_data['createdAt'] = {"seconds": int(app_data['createdAt'].timestamp())}
        apps.append(app_data)
    
    # 降順ソート
    apps = sorted(apps, key=lambda x: x.get('date', ''), reverse=True)
    return jsonify(apps[:50])


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
    user_doc = db.collection("users").document(email).get()
    current_user = user_doc.to_dict()
    
    # 申請番号発行
    apps_count = len(list(db.collection("applications").stream()))
    app_number = f"{datetime.now().strftime('%Y%m')}{apps_count:03d}"
    
    if custom_routes:
        # 起案ステップ（step 1）を「承認」として処理
        custom_routes[0]['name'] = current_user['name']
        custom_routes[0]['status'] = '承認'
        custom_routes[0]['comment'] = '起案しました'
        custom_routes[0]['time'] = datetime.now().strftime('%m/%d %H:%M')
        if len(custom_routes) > 1:
            custom_routes[1]['status'] = '進行中'
            
    doc_data = {
        "appNumber": app_number,
        "formName": data.get('formName', '申請'),
        "title": title,
        "applicant": current_user['name'],
        "applicantEmail": email,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "date": datetime.now().strftime('%Y/%m/%d %H:%M'),
        "globalStatus": "進行中",
        "currentStep": 2 if len(custom_routes) > 1 else 1,
        "pdfName": data.get('pdfName', '未添付'),
        "pdfUrl": "#",
        "routes": custom_routes
    }
    
    db.collection("applications").document(app_number).set(doc_data)
    return jsonify({"success": True, "appNumber": app_number})

# 5. 承認・差し戻し・却下のトランザクション処理
@firestore.transactional
def process_approval_transaction(transaction, app_ref, action_type, comment, current_user_name):
    snapshot = app_ref.get(transaction=transaction)
    if not snapshot.exists:
        raise Exception("申請データが見つかりません。")
        
    app_data = snapshot.to_dict()
    if app_data.get('globalStatus') != '進行中':
        raise Exception(f"ステータスが進行中ではありません。")
        
    routes = app_data.get('routes', [])
    current_step = app_data.get('currentStep', 1)
    
    step_idx = next((i for i, r in enumerate(routes) if r.get('step') == current_step), None)
    if step_idx is None:
        raise Exception("現在の進行ステップが見つかりません。")
        
    # アクションの反映
    if action_type == 'approve':
        is_kessai = '決裁' in routes[step_idx].get('role', '')
        routes[step_idx]['status'] = '決裁' if is_kessai else '承認'
    elif action_type == 'return':
        routes[step_idx]['status'] = '差し戻し'
    elif action_type == 'reject':
        routes[step_idx]['status'] = '却下'
        
    routes[step_idx]['actionAt'] = datetime.now().strftime('%Y/%m/%d %H:%M')
    routes[step_idx]['comment'] = comment
    
    # 次のステータス計算
    if action_type == 'reject':
        new_global_status = '却下'
    elif action_type == 'return':
        new_global_status = '差し戻し'
        # 差し戻しの場合はステップ1（起案）に戻し、他のステップを「未到達」に戻す
        current_step = 1
        for i, r in enumerate(routes):
            if i == 0:
                r['status'] = '承認' # 起案は承認済みのまま
            elif i == 1:
                r['status'] = '進行中' # 次ステップを進行中に
            else:
                r['status'] = '未到達'
        current_step = 2
    else: # approve
        if step_idx < len(routes) - 1:
            routes[step_idx + 1]['status'] = '進行中'
            current_step += 1
            new_global_status = '進行中'
        else:
            new_global_status = '決裁'
            
    transaction.update(app_ref, {
        'globalStatus': new_global_status,
        'currentStep': current_step,
        'routes': routes
    })
    return new_global_status

@app.route('/api/applications/action', methods=['POST'])
@login_required
def api_application_action():
    data = request.json
    app_number = data.get('appNumber')
    action_type = data.get('action') # 'approve', 'return', 'reject'
    comment = data.get('comment', '')
    
    if not app_number or not action_type:
        return jsonify({"error": "パラメータ不足"}), 400
        
    email = session['email']
    user_doc = db.collection("users").document(email).get()
    current_user = user_doc.to_dict()
    
    try:
        transaction = db.transaction()
        app_ref = db.collection("applications").document(app_number)
        
        new_status = process_approval_transaction(
            transaction, app_ref, action_type, comment, current_user['name']
        )
        return jsonify({"success": True, "newStatus": new_status})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 6. 管理者向け：マスタデータの新規作成・更新
@app.route('/api/admin/forms/save', methods=['POST'])
@login_required
def api_admin_save_form():
    email = session['email']
    user_doc = db.collection("users").document(email).get()
    if not user_doc.exists or not user_doc.to_dict().get('isAdmin'):
        return jsonify({"error": "Forbidden"}), 403
        
    data = request.json
    form_id = data.get('id')
    form_name = data.get('name')
    description = data.get('description', '')
    routes = data.get('routes', [])
    
    if not form_id or not form_name:
        return jsonify({"error": "必須入力項目不足"}), 400
        
    form_data = {
        "name": form_name,
        "description": description,
        "routes": routes,
        "sortOrder": data.get('sortOrder', 99)
    }
    
    db.collection("forms").document(form_id).set(form_data)
    return jsonify({"success": True})

# 7. 管理者向け：マスタデータの削除
@app.route('/api/admin/forms/delete/<form_id>', methods=['POST'])
@login_required
def api_admin_delete_form(form_id):
    email = session['email']
    user_doc = db.collection("users").document(email).get()
    if not user_doc.exists or not user_doc.to_dict().get('isAdmin'):
        return jsonify({"error": "Forbidden"}), 403
        
    db.collection("forms").document(form_id).delete()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(port=8082, debug=True)
