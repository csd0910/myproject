import win32com.client
import os
import glob
import csv
import traceback
import re
import sys

def create_visual_report(log_dir=None):
    print("【Ver 3】Excelシート図解レポート（全ログ強制描画版）の生成を開始します...")
    
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__))
    if not log_dir:
        log_dir = os.path.join(base_dir, "activity_logs")
    
    csv_files = glob.glob(os.path.join(log_dir, "system_log_ai_evaluated_*.csv"))
    if not csv_files:
        print("評価済みCSVが見つかりません。")
        return
    csv_file = max(csv_files, key=os.path.getmtime)
    print(f"対象ログ: {os.path.basename(csv_file)}")
    
    operations = []
    # pandasではなく標準csvモジュールでエラーを回避して読み込む
    with open(csv_file, "r", encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0 or len(row) < 6:
                continue
            
            time_str = row[0]
            app = row[1]
            event = row[2]
            title = row[3]
            meta = row[4]
            desc = row[5] if len(row) > 5 else ""
            
            if "Excel" in title or "EXCEL.EXE" in app:
                wb_name = title.split(" - ")[0].strip() if " - " in title else ""
                operations.append({
                    "time": time_str,
                    "event": event,
                    "wb": wb_name,
                    "meta": meta,
                    "desc": desc
                })
                
    if not operations:
        print("Excelの操作履歴が見つかりませんでした。")
        return

    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    
    try:
        # 開いている・対象となるワークブックを探す
        wb_names = set([op["wb"] for op in operations if op["wb"] and op["wb"] != "EXCEL.EXE"])
        
        for wb_name in wb_names:
            wb_path = os.path.join(base_dir, wb_name)
            if not os.path.exists(wb_path):
                continue
                
            print(f"対象ファイル: {wb_name} に図解を描画します...")
            wb = excel.Workbooks.Open(wb_path)
            
            # シートごとの時系列オフセット（不明なセルアドレス用）
            timeline_row_offset = {}
            
            for op in operations:
                if op["wb"] and op["wb"] != wb_name and op["wb"] != "EXCEL.EXE":
                    continue
                    
                time_str = op["time"]
                event = op["event"]
                meta = op["meta"]
                desc = op["desc"]
                
                # デフォルトはアクティブシート
                sheet_name = wb.ActiveSheet.Name
                # 説明文からシート名を推測
                sheet_match = re.search(r"シート[『「【](.+?)[』」】]", desc)
                if sheet_match:
                    sheet_name = sheet_match.group(1)
                elif "シート:" in meta:
                    sm = re.search(r"シート:([^,]+)", meta)
                    if sm: sheet_name = sm.group(1)

                cell_ref = None
                match = re.search(r"Cell:([A-Za-z0-9:]+)", meta)
                if match:
                    cell_ref = match.group(1).strip()
                    if ":" in cell_ref:
                        cell_ref = cell_ref.split(":")[0]
                
                try:
                    sh = wb.Sheets(sheet_name)
                except Exception:
                    sh = wb.ActiveSheet
                    
                sheet_name = sh.Name
                if sheet_name not in timeline_row_offset:
                    timeline_row_offset[sheet_name] = 2

                # セルが特定できない場合はタイムラインとして右側（AE列）に並べる
                is_timeline = False
                try:
                    if cell_ref:
                        cell = sh.Range(cell_ref)
                    else:
                        raise Exception("No cell")
                except Exception:
                    # アドレス不正や指定なしの場合はAE列にオフセット配置
                    cell = sh.Cells(timeline_row_offset[sheet_name], 31) # 31=AE
                    timeline_row_offset[sheet_name] += 6
                    is_timeline = True

                left = cell.Left + cell.Width + 10
                if is_timeline:
                    left = cell.Left
                top = cell.Top
                
                text = f"[{time_str}] {event}\n{desc}"
                height = max(70, len(text) * 1.5)
                
                try:
                    box = sh.Shapes.AddShape(105, left, top, 280, height)
                    box.TextFrame.Characters().Text = text
                    box.TextFrame.Characters().Font.Name = "Meiryo UI"
                    box.TextFrame.Characters().Font.Size = 9
                    box.TextFrame.Characters().Font.Color = 0
                    
                    box.Fill.ForeColor.RGB = 13434879
                    box.Line.ForeColor.RGB = 39423
                    box.Line.Weight = 1.5
                    
                    if not is_timeline:
                        arrow = sh.Shapes.AddLine(cell.Left + cell.Width, cell.Top + 10, left, top + 10)
                        arrow.Line.EndArrowheadStyle = 3
                        arrow.Line.ForeColor.RGB = 39423
                        arrow.Line.Weight = 1.5
                except Exception:
                    pass

            out_path = os.path.join(log_dir, wb_name.replace(".xlsx", "_VisualReport.xlsx").replace(".xlsb", "_VisualReport.xlsb"))
            wb.SaveAs(out_path)
            wb.Close(SaveChanges=False)
            print(f"図解レポートを出力しました: {out_path}")
            
    except Exception as e:
        print(f"Excel操作エラー: {e}")
        traceback.print_exc()
    finally:
        if excel:
            excel.Quit()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        create_visual_report(sys.argv[1])
    else:
        create_visual_report()
