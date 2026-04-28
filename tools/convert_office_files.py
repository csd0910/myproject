import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import win32com.client
from pathlib import Path
from datetime import datetime
from tqdm import tqdm  # 進捗バー用
import time

def convert_files():
    # 1. フォルダ選択ダイアログを表示
    root = tk.Tk()
    root.withdraw()
    target_dir = filedialog.askdirectory(title="変換したいファイルが入ったフォルダを選択してください")
    
    if not target_dir:
        print("キャンセルされました。")
        return

    # 2. 変換対象のファイルをリストアップ（事前に数を把握する）
    target_extensions = [".xls", ".doc"]
    all_files = os.listdir(target_dir)
    conversion_targets = [f for f in all_files if os.path.splitext(f)[1].lower() in target_extensions]
    
    total_count = len(conversion_targets)
    if total_count == 0:
        messagebox.showinfo("通知", "対象のファイル (.xls, .doc) が見つかりませんでした。")
        return

    # 3. 保存先フォルダの作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(target_dir, f"converted_{timestamp}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"\n開始時刻: {datetime.now().strftime('%H:%M:%S')}")
    print(f"対象件数: {total_count} 件")
    print(f"保存先  : {output_dir}\n")

    # Officeアプリの起動準備
    excel = None
    word = None
    converted_count = 0

    # 進捗バーの初期化
    with tqdm(total=total_count, desc="変換進捗", unit="file", dynamic_ncols=True) as pbar:
        try:
            for filename in conversion_targets:
                file_path = os.path.join(target_dir, filename)
                ext = os.path.splitext(filename)[1].lower()
                base_name = os.path.splitext(filename)[0]

                try:
                    # --- Excelの変換 (.xls -> .xlsx) ---
                    if ext == ".xls":
                        if excel is None: 
                            excel = win32com.client.Dispatch("Excel.Application")
                            excel.Visible = False
                            excel.DisplayAlerts = False # 警告を非表示
                        
                        abs_path = os.path.abspath(file_path)
                        wb = excel.Workbooks.Open(abs_path)
                        new_path = os.path.join(output_dir, base_name + ".xlsx")
                        wb.SaveAs(os.path.abspath(new_path), FileFormat=51) # 51 = xlsx
                        wb.Close()

                    # --- Wordの変換 (.doc -> .docx) ---
                    elif ext == ".doc":
                        if word is None:
                            word = win32com.client.Dispatch("Word.Application")
                            word.Visible = False
                            word.DisplayAlerts = 0 # 0 = wdAlertsNone

                        abs_path = os.path.abspath(file_path)
                        doc = word.Documents.Open(abs_path)
                        new_path = os.path.join(output_dir, base_name + ".docx")
                        doc.SaveAs2(os.path.abspath(new_path), FileFormat=16) # 16 = docx
                        doc.Close()

                    converted_count += 1
                
                except Exception as file_error:
                    print(f"\n[エラー] スキップしました ({filename}): {file_error}")
                
                # 進捗バーを1つ進める
                pbar.update(1)

            messagebox.showinfo("完了", f"すべての処理が完了しました！\n\n成功: {converted_count} / {total_count} 件\n保存先: {output_dir}")

        except Exception as e:
            messagebox.showerror("致命的エラー", f"処理を継続できませんでした:\n{str(e)}")
        
        finally:
            # アプリを確実に終了させる
            if excel: 
                excel.Quit()
            if word: 
                word.Quit()
            print(f"\n終了時刻: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    convert_files()
