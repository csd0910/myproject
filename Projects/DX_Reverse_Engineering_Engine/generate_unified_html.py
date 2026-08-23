import os
import csv
import json
import datetime
from google import genai
from collections import defaultdict
import glob

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

def generate_unified_report(target_dir):
    activity_logs = glob.glob(os.path.join(target_dir, "activity_log_*.csv"))
    system_logs = glob.glob(os.path.join(target_dir, "system_log_*.csv"))

    if not system_logs:
        print("[エラー] 統合するシステムログ(system_log_ai_evaluated_*.csv)が見つかりません。")
        return

    # --- データの読み込みと集計 ---
    app_usage = defaultdict(int)
    task_counts = {"手入力・編集": 0, "コピペ・反復転記": 0, "関数処理": 0, "その他閲覧・待機": 0}
    
    # Activity logs の集計 (グラフ用)
    for alog in activity_logs:
        with open(alog, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.reader(f)
            next(reader, None) # header
            for row in reader:
                if len(row) >= 6:
                    dur_str, app = row[2], row[4]
                    try:
                        dur_int = int(dur_str.replace("秒", "").strip())
                        app_usage[app] += dur_int
                    except:
                        pass

    # System logs の集計 (プロンプト＆グラフ補完用)
    system_log_text = ""
    for slog in system_logs:
        with open(slog, "r", encoding="utf-8-sig", errors="ignore") as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 0 or len(row) < 5: continue
                ts, app, ev, target, meta = row[0], row[1], row[2], row[3], row[4]
                
                # 詳細すぎるログは文字数制限を回避するため一部省略して渡すか、そのまま結合
                # AIがコンテキストを把握しやすいように加工
                desc = row[5] if len(row) > 5 else ""
                system_log_text += f"[{ts}] App:{app} | Event:{ev} | Target:{target} | Meta:{meta[:50]} | AI:{desc}\n"
                
                # タスクカウント（簡易集計）
                ev_lower = ev.lower()
                if "copy" in ev_lower or "paste" in ev_lower or "transfer" in ev_lower or "コピペ" in desc:
                    task_counts["コピペ・反復転記"] += 1
                elif "sheetchange" in ev_lower:
                    if "=" in meta:
                        task_counts["関数処理"] += 1
                    else:
                        task_counts["手入力・編集"] += 1
                elif "calculate" in ev_lower or "function" in ev_lower:
                    task_counts["関数処理"] += 1
                else:
                    task_counts["その他閲覧・待機"] += 1

    sorted_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)
    if not sorted_apps: # fallback
        sorted_apps = [("Excel", 100)]
    chart_labels = [app for app, dur in sorted_apps]
    chart_data = [dur for app, dur in sorted_apps]
    
    task_labels = list(task_counts.keys())
    task_data = list(task_counts.values())

    # ==========================================
    # Geminiへのプロンプト（統合版特化）
    # ==========================================
    prompt_dx = f"""
あなたはエグゼクティブ向けの優秀な業務コンサルタント兼Python/VBA自動化エンジニアです。
以下の【全日程・統合システムログ】を総合的に分析し、HTML要素のみを出力してください（```htmlなどのマークダウン記号は絶対に含まないこと）。

【出力フォーマット・要件】
<h2 class="text-2xl mb-4 border-b pb-2 text-blue-700 font-bold">📁 操作した主要ファイルと手作業のコスト</h2>
（操作した主要なファイル名・システム名すべてと、それに費やした手作業の実時間、およびプログラムで自動化した場合の想定削減時間を簡潔にリスト化してください）

<div class="mt-8 flex flex-col lg:flex-row gap-8">
    <div class="flex-1 lg:w-1/2">
        <h2 class="text-xl mb-4 border-b pb-2 text-teal-700 font-bold">🔄 現在の処理フロー図 (手動所要時間)</h2>
        <div class="mermaid bg-slate-50 p-4 rounded shadow">
        graph TD
        （ここに全日程を統合した現在のフローを記載。※絶対にSyntax Errorを出さないよう、A["ノードテキスト"]の記法を使用すること）
        （★必須条件★：各工程の間に、推測される所要時間を「A -->|約1分30秒| B」のように必ず表示してください。＊時間＊分＊秒 の形式で記載すること）
        </div>
    </div>
    <div class="flex-1 lg:w-1/2">
        <h2 class="text-xl mb-4 border-b pb-2 text-orange-600 font-bold">🚀 自動化後のフロー図 (短縮時間)</h2>
        <div class="mermaid bg-slate-50 p-4 rounded shadow">
        graph TD
        （ここに自動化後の最適化フローを記載。同様にA["ノード"]の構文を厳守）
        （★必須条件★：ここでも工程間に「A -->|約1秒| B」のように短縮後の時間を表示してください）
        </div>
    </div>
</div>

<div class="mt-12 bg-orange-50 p-6 rounded-xl border border-orange-100">
    <h2 class="text-2xl mb-4 text-orange-800 font-bold">💡 具体的な自動化案とステップ（統合版）</h2>
    （全日程の操作を通じた、最終的かつ総合的なDX化案をStep1, Step2...と順に記載してください。
    【最重要制約】RPA（UiPathやWinActorなど）は絶対に使用・提案しないでください。最優先で「Python」を用いた自動化スクリプトの開発を提案し、次点で「Excel VBA」によるマクロ化を提案してください。）
</div>

【システム詳細ログ（全日程）】
{system_log_text[-50000:]} 
"""
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        print("Gemini APIへ統合分析をリクエスト中...")
        res_dx = client.models.generate_content(model=GEMINI_MODEL, contents=prompt_dx)
        html_dx = res_dx.text.replace("```html", "").replace("```", "").strip()
        
        template_dx = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>完全統合版 DX抽出レポート</title>
    <script src="https://cdn.tailwindcss.com"></script><script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({{startOnLoad:true}});</script>
    <style>body {{ background-color: #f8fafc; color: #334155; }}</style>
</head>
<body class="p-6 md:p-12">
    <div class="max-w-7xl mx-auto bg-white p-8 rounded-xl shadow-lg border border-gray-100">
        <header class="mb-12 border-b pb-6">
            <h1 class="text-4xl font-extrabold text-slate-800 mb-2">完全統合版 DX抽出レポート</h1>
            <p class="text-slate-500">全業務ログの統合AI分析と最終自動化提案</p>
        </header>
        
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-12">
            <!-- 左カラム：グラフ -->
            <div class="lg:col-span-3 space-y-12 border-r pr-8">
                <div>
                    <h2 class="text-lg font-bold mb-4 text-center text-slate-700">🖥️ アプリ使用割合 (総計)</h2>
                    <div class="relative w-full aspect-square"><canvas id="appChart"></canvas></div>
                </div>
                <div>
                    <h2 class="text-lg font-bold mb-4 text-center text-slate-700">⚙️ 操作ごとの割合 (作業分解)</h2>
                    <div class="relative w-full aspect-square"><canvas id="taskChart"></canvas></div>
                </div>
            </div>
            
            <!-- 右カラム：AI解析結果 -->
            <div class="lg:col-span-9">
                {html_dx}
            </div>
        </div>
    </div>
    <script>
        new Chart(document.getElementById('appChart').getContext('2d'), {{
            type: 'pie', data: {{ labels: {json.dumps(chart_labels)}, datasets: [{{ data: {json.dumps(chart_data)}, backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b'] }}] }}
        }});
        new Chart(document.getElementById('taskChart').getContext('2d'), {{
            type: 'pie', data: {{ labels: {json.dumps(task_labels)}, datasets: [{{ data: {json.dumps(task_data)}, backgroundColor: ['#ef4444', '#3b82f6', '#10b981', '#64748b'] }}] }}
        }});
    </script>
</body></html>"""
        report_dir = os.path.join(target_dir, "daily_reports")
        os.makedirs(report_dir, exist_ok=True)
        file_dx = os.path.join(report_dir, "DX_Integrated_Report.html")
        with open(file_dx, "w", encoding="utf-8") as f:
            f.write(template_dx)
        print(f"[完了] 完全統合版のHTMLレポートを生成しました: {file_dx}")
    except Exception as e:
        print(f"[エラー] 統合版生成エラー: {e}")

if __name__ == '__main__':
    generate_unified_report(r"C:\Users\フォーレスト026\MyProject\業務自動化分析ツール\AutoAnalysisLogs")
