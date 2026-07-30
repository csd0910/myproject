import os
import csv
import json
import datetime
from google import genai
from collections import defaultdict

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

def generate_reports(target_dir=None):
    if not target_dir:
        target_dir = os.path.dirname(__file__)
        
    activity_log = None
    system_log = None
    for f in os.listdir(target_dir):
        if f.startswith("activity_log_") and f.endswith(".csv"):
            activity_log = os.path.join(target_dir, f)
        elif f.startswith("system_log_") and f.endswith(".csv"):
            system_log = os.path.join(target_dir, f)

    if not activity_log and not system_log:
        print("[エラー] ログファイルが見つかりません。")
        return

    # --- データの読み込み ---
    target_date = datetime.datetime.now().strftime("%Y%m%d")
    app_usage = defaultdict(int)
    total_seconds = 0
    log_text = ""
    system_log_text = ""
    
    # 簡易集計（活動ログ）
    if activity_log:
        target_date = activity_log.split("_")[-1].replace(".csv", "")
        with open(activity_log, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            for row in reader:
                if len(row) >= 4:
                    app, title, start, end, dur = row[1], row[2], row[3], row[4], row[5]
                    try:
                        dur_int = int(dur)
                        app_usage[app] += dur_int
                        total_seconds += dur_int
                    except:
                        pass
                    log_text += f"- {start}〜{end} [{app}] {title} ({dur}秒)\n"

    # 詳細集計（システムログ）と作業割合の算出
    task_counts = {"手入力・編集": 0, "コピペ・反復転記": 0, "関数処理": 0, "その他閲覧・待機": 0}
    if system_log:
        with open(system_log, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            for row in reader:
                if len(row) >= 5:
                    ts, app, ev, target, meta = row[0], row[1], row[2], row[3], row[4]
                    system_log_text += f"[{ts}] App:{app} | Event:{ev} | Target:{target} | Meta:{meta}\n"
                    
                    # 作業種類の判別（推測ロジック）
                    ev_lower = ev.lower()
                    if "copy" in ev_lower or "paste" in ev_lower or "transfer" in ev_lower:
                        task_counts["コピペ・反復転記"] += 1
                    elif "sheetchange" in ev_lower:
                        # 簡易的に関数入力かどうかを推測
                        if "meta" in ev_lower and "=" in meta:
                            task_counts["関数処理"] += 1
                        else:
                            task_counts["手入力・編集"] += 1
                    elif "calculate" in ev_lower or "function" in ev_lower:
                        task_counts["関数処理"] += 1
                    else:
                        task_counts["その他閲覧・待機"] += 1

    sorted_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)
    chart_labels = [app for app, dur in sorted_apps]
    chart_data = [dur for app, dur in sorted_apps]
    
    task_labels = list(task_counts.keys())
    task_data = list(task_counts.values())

    report_dir = os.path.join(target_dir, "daily_reports")
    os.makedirs(report_dir, exist_ok=True)

    if not GEMINI_API_KEY:
        print("[エラー] GEMINI_API_KEYが設定されていません。")
        return

    client = genai.Client()

    # ==========================================
    # 1. 簡易モード（日報）の生成
    # ==========================================
    prompt_simple = f"""
あなたは優秀なアシスタントです。以下の作業ログから、1日の業務をまとめた綺麗なHTMLの日報を作成してください。
【本日の作業ログ】
{log_text}
【要件】
1. HTMLの <div> などの要素のみ出力してください（```html などの記号は不要）。
2. 「本日の主な業務サマリ」と「タイムライン（時系列の作業内容）」を分かりやすく記載してください。
"""
    try:
        res_simple = client.models.generate_content(model=GEMINI_MODEL, contents=prompt_simple)
        html_simple = res_simple.text.replace("```html", "").replace("```", "").strip()
        
        template_simple = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>簡易業務日報 - {target_date}</title>
    <script src="https://cdn.tailwindcss.com"></script><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>body {{ background-color: #f8fafc; color: #334155; }}</style>
</head>
<body class="p-6 md:p-12">
    <div class="max-w-5xl mx-auto bg-white p-8 rounded-xl shadow-lg border border-gray-100">
        <h1 class="text-3xl font-extrabold mb-8 border-b pb-4 text-slate-800">簡易業務日報 ({target_date})</h1>
        <div class="flex flex-col md:flex-row gap-8">
            <div class="md:w-1/3 border-r pr-8">
                <h2 class="text-xl font-bold mb-4 text-center text-slate-700">アプリ使用割合</h2>
                <div class="relative w-full aspect-square"><canvas id="appChart"></canvas></div>
            </div>
            <div class="md:w-2/3">
                {html_simple}
            </div>
        </div>
    </div>
    <script>
        new Chart(document.getElementById('appChart').getContext('2d'), {{
            type: 'pie', data: {{ labels: {json.dumps(chart_labels)}, datasets: [{{ data: {json.dumps(chart_data)} }}] }}
        }});
    </script>
</body></html>"""
        file_simple = os.path.join(report_dir, f"daily_report_simple_{target_date}.html")
        with open(file_simple, "w", encoding="utf-8") as f:
            f.write(template_simple)
        print(f"[完了] 簡易モード日報生成: {file_simple}")
    except Exception as e:
        print(f"[エラー] 簡易モード: {e}")

    # ==========================================
    # 2. 詳細DX抽出モードの生成
    # ==========================================
    prompt_dx = f"""
あなたはエグゼクティブ向けの優秀な業務コンサルタント兼RPAエンジニアです。
以下の【システム詳細ログ】を分析し、HTML要素のみを出力してください（```htmlなどのマークダウン記号は絶対に含まないこと）。

【出力フォーマット・要件】
<h2 class="text-2xl mb-4 border-b pb-2 text-blue-700 font-bold">⏱ タイムスタンプ順の操作履歴と所要時間</h2>
（各作業の「手作業での所要時間」と「プログラムで自動化した場合の参考時間」を対比してリスト化）

<div class="mt-8 flex flex-col lg:flex-row gap-8">
    <div class="flex-1 lg:w-1/2">
        <h2 class="text-xl mb-4 border-b pb-2 text-teal-700 font-bold">🔄 現在の処理フロー図 (手動所要時間)</h2>
        <div class="mermaid bg-slate-50 p-4 rounded shadow">
        （ここに現在のフローのgraph TDを記載。※ノード名に()や[]を含む場合は必ずダブルクォーテーションで囲むこと）
        </div>
    </div>
    <div class="flex-1 lg:w-1/2">
        <h2 class="text-xl mb-4 border-b pb-2 text-orange-600 font-bold">🚀 自動化後のフロー図 (短縮時間)</h2>
        <div class="mermaid bg-slate-50 p-4 rounded shadow">
        （ここに自動化後のフローのgraph TDを記載。どういう自動化ができるかと予定短縮時間を含めること）
        </div>
    </div>
</div>

<div class="mt-12 bg-orange-50 p-6 rounded-xl border border-orange-100">
    <h2 class="text-2xl mb-4 text-orange-800 font-bold">💡 具体的な自動化案とステップ</h2>
    （現在の処理に対する具体的なDX化案をStep1, Step2...と順に記載）
</div>

【システム詳細ログ】
{system_log_text}
"""
    try:
        res_dx = client.models.generate_content(model=GEMINI_MODEL, contents=prompt_dx)
        html_dx = res_dx.text.replace("```html", "").replace("```", "").strip()
        
        template_dx = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>詳細DX抽出レポート - {target_date}</title>
    <script src="https://cdn.tailwindcss.com"></script><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true}});</script>
    <style>body {{ background-color: #f8fafc; color: #334155; }}</style>
</head>
<body class="p-6 md:p-12">
    <div class="max-w-7xl mx-auto bg-white p-8 rounded-xl shadow-lg border border-gray-100">
        <header class="mb-12 border-b pb-6">
            <h1 class="text-3xl font-extrabold text-slate-800 mb-2">詳細DX抽出レポート ({target_date})</h1>
            <p class="text-slate-500">業務ロギングとAIによる自動化提案</p>
        </header>
        
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-12">
            <!-- 左カラム：グラフ（アプリ割合 ＆ 操作割合） -->
            <div class="lg:col-span-3 space-y-12 border-r pr-8">
                <div>
                    <h2 class="text-lg font-bold mb-4 text-center text-slate-700">🖥️ アプリ使用割合</h2>
                    <div class="relative w-full aspect-square"><canvas id="appChart"></canvas></div>
                </div>
                <div>
                    <h2 class="text-lg font-bold mb-4 text-center text-slate-700">⚙️ 操作ごとの割合 (作業分解)</h2>
                    <div class="relative w-full aspect-square"><canvas id="taskChart"></canvas></div>
                </div>
            </div>
            
            <!-- 右カラム：AI解析結果（タイムライン、フロー図、DX提案） -->
            <div class="lg:col-span-9">
                {html_dx}
            </div>
        </div>
    </div>
    <script>
        // アプリ割合グラフ
        new Chart(document.getElementById('appChart').getContext('2d'), {{
            type: 'pie', data: {{ labels: {json.dumps(chart_labels)}, datasets: [{{ data: {json.dumps(chart_data)}, backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b'] }}] }}
        }});
        // 操作割合（手作業/コピペなど）グラフ
        new Chart(document.getElementById('taskChart').getContext('2d'), {{
            type: 'pie', data: {{ labels: {json.dumps(task_labels)}, datasets: [{{ data: {json.dumps(task_data)}, backgroundColor: ['#ef4444', '#3b82f6', '#10b981', '#64748b'] }}] }}
        }});
    </script>
</body></html>"""
        file_dx = os.path.join(report_dir, f"dx_analysis_report_{target_date}.html")
        with open(file_dx, "w", encoding="utf-8") as f:
            f.write(template_dx)
        print(f"[完了] 詳細DXモード生成: {file_dx}")
    except Exception as e:
        print(f"[エラー] 詳細DXモード: {e}")

if __name__ == "__main__":
    generate_reports()
