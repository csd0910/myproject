import time
import json
from database import get_connection

def insert_dummy_data():
    conn = get_connection()
    cursor = conn.cursor()
    
    user_id = "excel_worker_demo"
    base_time = time.time() - 3600 # 1時間前から開始
    
    # 1時間の作業をシミュレートするダミーログ
    logs = [
        {"time": 0, "app": "EXCEL.EXE", "title": "【商品課】週次報告フォーマット.xlsx", "analysis": "前週の実績ファイルを複数開き、対象列を手作業でコピー＆ペーストして転記している。"},
        {"time": 300, "app": "EXCEL.EXE", "title": "受注明細_202607.csv", "analysis": "CSVから大量のデータをコピーし、報告書フォーマットの別シートに貼り付け。"},
        {"time": 600, "app": "EXCEL.EXE", "title": "【商品課】週次報告フォーマット.xlsx", "analysis": "手入力でVLOOKUP関数を複数の列（CH列〜CV列）に構築し、別ファイルから単価や担当者名を引っ張っている。"},
        {"time": 900, "app": "EXCEL.EXE", "title": "【商品課】週次報告フォーマット.xlsx", "analysis": "ROUNDUP関数とMATCH関数を組み合わせた複雑な数式を手作業で組み立て、各行にオートフィルで適用。"},
        {"time": 1500, "app": "EXCEL.EXE", "title": "0727商品一覧.csv", "analysis": "さらに別のCSVを開き、先ほどのシートと目視で見比べながら欠損データを手作業で補完。"},
        {"time": 2100, "app": "EXCEL.EXE", "title": "【商品課】週次報告フォーマット.xlsx", "analysis": "値の貼り付け（値のみペースト）を数十回繰り返し、数式をテキスト化している。"},
        {"time": 2700, "app": "EXCEL.EXE", "title": "【商品課】週次報告フォーマット.xlsx", "analysis": "エラー（#N/A）が出たセルを目視で探し、手作業で1つずつ削除・修正している。"},
        {"time": 3300, "app": "EXCEL.EXE", "title": "【商品課】週次報告フォーマット.xlsx", "analysis": "完成したデータをピボットテーブルにかけ、最終的なレポートの形に集計。同じ作業を毎週繰り返していると推測される。"},
        {"time": 3600, "app": "EXCEL.EXE", "title": "【商品課】週次報告フォーマット.xlsx", "analysis": "ファイルを上書き保存し、作業完了。"}
    ]
    
    for i, log in enumerate(logs):
        log_time = base_time + log["time"]
        payload = {
            "app": log["app"],
            "title": log["title"],
            "analysis": log["analysis"],
            "simulated": True
        }
        
        # PostgreSQLはJSON文字列で保存するか、辞書のまま（psycopg2が自動変換するかは場合によるがjson.dumpsが無難）
        payload_str = json.dumps(payload, ensure_ascii=False)
        
        cursor.execute(
            "INSERT INTO client_logs (user_id, log_type, payload, received_at) VALUES (%s, %s, %s, %s)",
            (user_id, "window_change", payload_str, log_time)
        )
        
    conn.commit()
    conn.close()
    print("ダミーデータの注入が完了しました！")

if __name__ == "__main__":
    insert_dummy_data()
