import glob
import os
import re
from bs4 import BeautifulSoup

def integrate_html_reports(html_files, output_path):
    if not html_files:
        print("結合するHTMLファイルがありません")
        return

    # ベースとなるHTML構造を作成
    base_html = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>統合DX抽出レポート</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({startOnLoad:true});</script>
    <style>
        body { background-color: #f8fafc; color: #334155; }
        .day-container { margin-bottom: 4rem; }
    </style>
</head>
<body class="p-6 md:p-12">
    <h1 class="text-4xl font-extrabold text-slate-800 mb-8 text-center">DX業務分析レポート (統合版)</h1>
"""
    
    script_content = ""
    
    for idx, html_file in enumerate(html_files):
        with open(html_file, 'r', encoding='utf-8') as f:
            html = f.read()
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # main container を抽出
        container = soup.find('div', class_='max-w-7xl')
        if not container:
            continue
            
        # Canvas IDとJS変数を重複しないように書き換え
        for canvas in container.find_all('canvas'):
            old_id = canvas.get('id', '')
            if old_id:
                new_id = f"{old_id}_{idx}"
                canvas['id'] = new_id
                
                # スクリプト内の対象IDも書き換えたいが、スクリプトは <script> タグにある
        
        # このHTML内の最後の <script> タグにChart.jsの初期化コードが入っているはず
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'new Chart' in script.string:
                js_code = script.string
                js_code = js_code.replace("document.getElementById('appChart')", f"document.getElementById('appChart_{idx}')")
                js_code = js_code.replace("document.getElementById('taskChart')", f"document.getElementById('taskChart_{idx}')")
                js_code = js_code.replace("const ctxApp =", f"const ctxApp_{idx} =")
                js_code = js_code.replace("const ctxTask =", f"const ctxTask_{idx} =")
                js_code = js_code.replace("new Chart(ctxApp", f"new Chart(ctxApp_{idx}")
                js_code = js_code.replace("new Chart(ctxTask", f"new Chart(ctxTask_{idx}")
                script_content += f"\n// --- Script for {os.path.basename(html_file)} ---\n" + js_code
                
        # div にクラスを追加して追加
        container['class'] = container.get('class', []) + ['day-container']
        base_html += str(container) + "\n"

    base_html += f"""
    <script>
    {script_content}
    </script>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(base_html)
    print(f"統合HTMLレポートを出力しました: {output_path}")

if __name__ == '__main__':
    html_files = [
        r"C:\AutoAnalysisLogs\daily_reports\dx_analysis_report_20260810.html",
        r"C:\AutoAnalysisLogs\daily_reports\dx_analysis_report_20260811.html"
    ]
    valid_files = [f for f in html_files if os.path.exists(f)]
    out_path = r"C:\AutoAnalysisLogs\daily_reports\DX_Integrated_Report.html"
    integrate_html_reports(valid_files, out_path)
