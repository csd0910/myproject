# -*- coding: utf-8 -*-
"""
PostgreSQL (Cloud SQL) 接続テスト & テーブル初期化スクリプト
実行すると:
  1. DBへの接続確認
  2. 必要なテーブルが存在しなければ作成
  3. usersテーブルが空の場合に初期管理者ユーザーを1件追加
"""

import sys
import pg8000.dbapi

# ==========================================
# ⚙️ 接続情報（定数）
# ==========================================
DB_HOST = "34.146.122.39"
DB_PORT = 5432
DB_NAME = "forest-workflow-app-001-database"
DB_USER = "postgres"
DB_PASS = "Forest0720@"


def test_connection():
    print("=== PostgreSQL (Cloud SQL) 接続テスト開始 ===")
    conn = None
    try:
        conn = pg8000.dbapi.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            timeout=10
        )
        print("[OK] データベースへの接続成功！")
        cursor = conn.cursor()

        # 1. ユーザーテーブルの作成
        print("テーブル作成: users ...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email           VARCHAR(255) PRIMARY KEY,
                name            VARCHAR(255) NOT NULL,
                dept            VARCHAR(255) NOT NULL DEFAULT '所属なし',
                title           VARCHAR(255),
                is_admin        BOOLEAN DEFAULT FALSE,
                is_allowed_user BOOLEAN DEFAULT TRUE
            );
        """)

        # 2. フォームマスタテーブルの作成
        print("テーブル作成: forms ...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS forms (
                id          VARCHAR(255) PRIMARY KEY,
                name        VARCHAR(255) NOT NULL,
                description TEXT,
                folder_id   VARCHAR(255),
                routes      TEXT,
                sort_order  INTEGER DEFAULT 99
            );
        """)

        # 3. 申請テーブルの作成
        print("テーブル作成: applications ...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                app_number      VARCHAR(255) PRIMARY KEY,
                form_name       VARCHAR(255) NOT NULL,
                title           VARCHAR(255) NOT NULL,
                applicant       VARCHAR(255) NOT NULL,
                applicant_email VARCHAR(255) NOT NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date            VARCHAR(20) NOT NULL,
                global_status   VARCHAR(50) NOT NULL DEFAULT '進行中',
                current_step    INTEGER DEFAULT 1,
                pdf_name        VARCHAR(255),
                pdf_url         TEXT,
                routes          TEXT
            );
        """)

        conn.commit()
        print("[OK] テーブル作成・スキーマ確認 完了。")

        # 4. 初期管理者ユーザーの挿入（空の場合のみ）
        cursor.execute("SELECT COUNT(*) FROM users;")
        count = cursor.fetchone()[0]
        if count == 0:
            print("初期管理者ユーザーを挿入します ...")
            cursor.execute("""
                INSERT INTO users (email, name, dept, title, is_admin, is_allowed_user)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, ("forest026@gmail.com", "管理者", "システム開発部", "社内SE", True, True))
            conn.commit()
            print("[OK] 初期ユーザーを挿入しました。")
        else:
            print(f"  ※ usersテーブルには既に {count} 件のデータがあります。初期挿入はスキップします。")

        # 5. 各テーブルの件数確認
        print("\n--- テーブル件数確認 ---")
        for tbl in ("users", "forms", "applications"):
            cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
            n = cursor.fetchone()[0]
            print(f"  {tbl}: {n} 件")

        print("\n=== テスト完了 ===")

    except Exception as e:
        print(f"[ERROR] 接続またはテーブル初期化に失敗しました: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn:
            conn.close()
            print("接続をクローズしました。")


if __name__ == "__main__":
    test_connection()
