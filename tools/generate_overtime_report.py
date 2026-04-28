import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import time
import openpyxl
from docx import Document
from dotenv import load_dotenv
from google import genai

# ---------------------------------------------------------
# 初期設定 (Gemini API)
# ---------------------------------------------------------
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)
api_key = os.getenv("GEMINI_API_KEY")
client = None
if api_key:
    client = genai.Client(api_key=api_key)

# ---------------------------------------------------------
# GUI ダイアログ関数
# ---------------------------------------------------------
def select_paths():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    messagebox.showinfo("ファイル選択 (1/3)", "全社員の「勤怠マスタ（Excel）」を1つ選択してください。")
    excel_path = filedialog.askopenfilename(title="勤怠マスタ(Excel)を選択", filetypes=[("Excelファイル", "*.xlsx *.xls")])
    if not excel_path: return None, None, None

    messagebox.showinfo("ファイル選択 (2/3)", "対象者の「PC操作ログ（CSV）」を【複数選択】してください。\n※ShiftキーやCtrlキーを押しながらクリックすると複数ファイルを選べます。")
    csv_paths = filedialog.askopenfilenames(title="PC操作ログ(CSV)を複数選択", filetypes=[("CSVファイル", "*.csv")])
    if not csv_paths: return None, None, None

    messagebox.showinfo("フォルダ選択 (3/3)", "生成された報告書（Word）を保存する「出力先フォルダ」を選択してください。")
    output_dir = filedialog.askdirectory(title="報告書の保存先フォルダを選択")
    if not output_dir: return None, None, None

    return excel_path, csv_paths, output_dir

# ---------------------------------------------------------
# 解析補助関数
# ---------------------------------------------------------
def get_audit_target_dates(excel_path, sheet_name='管理部提出用'):
    """ExcelのAC列(29)に「〇」が入力されている「監査対象行」の氏名と日付(MM/DD)を抽出する"""
    try:
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        if sheet_name not in wb.sheetnames:
            return set()
        ws = wb[sheet_name]
        
        name_col_idx = None
        date_col_idx = None
        
        for row in ws.iter_rows(min_row=1, max_row=5):
            for cell in row:
                val = str(cell.value).strip() if cell.value else ''
                if '氏名' in val or '名前' in val:
                    name_col_idx = cell.column
                if '日付' in val:
                    date_col_idx = cell.column
            if name_col_idx and date_col_idx:
                break
                
        if not name_col_idx or not date_col_idx:
            name_col_idx = 2
            date_col_idx = 3
            
        targets = set()
        ac_col_idx = 29  # AC列 (A=1, Z=26, AA=27, AB=28, AC=29)
        
        for row_idx in range(2, ws.max_row + 1):
            ac_cell = ws.cell(row=row_idx, column=ac_col_idx)
            val = str(ac_cell.value).strip() if ac_cell.value else ''
            
            # 丸記号（〇、○、O）などが入力されていれば監査対象とする
            if val in ['〇', '○', 'o', 'O', '丸', '対象']:
                name_val = str(ws.cell(row=row_idx, column=name_col_idx).value or '').strip()
                date_val = ws.cell(row=row_idx, column=date_col_idx).value
                if name_val and date_val:
                    try:
                        # 年のズレによる不一致を防ぐため %m/%d だけで抽出
                        dt = pd.to_datetime(date_val).strftime('%m/%d')
                        name_clean = name_val.replace(' ', '').replace('　', '').replace('社員', '')
                        targets.add((name_clean, dt))
                    except:
                        pass
        return targets
    except Exception as e:
        print(f"監査対象日（AC列の〇）の抽出に失敗しました: {e}")
        return set()

def extract_app_name(path):
    path = str(path).upper()
    if pd.isna(path) or path.strip() == '' or path == 'NAN': 
        return 'その他（システム処理・待機等）'
    
    filename = path.split('\\')[-1]
    
    if 'EXCEL.EXE' in filename or '.XLS' in filename:
        return 'Excel作業（EXCEL.EXE）'
    elif 'CHROME' in filename or 'MSEDGE' in filename or 'HTTP' in path:
        return 'サイボウズ・Web（msedge.exe / chrome.exe）'
    elif 'WINWORD.EXE' in filename:
        return 'Word作業（WINWORD.EXE）'
    else:
        return 'その他（バックグラウンド処理・他）'

def parse_duration(duration_str):
    if pd.isna(duration_str): return pd.Timedelta(seconds=0)
    try:
        parts = str(duration_str).split(':')
        if len(parts) == 3:
            return pd.Timedelta(hours=int(parts[0]), minutes=int(parts[1]), seconds=int(parts[2]))
    except: pass
    return pd.Timedelta(seconds=0)

