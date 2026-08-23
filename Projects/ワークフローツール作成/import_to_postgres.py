# -*- coding: utf-8 -*-
"""
CSVデータ → PostgreSQL (Cloud SQL) インポートスクリプト
実行すると:
  - m_user.csv       → usersテーブルに UPSERT
  - m_route_form.csv → formsテーブルに UPSERT
  - （オプション）Firestore申請データの移行（コメントアウト中）
"""

import os
import csv
import json
import sys
import pg8000.dbapi

# ==========================================
# ⚙️ パス・接続情報（定数）
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USER_CSV_PATH  = os.path.join(BASE_DIR, "m_user.csv")
FORM_CSV_PATH  = os.path.join(BASE_DIR, "m_route_form.csv")

DB_HOST = "34.146.122.39"
DB_PORT = 5432
DB_NAME = "forest-workflow-app-001-database"
DB_USER = "postgres"
DB_PASS = "Forest0720@"


# ==========================================
# 🔌 DB接続
# ==========================================
def get_pg_connection():
    return pg8000.dbapi.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        timeout=15
    )


# ==========================================
# 📂 CSV読み込み（文字コード自動判定）
# ==========================================
def read_csv_safely(path):
    """複数エンコーディングを順に試してCSVを読み込む"""
    encodings = ['utf-8-sig', 'cp932', 'shift_jis', 'utf-8']
    for enc in encodings:
        try:
            with open(path, 'r', encoding=enc) as f:
                return list(csv.reader(f))
        except UnicodeDecodeError:
            continue
    raise ValueError(f"ファイルのエンコードを特定できませんでした: {path}")


# ==========================================
# 👤 ユーザーインポート
# ==========================================
def import_users(cursor):
    print("--- m_user.csv からユーザーをインポート ---")
    if not os.path.exists(USER_CSV_PATH):
        print("  ※ m_user.csv が見つかりません。スキップします。")
        return

    try:
        rows = read_csv_safely(USER_CSV_PATH)
    except Exception as e:
        print(f"  [ERROR] CSV読み込み失敗: {e}")
        return

    count = 0
    for row in rows[1:]:   # 1行目はヘッダー
        if len(row) < 3 or not row[2].strip():
            continue

        first_name = row[0].strip()
        last_name  = row[1].strip()
        email      = row[2].strip().lower()
        dept       = row[5].strip()  if len(row) > 5  else ""
        title      = row[20].strip() if len(row) > 20 else ""
        role_flag  = row[40].strip() if len(row) > 40 else "0"

        is_admin   = (role_flag in ["1", "1.0", "１"])
        is_allowed = (is_admin or role_flag in ["2", "2.0", "２"])
        name       = f"{last_name} {first_name}".strip()

        cursor.execute("""
            INSERT INTO users (email, name, dept, title, is_admin, is_allowed_user)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                name            = EXCLUDED.name,
                dept            = EXCLUDED.dept,
                title           = EXCLUDED.title,
                is_admin        = EXCLUDED.is_admin,
                is_allowed_user = EXCLUDED.is_allowed_user;
        """, (email, name, dept or "所属なし", title or "", is_admin, is_allowed))
        count += 1

    print(f"  ユーザー: {count} 件をインポート／更新しました。")


# ==========================================
# 📋 フォームマスタインポート
# ==========================================
def import_forms(cursor):
    print("--- m_route_form.csv からフォームをインポート ---")
    if not os.path.exists(FORM_CSV_PATH):
        print("  ※ m_route_form.csv が見つかりません。スキップします。")
        return

    try:
        rows = read_csv_safely(FORM_CSV_PATH)
    except Exception as e:
        print(f"  [ERROR] CSV読み込み失敗: {e}")
        return

    count = 0
    for idx, row in enumerate(rows[1:]):   # 1行目はヘッダー
        if len(row) < 2 or not row[0].strip():
            continue

        form_id     = row[0].strip()
        form_name   = row[1].strip()
        description = row[2].strip() if len(row) > 2 else ""
        routes_str  = row[3].strip() if len(row) > 3 and row[3].strip() else "[]"
        folder_id   = row[4].strip() if len(row) > 4 else ""
        sort_order  = idx
        if len(row) > 5 and row[5].strip():
            try:
                sort_order = int(float(row[5].strip()))
            except ValueError:
                pass

        cursor.execute("""
            INSERT INTO forms (id, name, description, folder_id, routes, sort_order)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name        = EXCLUDED.name,
                description = EXCLUDED.description,
                folder_id   = EXCLUDED.folder_id,
                routes      = EXCLUDED.routes,
                sort_order  = EXCLUDED.sort_order;
        """, (form_id, form_name, description, folder_id, routes_str, sort_order))
        count += 1

    print(f"  フォーム: {count} 件をインポート／更新しました。")


# ==========================================
# 🚀 メイン処理
# ==========================================
def main():
    print("=== PostgreSQL データインポート 開始 ===\n")
    conn = get_pg_connection()
    try:
        cursor = conn.cursor()

        import_users(cursor)
        import_forms(cursor)
        # ↓ Firestoreからの申請データ移行が必要な場合はコメント解除
        # migrate_firestore_applications(cursor)

        conn.commit()
        print("\n[SUCCESS] インポート完了！")
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] インポート失敗: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()
        print("DB接続をクローズしました。")


if __name__ == "__main__":
    main()
