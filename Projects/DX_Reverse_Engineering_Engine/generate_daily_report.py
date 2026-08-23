import os
import csv
import json
import datetime
from google import genai
from collections import defaultdict

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

def generate_reports(target_dir=None, progress_callback=None):
    if not target_dir:
        target_dir = os.path.dirname(__file__)
        
    activity_logs = []
    system_logs = []
    import glob
    for f in glob.glob(os.path.join(target_dir, "activity_log_*.csv")):
        activity_logs.append(f)
    for f in glob.glob(os.path.join(target_dir, "system_log_*.csv")):
        if "ai_evaluated" not in f:
            system_logs.append(f)

    activity_log = max(activity_logs, key=os.path.getmtime) if activity_logs else None
    system_log = max(system_logs, key=os.path.getmtime) if system_logs else None

    if not activity_log and not system_log:
        print("[エラー] ログファイルが見つかりません。")
        return

    # --- データの読み込み ---
    target_date = datetime.datetime.now().strftime("%Y%m%d")
    app_usage = defaultdict(int)
    total_seconds = 0
    log_text = ""
    system_log_text = ""
    task_counts = {"手入力・編集": 0, "コピペ・反復転記": 0, "関数処理": 0, "その他閲覧・待機": 0}
    
    # 簡易集計（活動ログ）
    if activity_log:
        target_date = activity_log.split("_")[-1].replace(".csv", "")
        with open(activity_log, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            for row in reader:
                if len(row) >= 6:
                    start, end, dur_str, status, app, title = row[0], row[1], row[2], row[3], row[4], row[5]
                    ai_text = row[6] if len(row) > 6 else ""
                    
                    try:
                        dur_int = int(dur_str.replace("秒", "").strip())
                        app_usage[app] += dur_int
                        total_seconds += dur_int
                    except:
                        pass
                        
                    log_text += f"- {start}〜{end} [{app}] {title} ({dur_str}) : {ai_text}\n"
                    
                    # system_logが無い場合は、activity_logからタスク種別を推測して代用
                    if not system_log:
                        system_log_text += f"[{start}] App:{app} | Action:{ai_text}\n"
                        ai_lower = ai_text.lower() + title.lower()
                        if "コピペ" in ai_lower or "転記" in ai_lower or "コピー" in ai_lower:
                            task_counts["コピペ・反復転記"] += 1
                        elif "入力" in ai_lower or "更新" in ai_lower:
                            task_counts["手入力・編集"] += 1
                        elif "計算" in ai_lower or "関数" in ai_lower:
                            task_counts["関数処理"] += 1
                        else:
                            task_counts["その他閲覧・待機"] += 1
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

    client = genai.Client(api_key=GEMINI_API_KEY)

    # ==========================================
    # 1. 簡易モード（日報）の生成
    # ==========================================
    prompt_simple = f"""
あなたは優秀なアシスタントです。以下の【タイムラインログ】と【システム詳細操作ログ】を総合的に分析し、1日の業務をまとめた綺麗なHTMLの日報を作成してください。
【タイムラインログ（アプリ滞在時間など）】
{log_text}
【システム詳細操作ログ（Excelでの数式入力やコピペ履歴）】
{system_log_text}
【要件】
1. HTMLの <div> などの要素のみ出力してください（```html などの記号は不要）。
2. 「本日の主な業務サマリ」と「タイムライン」を分かりやすく記載してください。ただし、タイムラインの内容は長々と書かず、操作内容を端的に短くまとめてください。
3. 特に【システム詳細操作ログ】を読み解き、「どのような関数（VLOOKUP等）を組んでいたか」「どんな手作業・コピペをしていたか」の具体例を日報のサマリに盛り込んでください。
"""
    file_simple = os.path.join(report_dir, f"daily_report_simple_{target_date}.html")
    if os.path.exists(file_simple):
        print(f"[スキップ] 既に簡易日報が存在します: {file_simple}")
        if progress_callback: progress_callback(20, "簡易日報は既存のためスキップしました (1/3)...")
    else:
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
            with open(file_simple, "w", encoding="utf-8") as f:
                f.write(template_simple)
            print(f"[完了] 簡易モード日報生成: {file_simple}")
            if progress_callback: progress_callback(20, "簡易日報の生成完了 (1/3)...")
        except Exception as e:
            print(f"[エラー] 簡易モード: {e}")
            if progress_callback: progress_callback(20, f"[エラー] 簡易日報: {e}")


    # ==========================================
    # 2. 詳細DX抽出モードの生成
    # ==========================================
    prompt_dx = f"""
あなたはエグゼクティブ向けの優秀な業務コンサルタント兼Python/VBA自動化エンジニアです。
以下の【システム詳細ログ】を分析し、HTML要素のみを出力してください（```htmlなどのマークダウン記号は絶対に含まないこと）。

※ログには物理キーボードの打鍵（KeyLog）やExcelの詳細な入力値（Value）、数式（Formula）が含まれています。
システム部が自動化の仕様書を定義できるよう、ユーザーが「何を」「どう入力したか（どのキーを打ったか等）」を具体的に反映させて分析してください。

【出力フォーマット・要件】
<h2 class="text-2xl mb-4 border-b pb-2 text-blue-700 font-bold">📁 操作した主要ファイルと手作業のコスト</h2>
（操作した主要なファイル名・システム名と、それに費やした手作業の実時間、およびプログラムで自動化した場合の想定削減時間を簡潔にリスト化してください。日報のような時系列の履歴は不要です。）

<div class="mt-8 flex flex-col lg:flex-row gap-8">
    <div class="flex-1 lg:w-1/2">
        <h2 class="text-xl mb-4 border-b pb-2 text-teal-700 font-bold">🔄 現在の処理フロー図 (全体の手動所要時間: 〇時間〇分〇秒)</h2>
        <!-- ※見出しの「〇時間〇分〇秒」の部分は、あなたが推測した各工程の手作業時間をすべて合計した具体的な総時間を必ず入れてください -->
        <div class="mermaid bg-slate-50 p-4 rounded shadow">
        graph TD
        （ここに現在のフローを記載。※絶対にSyntax Errorを出さないよう、ノードのテキストに記号()や[]、スペースなどを含む場合は、必ず A["ノードテキスト(記号)"] のようにダブルクォーテーションで囲んでください）
        （★必須条件★：各工程の間に、推測される所要時間を「A -->|約1分30秒| B」のように必ず表示してください。＊時間＊分＊秒 の形式で記載すること）
        </div>
    </div>
    <div class="flex-1 lg:w-1/2">
        <h2 class="text-xl mb-4 border-b pb-2 text-orange-600 font-bold">🚀 自動化後のフロー図 (全体の短縮時間: 〇秒)</h2>
        <!-- ※見出しの「〇秒」の部分は、自動化した場合の全体の総実行時間（例：約3秒 など）を必ず入れてください -->
        <div class="mermaid bg-slate-50 p-4 rounded shadow">
        graph TD
        （ここに自動化後のフローを記載。同様に A["ノード名"] の構文を厳守）
        （★必須条件★：ここでも工程間に「A -->|約1秒| B」のように短縮後の時間を表示してください）
        </div>
    </div>
</div>

<div class="mt-12 bg-orange-50 p-6 rounded-xl border border-orange-100">
    <h2 class="text-2xl mb-4 text-orange-800 font-bold">💡 具体的な自動化案とステップ</h2>
    （現在の処理に対する具体的なDX化案をStep1, Step2...と順に記載してください。
    【最重要制約】自動化の手段として、RPA（UiPathやWinActorなど）は絶対に使用・提案しないでください。最優先で「Python」を用いた自動化スクリプトの開発を提案し、次点で「Excel VBA」によるマクロ化を提案してください。）
</div>

【システム詳細ログ】
{system_log_text}
"""
    file_dx = os.path.join(report_dir, f"dx_analysis_report_{target_date}.html")
    if os.path.exists(file_dx):
        print(f"[スキップ] 既にDX分析レポートが存在します: {file_dx}")
        if progress_callback: progress_callback(30, "DX分析レポートは既存のためスキップしました (2/3)...")
    else:
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
            with open(file_dx, "w", encoding="utf-8") as f:
                f.write(template_dx)
            print(f"[完了] 詳細DXモード生成: {file_dx}")
            if progress_callback: progress_callback(30, "DX分析レポートの生成完了 (2/3)...")
        except Exception as e:
            print(f"[エラー] 詳細DXモード: {e}")
            if progress_callback: progress_callback(30, f"[エラー] DX分析: {e}")


    # ==========================================
    # 3. 生ログへのAI要約付与（CSV出力）
    # ==========================================
    if system_log:
        with open(system_log, "r", encoding="utf-8-sig") as f:
            first_line = f.readline()
            
        if "AI解析要約" in first_line:
            print(f"[スキップ] 既にAI解析要約済みのCSVです: {system_log}")
            if progress_callback: progress_callback(40, "CSVの全行AI要約は既存のためスキップしました (3/3)...")
        else:
            if progress_callback: progress_callback(35, "CSVの全行AI要約を開始します（ログが長い場合は数分かかります）...")
            with open(system_log, "r", encoding="utf-8-sig") as f:
                all_lines = f.readlines()
                
            header = all_lines[0]
            data_lines = all_lines[1:]
            chunk_size = 20
            
            final_csv_text = "Timestamp,ActiveApp,EventType,TargetName,Metadata,AI解析要約\n"
            
            print(f"[AI] システムログ（全{len(data_lines)}行）の解析を {chunk_size} 行ずつ分割して実行中...")
            
            for i in range(0, len(data_lines), chunk_size):
                chunk = data_lines[i:i+chunk_size]
                raw_system_log = "".join(chunk)
                
                prompt_csv = f"""
以下のシステム操作ログ（カンマ区切りのCSV形式）は、ユーザーがPC（主にExcel）で操作した生の記録です。
このログを元に、各行の右端に新しく「AI解析要約」という列を追加して、人間らしい操作の解説を追記したCSVを出力してください。

【厳守事項】
- 出力は必ずプレーンなCSV形式テキストのみ（```csvなどのMarkdown記号や、ヘッダー行は一切不要）としてください。データ行のみを出力してください。
- システム部が自動化（RPA等）の仕様を組むために必要なため、AI解析要約には、「何を」「どう入力したか（キーボード入力、コピペ等）」を具体的に記述してください。
  ❌ダメな例：「データを手入力している」
  ⭕良い例：「セルA1に『ノートPC』とキーボードで手入力している」
  ⭕良い例：「セルC8に『=VLOOKUP(...)』という数式を入力している」
  ※Metadata列に含まれている Value や Formula、Keys の情報を必ず拾い上げて解説に含めること。
- 【重要：連続操作の集約】
  縦方向のドラッグコピーや、連続したセルへの同種の入力（例: E8, E9, E10... と続く操作）など、明らかに一連の反復作業であると見なせるログ行は、**1行にまとめて（圧縮して）出力**してください。
  集約した場合、**Metadata列には必ず「Cell:A9:A15」など、操作対象のセル範囲を残してください**（これがないと図解化の際にエラーになります）。
  解説文は「セルE8～E15に『2026/8/14』を連続してドラッグ入力している」のように表現してください。
  ⚠️注意：集約する場合でも、「日付らしきデータ」のように抽象化せず、必ず【どんな具体的な値や数式（『ノートPC』や『15000』など）】を入力・コピーしたのかを省略せずに明記してください。
- 【重要：キー操作の強烈なアピール】
  Metadataに「Keys:」が含まれている場合、「Ctrl+C」「Ctrl+V」を用いたコピペ操作や、具体的な文字のタイピング（例:「notepc[enter]」など）が行われたことを、自動化要件定義のために**強烈にアピールして（詳細に）**記述してください。

【元のCSVデータ】
{raw_system_log}
"""
                try:
                    res_csv = client.models.generate_content(model=GEMINI_MODEL, contents=prompt_csv)
                    csv_text = res_csv.text.replace("```csv", "").replace("```", "").strip()
                    
                    # ヘッダーが含まれていたら削除する
                    csv_lines = csv_text.split("\n")
                    if csv_lines and "Timestamp" in csv_lines[0]:
                        csv_lines = csv_lines[1:]
                        
                    final_csv_text += "\n".join(csv_lines) + "\n"
                    print(f"  - チャンク {i//chunk_size + 1}/{(len(data_lines)+chunk_size-1)//chunk_size} 完了")
                except Exception as e:
                    print(f"  [エラー] チャンク {i//chunk_size + 1}: {e}")
            
            try:
                # 元のsystem_logは上書きせず、別ファイルとして保存する
                evaluated_log = system_log.replace("system_log_", "system_log_ai_evaluated_")
                with open(evaluated_log, "w", encoding="utf-8-sig") as f:
                    f.write(final_csv_text.strip() + "\n")
                print(f"[完了] AI要約付きCSV生成（フルサイズ）: {evaluated_log}")
            except Exception as e:
                print(f"[エラー] AI要約付きCSV書き込み: {e}")

if __name__ == "__main__":
    generate_reports()