def load_csv_safely(filepath):
    for enc in ['cp932', 'utf-8', 'utf-8-sig', 'shift_jis']:
        try:
            return pd.read_csv(filepath, encoding=enc, engine='python', on_bad_lines='skip')
        except Exception:
            pass
    raise Exception("対応する文字コード(cp932, utf-8等)で読み込めませんでした。")

def find_col(df, keywords, fallback_index=None):
    for col in df.columns:
        for kw in keywords:
            if kw in col:
                return col
    if fallback_index is not None and fallback_index < len(df.columns):
        return df.columns[fallback_index]
    return df.columns[0]

def get_val(row, col_name, fallback_index=None):
    if col_name in row.index: return str(row[col_name])
    if fallback_index is not None and fallback_index < len(row.index): return str(row.iloc[fallback_index])
    return ''

# ---------------------------------------------------------
# Gemini API 連携関数
# ---------------------------------------------------------
def generate_summary_with_ai(log_df, col_title, col_path):
    if not client:
        return "APIキー未設定のため生成スキップ", "APIキー未設定"
    
    log_lines = []
    for _, row in log_df.iterrows():
        t = str(row.get(col_title, ''))
        p = str(row.get(col_path, ''))
        if t and t != 'nan' and '電源' not in t:
            log_lines.append(f"[{p}] {t}")
    
    unique_logs = list(dict.fromkeys(log_lines))[:100]
    log_text = "\n".join(unique_logs)
    
    if not log_text.strip():
        return "具体的な作業ログなし", "特記事項なし"
        
    prompt = f"""
あなたは企業の監査担当です。以下のPC操作ログから、作業の詳細と総括サマリーを生成してください。
【操作ログ】
{log_text}

【出力フォーマット指示】
必ず以下の2つのセクションに分けて出力してください。不要な挨拶等は一切不要です。

■作業詳細
（Excelのファイル名やシステム名を元に、何を作業していたか箇条書きで簡潔に整理）

■サマリー
（上記を踏まえ、どんな業務を行っていたかを客観的で厳格な2〜3行の自然な日本語で総括してください）
"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            text = response.text
            
            details, summary = "詳細のパースに失敗しました。", "サマリーのパースに失敗しました。"
            if "■作業詳細" in text and "■サマリー" in text:
                parts = text.split("■サマリー")
                details = parts[0].replace("■作業詳細", "").strip()
                summary = parts[1].strip()
            else:
                summary = text.strip()
                
            return details, summary
            
        except Exception as e:
            if '503' in str(e) or 'UNAVAILABLE' in str(e):
                if attempt < max_retries - 1:
                    print(f"  -> [API混雑] サーバー混雑のため、5秒待機して再実行します... (試行 {attempt+1}/{max_retries})")
                    time.sleep(5)
                else:
                    print(f"  -> [APIエラー詳細] 複数回のリトライに失敗しました: {e}")
                    return "AI生成エラー: サーバー混雑", "現在AIサーバーが非常に混雑しています。時間を空けて再度お試しください。"
            else:
                print(f"  -> [APIエラー詳細] {e}")
                return f"AI生成エラー: {str(e)}", "エラーのため生成できませんでした"

# ---------------------------------------------------------
# メイン処理（レポート一括生成）
# ---------------------------------------------------------
def generate_reports(excel_path, csv_paths, output_dir):
    print("勤怠マスタの読み込みを開始します（色の解析中...）")
    
    # セルに色が塗られている「監査対象」の氏名と日付を抽出
    audit_targets = get_audit_target_dates(excel_path)
    if not audit_targets:
        print("[警告] マスタのAC列に「〇」（監査対象）が見つかりませんでした。全件処理します。")
    else:
        print(f"監査対象として {len(audit_targets)} 件の「〇」データを検出しました！ (例: {list(audit_targets)[:3]})")
    
    # 1. マスタ読み込みと整形
    df_master = pd.read_excel(excel_path, sheet_name='管理部提出用')
    df_master.columns = [str(c).strip().replace('\u3000', '').replace(' ', '') for c in df_master.columns]
    name_col = find_col(df_master, ['氏名', '名前'], 1)
    
    print(f"\n合計 {len(csv_paths)} 個のログファイルを連続処理します。\n")

    # 2. 複数のCSVファイルをループで処理
    for csv_path in csv_paths:
        filename_csv = os.path.basename(csv_path)
        print(f"========== 処理開始: {filename_csv} ==========")
        
        # ファイル名から対象者を推測（マスタの全氏名と照合して安全に取得）
        target_name_guess = None
        for name in df_master[name_col].dropna().unique():
            name_clean = str(name).replace(' ', '').replace('　', '').replace('社員', '')
            if name_clean and name_clean in filename_csv.replace(' ', '').replace('　', ''):
                target_name_guess = str(name)
                break
                
        # フォールバック
        if not target_name_guess:
            target_name_guess = filename_csv.split('_')[0] if '_' in filename_csv else filename_csv[:2]
            
        df_target_master = df_master[df_master[name_col].str.contains(target_name_guess, na=False)].copy()
        
        if len(df_target_master) == 0:
            print(f"  -> [スキップ] 勤怠マスタから対象者「{target_name_guess}」が見つかりませんでした。")
            continue
            
        date_col = find_col(df_target_master, ['日付'], 2)
        df_target_master['日付_master'] = pd.to_datetime(df_target_master[date_col])
        
        try:
            df_log = load_csv_safely(csv_path)
        except Exception as e:
            print(f"  -> [エラー] CSV読み込み失敗: {e}")
            continue

        df_log.columns = [str(c).strip().replace('\u3000', '').replace(' ', '') for c in df_log.columns]
        
        col_datetime = find_col(df_log, ['日時'], 6)
        col_duration = find_col(df_log, ['期間', '操作時間'], 10)
        col_path = find_col(df_log, ['パス', 'URL', 'ＵＲＬ'], 11)
        col_title = find_col(df_log, ['タイトル'], 12)
        
        try:
            df_log['日時'] = pd.to_datetime(df_log[col_datetime])
            df_log['日付_log'] = df_log['日時'].dt.normalize()
        except Exception as e:
            print(f"  -> [エラー] 日時データが不正です: {e}")
            continue

        df_log['操作時間'] = df_log[col_duration].apply(parse_duration)
        df_log['アプリ分類'] = df_log[col_path].apply(extract_app_name)
        
        daily_log = df_log.groupby('日付_log').agg(PC電源ON=('日時', 'min'), PC電源OFF=('日時', 'max')).reset_index()
        
        merged_df = pd.merge(df_target_master, daily_log, left_on='日付_master', right_on='日付_log', how='left')
        
        col_status = find_col(df_target_master, ['勤務日種別', '区分'], 2)
        col_jiyu = find_col(df_target_master, ['事由'], 11)
        col_start = find_col(df_target_master, ['打刻・出勤', '出勤'], 3)
        col_end = find_col(df_target_master, ['打刻・退勤', '退勤'], 4)

        # 3. ログが存在する日ごとにWordを作成
        processed_count = 0
        for index, row in merged_df.iterrows():
            if pd.isna(row['PC電源ON']):
                continue
                
            date_str = row['日付_master'].strftime('%Y/%m/%d')
            date_md = row['日付_master'].strftime('%m/%d') # 年ズレ防止用
            target_fullname = get_val(row, name_col)
            target_fullname_clean = target_fullname.replace(' ', '').replace('　', '').replace('社員', '')
            
            # --- 監査対象（AC列の〇印）のみを狙い撃ち ---
            if audit_targets and (target_fullname_clean, date_md) not in audit_targets:
                print(f"    -> [スキップ] {date_str} はマスタのAC列に〇がないためスキップしました。")
                continue
                
            processed_count += 1
            shift_info = f"{get_val(row, col_status)} {get_val(row, col_jiyu)}".strip().replace('nan', '')
            flags = []
            
            # --- 異常検知ロジック ---
            if ('休' in shift_info):
                flags.append(f"【休日稼働】シフトは「{shift_info}」ですがPCが稼働しています")
            
            if 'テレワーク' in shift_info:
                flags.append(f"【テレワーク検知】社外からの稼働です")

            start_str = get_val(row, col_start)
            end_str = get_val(row, col_end)
            
            if ('休' not in shift_info):
                if start_str and start_str != 'nan':
                    try:
                        work_start = pd.to_datetime(f"{date_str} {start_str}")
                        if row['PC電源ON'] < work_start - pd.Timedelta(minutes=10):
                            diff = int((work_start - row['PC電源ON']).total_seconds() / 60)
                            flags.append(f"【早出疑義】出勤打刻より {diff}分早く PCが起動({row['PC電源ON'].strftime('%H:%M')})しています")
                    except: pass

                if end_str and end_str != 'nan':
                    try:
                        work_end = pd.to_datetime(f"{date_str} {end_str}")
                        if row['PC電源OFF'] > work_end + pd.Timedelta(minutes=10):
                            diff = int((row['PC電源OFF'] - work_end).total_seconds() / 60)
                            flags.append(f"【残業疑義】退勤打刻より {diff}分遅くまで PCが稼働({row['PC電源OFF'].strftime('%H:%M')})しています")
                    except: pass

            day_logs = df_log[df_log['日付_log'] == row['日付_log']]
            app_summary = day_logs.groupby('アプリ分類')['操作時間'].sum().sort_values(ascending=False)
            
            print(f"    [{date_str}] Gemini APIでAIサマリーを生成中... (監査対象)")
            time.sleep(2)
            ai_details, ai_summary = generate_summary_with_ai(day_logs, col_title, col_path)
            
            doc = Document()
            doc.add_heading('残業調査報告書', 0)
            
            yobi = ["月", "火", "水", "木", "金", "土", "日"][row['日付_master'].weekday()]
            
            is_holiday = ('休' in shift_info)
            if end_str and end_str != 'nan':
                end_time_display = end_str
            elif is_holiday:
                end_time_display = "休日"
            else:
                end_time_display = "記録なし"

            calc_start = row['PC電源ON']
            calc_end = row['PC電源OFF']
            
            if not is_holiday and end_str and end_str != 'nan':
                try:
                    work_end_dt = pd.to_datetime(f"{date_str} {end_str}")
                    if row['PC電源OFF'] > work_end_dt:
                        calc_start = work_end_dt
                except: pass

            diff_sec = (calc_end - calc_start).total_seconds()
            if diff_sec < 0: diff_sec = 0
            h, rem = divmod(int(diff_sec), 3600)
            m, _ = divmod(rem, 60)
            est_time_str = f"{calc_start.strftime('%H:%M')} ～ {calc_end.strftime('%H:%M')}（約{h}時間{m:02d}分）"
            
            doc.add_paragraph(f"対象者：{target_fullname}")
            doc.add_paragraph(f"{row['日付_master'].strftime('%Y/%m/%d')}（{yobi}）")
            doc.add_paragraph(f"退勤打刻時間：{end_time_display}")
            doc.add_paragraph(f"PCの稼働：{row['PC電源ON'].strftime('%H:%M')} ～ {row['PC電源OFF'].strftime('%H:%M')}（最終）")
            doc.add_paragraph(f"作業していたと推測される時間：{est_time_str}")
            
            doc.add_heading('判定結果', level=2)
            if not flags: doc.add_paragraph("・問題なし（適正な稼働）")
            else:
                for f in flags: doc.add_paragraph(f"・{f}")
                    
            doc.add_heading('PC稼働状況（アプリ別集計）', level=2)
            table = doc.add_table(rows=1, cols=2)
            table.style = 'Table Grid'
            table.rows[0].cells[0].text = 'アプリケーション'
            table.rows[0].cells[1].text = '合計時間（概算）'
            
            count = 0
            for app_name, td in app_summary.items():
                if count >= 5 or td.total_seconds() == 0: break
                row_cells = table.add_row().cells
                row_cells[0].text = app_name
                h_app, rem_app = divmod(int(td.total_seconds()), 3600)
                m_app, s_app = divmod(rem_app, 60)
                row_cells[1].text = f"{h_app:02}:{m_app:02}:{s_app:02}"
                count += 1
                
            doc.add_heading('作業詳細', level=2)
            doc.add_paragraph(ai_details)
            doc.add_heading('サマリー', level=2)
            doc.add_paragraph(ai_summary)
            
            target_name_short = target_fullname.replace('社員', '').replace(' ', '').replace('　', '')
            safe_date = date_str.replace('/', '')
            filename = f"残業調査報告書_{target_name_short}_{safe_date}.docx"
            filepath = os.path.join(output_dir, filename)
            
            try:
                doc.save(filepath)
                print(f"      -> 保存完了: {filename}")
            except PermissionError:
                alt_filename = f"残業調査報告書_{target_name_short}_{safe_date}_再生成.docx"
                alt_filepath = os.path.join(output_dir, alt_filename)
                try:
                    doc.save(alt_filepath)
                    print(f"      -> [警告] ファイルが使用中のため、別名で保存しました: {alt_filename}")
                except Exception as e:
                    print(f"      -> [エラー] 保存に失敗しました: {e}")
            
            time.sleep(1)

        if processed_count == 0:
            print(f"    -> [スキップ] このファイルのログには、マスタ上で赤文字となっている監査対象日が含まれていませんでした。")

    print("\n全てのログファイルの処理が完了しました！出力先フォルダをご確認ください。")

def main():
    excel_path, csv_paths, output_dir = select_paths()
    if excel_path and csv_paths and output_dir:
        generate_reports(excel_path, csv_paths, output_dir)
    else:
        print("処理がキャンセルされました。")

if __name__ == "__main__":
    main()
