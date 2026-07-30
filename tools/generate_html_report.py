import os
import csv
import datetime
import json
from google import genai

# ==========================================
# 設定項目
# ==========================================
# 環境変数 GEMINI_API_KEY から読み込む
API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
# ==========================================

client = genai.Client(api_key=API_KEY)

def generate_html_report():
    log_dir = os.path.join(os.path.dirname(__file__), "activity_logs")
    report_dir = os.path.join(os.path.dirname(__file__), "daily_reports")
    os.makedirs(report_dir, exist_ok=True)
    
    # 処理対象の日付（デフォルトは今日）
    target_date = datetime.datetime.now().strftime("%Y%m%d")
    csv_file = os.path.join(log_dir, f"activity_log_{target_date}.csv")
    
    if not os.path.exists(csv_file):
        print(f"本日（{target_date}）のログファイルが見つかりません。")
        return
        
    print(f"本日のログ ({csv_file}) を読み込んでいます...")
    
    log_text = ""
    app_durations = {}
    total_seconds = 0
    
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ai_col = row.get("AI作業解析内容", "")
            # ノイズ（離席、未解析、エラー）を除外
            if ai_col and "離席" not in ai_col and "エラー" not in ai_col and "Unknown" not in ai_col:
                start = row.get("開始日時", "").split(" ")[-1]
                end = row.get("終了日時", "").split(" ")[-1]
                app = row.get("アプリケーション名", "")
                
                # 滞在時間の集計
                dur_str = row.get("滞在時間", "0秒").replace("秒", "")
                try:
                    dur = int(dur_str)
                    app_durations[app] = app_durations.get(app, 0) + dur
                    total_seconds += dur
                except:
                    pass
                
                log_text += f"[{start} - {end}] {app}: {ai_col}\n"
                
    if not log_text or total_seconds == 0:
        print("有効なAI解析ログがありません。")
        return

    # Chart.js 用のデータを準備
    chart_labels = []
    chart_data = []
    sorted_apps = sorted(app_durations.items(), key=lambda x: x[1], reverse=True)
    for app, dur in sorted_apps:
        chart_labels.append(app)
        chart_data.append(dur)
        
    chart_labels_json = json.dumps(chart_labels)
    chart_data_json = json.dumps(chart_data)
        
    print("Geminiに業務分析と日報の生成を依頼しています（数秒お待ちください）...")
    
    prompt = f"""
あなたはエグゼクティブ向けの優秀な業務コンサルタントです。
以下の【本日の作業ログ】を分析し、HTMLの形式で出力してください。
※重要: ```html などのコードブロック（バッククォート記号）は絶対に含めず、純粋なHTMLタグのみをプレーンテキストとして返してください。

【出力要件】
1. 細かい作業（PDF変換ツールの操作、フォルダの移動、一瞬の検索など）は完全に無視し、1日の「大きな成果物・主要な業務（例：〇〇の稟議書の作成、見積もりの作成など）」が何であったかにフォーカスして、大局的かつ極めて簡潔に要約してください。
2. 箇条書きがダラダラと続くのはNGです。1つの大きな業務につき、数行の読みやすい文章でまとめる「エグゼクティブ・サマリー」形式にしてください。

<h2 class="text-2xl mb-4 border-b border-gray-300 pb-2 text-blue-700 font-bold">📊 業務サマリーと分析</h2>
本日の主要な業務内容と、そこから読み取れる傾向やアドバイスを短く記述してください。

<h2 class="text-2xl mt-8 mb-4 border-b border-gray-300 pb-2 text-teal-700 font-bold">📝 主要業務ダイジェスト</h2>
時系列の細かい羅列ではなく、本日遂行した「大きな業務カテゴリ」を <h3> タグ（見出し）で数個だけ挙げ、その中で何が行われたかを大局的に要約してください。細かすぎる行動履歴は不要です。

【本日の作業ログ】
{log_text}
"""
    
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        
        # AIからの返答からマークダウンのコードブロックなどを除去
        ai_html_content = response.text.replace("```html", "").replace("```", "").strip()
        
        # HTMLテンプレート（クリーンなライトモード・高視認性デザイン）
        html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>業務分析レポート - {target_date}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Noto+Sans+JP:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{ 
            background-color: #f8fafc; 
            color: #334155; 
            font-family: 'Inter', 'Noto Sans JP', sans-serif; 
        }}
        .card {{ 
            background: #ffffff; 
            border: 1px solid #e2e8f0; 
            border-radius: 1rem; 
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}
        h2 {{ font-weight: 700; letter-spacing: 0.02em; }}
        h3 {{ color: #0f172a; font-weight: 700; margin-top: 1.5rem; margin-bottom: 0.75rem; font-size: 1.15rem; border-left: 4px solid #3b82f6; padding-left: 0.75rem; }}
        ul {{ list-style-type: disc; margin-left: 1.5rem; margin-bottom: 1.5rem; }}
        li {{ margin-bottom: 0.5rem; color: #475569; }}
        p {{ line-height: 1.7; margin-bottom: 1rem; color: #475569; font-size: 1rem; }}
    </style>
</head>
<body class="p-6 md:p-12">
    <div class="max-w-6xl mx-auto">
        <header class="mb-12 text-center">
            <h1 class="text-3xl md:text-4xl font-extrabold text-slate-800 mb-3 tracking-tight">
                Activity Intelligence Report
            </h1>
            <p class="text-slate-500 font-medium tracking-widest uppercase text-sm">
                DATE: {target_date} &nbsp;|&nbsp; TOTAL TIME: {total_seconds // 60}m {total_seconds % 60}s
            </p>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
            <!-- Left Column: Charts -->
            <div class="lg:col-span-4 space-y-8">
                <div class="card p-8">
                    <h2 class="text-xl mb-6 border-b border-gray-200 pb-3 text-slate-800 font-bold">⏱️ アプリケーション使用割合</h2>
                    <div class="relative w-full" style="aspect-ratio: 1/1;">
                        <canvas id="appPieChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- Right Column: AI Analysis -->
            <div class="lg:col-span-8 space-y-8">
                <div class="card p-8">
                    {ai_html_content}
                </div>
            </div>
        </div>
    </div>

    <script>
        // 視認性の高いシンプルなPieチャート
        const ctx = document.getElementById('appPieChart').getContext('2d');
        new Chart(ctx, {{
            type: 'pie',
            data: {{
                labels: {chart_labels_json},
                datasets: [{{
                    data: {chart_data_json},
                    backgroundColor: [
                        '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b'
                    ],
                    borderColor: '#ffffff',
                    borderWidth: 2,
                    hoverOffset: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ 
                        position: 'bottom', 
                        labels: {{ 
                            color: '#475569',
                            font: {{ family: "'Inter', sans-serif", size: 13 }},
                            padding: 15
                        }} 
                    }},
                    tooltip: {{
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#0f172a',
                        bodyColor: '#334155',
                        borderColor: '#e2e8f0',
                        borderWidth: 1,
                        padding: 12,
                        callbacks: {{
                            label: function(context) {{
                                let label = context.label || '';
                                if (label) {{
                                    label += ': ';
                                }}
                                if (context.parsed !== null) {{
                                    let mins = Math.floor(context.parsed / 60);
                                    let secs = context.parsed % 60;
                                    label += mins > 0 ? mins + '分' + secs + '秒' : secs + '秒';
                                }}
                                return label;
                            }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        
        report_file = os.path.join(report_dir, f"daily_report_{target_date}.html")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html_template)
            
        print("\n[完了] HTMLグラフィックレポートの生成が完了しました！\n")
        print(f"以下のファイルをWebブラウザ（ChromeやEdge）でダブルクリックして開いてください：\n👉 {report_file}\n")
        
    except Exception as e:
        print(f"日報の生成中にエラーが発生しました: {e}")

if __name__ == "__main__":
    generate_html_report()
