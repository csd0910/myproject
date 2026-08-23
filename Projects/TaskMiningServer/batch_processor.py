import os
import json
import time
from google import genai
from database import get_connection, DATABASE_URL

# .envはdatabase.py内で読み込み済み
# 新しいSDKのクライアントを初期化
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# 軽量で高速な最新モデルを指定
MODEL_NAME = 'gemini-3.5-flash'

def run_nightly_batch():
    """
    【Cloud Run ジョブ / Cloud Scheduler 用の処理】
    夜間に1回起動し、未処理の生データを一括でGemini APIに投げてDXレポートを生成する
    """
    print("【Batch】夜間バッチ処理を開始します...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 【最適化】生データをそのままAIに投げると数百万文字になりトークン制限（クオータ）を突破するため、
    # DB側で「ユーザー・アプリ・操作種別ごとの合計時間・合計回数」に圧縮集計してから取得する
    query_summary = """
        SELECT user_id, app_name, operation_type,
               COUNT(*) as event_count,
               SUM(duration_seconds) as total_duration_seconds,
               SUM(manual_typing_count) as total_manual_typing,
               SUM(copy_paste_count) as total_copy_paste,
               AVG(cpu_usage_percent) as avg_cpu_usage,
               MAX(browser_tab_count) as max_browser_tabs
        FROM client_logs 
        WHERE is_processed = 0 
        GROUP BY user_id, app_name, operation_type
    """
    cursor.execute(query_summary)
    summary_rows = cursor.fetchall()
    
    # 時間帯ごとの件数推移を取得（PostgreSQL/SQLite両対応の簡易判定）
    if DATABASE_URL:
        cursor.execute("SELECT EXTRACT(HOUR FROM TO_TIMESTAMP(received_at)) as hr, COUNT(*) FROM client_logs WHERE is_processed = 0 GROUP BY hr ORDER BY hr")
    else:
        cursor.execute("SELECT strftime('%H', datetime(received_at, 'unixepoch', 'localtime')) as hr, COUNT(*) FROM client_logs WHERE is_processed = 0 GROUP BY hr ORDER BY hr")
    hourly_rows = cursor.fetchall()
    
    # さらに未処理IDリスト（処理済みフラグを立てる用）を別途取得
    cursor.execute("SELECT id FROM client_logs WHERE is_processed = 0")
    processed_ids = [r[0] for r in cursor.fetchall()]
    
    if not processed_ids:
        print("【Batch】処理待ちのデータはありません。")
        return None

    # サマリーデータをJSON化
    aggregated_data = []
    for row in summary_rows:
        aggregated_data.append({
            "user_id": row[0],
            "app_name": row[1],
            "operation": row[2],
            "event_count": row[3],
            "total_duration_sec": row[4],
            "total_typing": row[5],
            "total_copypaste": row[6],
            "avg_cpu": row[7],
            "max_tabs": row[8]
        })
        
    print(f"【Batch】計{len(processed_ids)}件の生ログを、{len(aggregated_data)}件のサマリーに極限圧縮。Gemini APIへ送信します...")

    # ユーザーごとのループを廃止し、部門全体のデータとして1回で送信
    print(f"【Gemini】全部門のデータを一括解析中...")
    prompt = f"""
    あなたは企業のDXコンサルタントです。以下のデータは、ある部署（6名）の1日（9:00〜18:00）のPC操作ログです。
    部内全体として、どういうファイル作業にどのような時間を使い、どのアプリでの作業が多いかをマクロな視点で分析し、部単位の業務改善レポートを作成してください。
    
    【重要：提案内容の技術スタックに関する制約】
    以下の技術のみを用いて効率化・自動化の提案を行ってください。
    ✅ 推奨技術: PowerShell, Excel VBA, Python, Google Apps Script (GAS)
    ❌ 禁止技術: 商用RPAツール (WinActor, UiPath, BizRobo! 等), Power Query
    
    【重要：出力形式】
    結果は単なるテキストではなく、美しくモダンなダッシュボード風のHTMLファイルとして出力してください。
    以下のデザイン要件を必ず満たしてください：
    - 1つの完全なHTMLファイルとして出力（<!DOCTYPE html>から始めること）
    - TailwindCSSではなく、純粋なVanilla CSSを使用すること
    - 画面表示時はダークモードを基調とし、モダンなフォント（Google FontsのInterなど）を使用
    - 【重要】印刷時（Ctrl+P）を考慮し、CSSに `@media print` を用いて、印刷時は自動的に「完全な白背景」「黒文字」「影や不要な背景グラデーションの無効化」となるようにコーディングすること
    - カード型レイアウト、グラデーション、微細なアニメーションを取り入れ「プレミアムなDXレポート」にすること
    - Chart.js (CDN経由: https://cdn.jsdelivr.net/npm/chart.js) を必ず利用し、以下の5つの視覚的グラフを描画してください：
      1. 【時系列の滑らかな折れ線グラフ】横軸に時間（9:00〜18:00）または日数、縦軸に作業件数を示す Line Chart（`tension: 0.4` を指定して美しい滑らかな曲線にすること）。
      2. 【手作業固執度グラフ】手作業（コピペや手入力）の多さを可視化し、「手作業でもいいや」という学習意欲の低さ（DX停滞度）をあぶり出す Bar Chart または Scatter Chart。
      3. 【割合の円グラフ】作業アプリや操作種別の割合を示す Pie Chart または Doughnut Chart。
      4. 【5段階評価のレーダーチャート】DX度合いを視覚化するため「自動化率」「タイピング少なさ」「コピペ少なさ」「PC負荷の低さ」「変化への適応力」の5項目を5角形で評価する Radar Chart。
      5. 【改善効果の比較グラフ】「現状（Before）」と「AIによる改善案適用後（After）」の予想作業時間を比較する Bar Chart。
    - 【重要：直感的な説明ポップアップ（ツールチップ）】各グラフの描画領域（キャンバスやラッパー要素）には、マウスカーソルを合わせた際（ホバー時）に「このグラフが何を表しているか（例：手作業への固執度が高いため、早急に自動化が必要です等）」が詳細なポップアップとして浮かび上がるよう、HTMLの `title` 属性や、Chart.jsの `plugins.tooltip.callbacks` などを駆使して実装してください。
    - 長くて複雑なテキストは最小限に抑え、パッと見て課題と改善効果が直感的に伝わる「視覚的」なレポートにしてください。
    - 【重要：瞬時のティーチング】グラフの下に、「あなたはこの手作業をいますぐこう変えなさい」という即効性のある『マイクロラーニング（VBAやPythonのコピペで動く3行ほどのコードや、ショートカットキーの提示）』を必ずポップなUIで差し込み、学習意欲が低い人でもその場で瞬時に学べる（気づきを得られる）仕掛けを作ってください。
    
    【部門操作サマリー（ユーザー/アプリ別）】
    {json.dumps(aggregated_data, ensure_ascii=False)}
    
    【時間帯ごとの作業件数（時系列）】
    {json.dumps(hourly_rows, ensure_ascii=False)}
    """
    
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        report_text = response.text.replace("```html", "").replace("```", "").strip()
        
        filename = f"report_department_{int(time.time())}.html"
        filepath = os.path.join(os.path.dirname(__file__), filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_text)
            
        print(f"  -> [解析完了] 部門レポートを {filename} に保存しました。")
    except Exception as e:
        print(f"  -> [エラー] 部門レポートの解析中にエラー: {e}")
        
    # 処理完了マークをつける（UPDATE）
    for row_id in processed_ids:
        # DBごとにプレースホルダを分ける
        if DATABASE_URL:
            cursor.execute("UPDATE client_logs SET is_processed = 1 WHERE id = %s", (row_id,))
        else:
            cursor.execute("UPDATE client_logs SET is_processed = 1 WHERE id = ?", (row_id,))
            
    conn.commit()
    conn.close()
    
    print("【Batch】夜間バッチ処理がすべて完了しました。")
    return filename

if __name__ == "__main__":
    run_nightly_batch()
