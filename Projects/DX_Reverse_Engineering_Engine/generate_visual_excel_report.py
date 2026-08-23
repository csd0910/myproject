import win32com.client
import os
import glob
import csv
import traceback
import re
import sys
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

def create_visual_report(log_dir=None, target_file_path=None):
    print("【Ver 3】Excelシート図解レポート（全ログ強制描画版）の生成を開始します...")
    
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__))
    if not log_dir:
        log_dir = os.path.join(base_dir, "activity_logs")
    
    # まずAI解析済みのファイルを優先して探す
    ai_csv_files = glob.glob(os.path.join(log_dir, "system_log_ai_evaluated_*.csv"))
    if ai_csv_files:
        csv_file = max(ai_csv_files, key=os.path.getmtime)
    else:
        # なければ通常のシステムログを探す
        csv_files = glob.glob(os.path.join(log_dir, "system_log_*.csv"))
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
                wb_name = title.split(" - ")[0].strip() if " - " in title else title.strip()
                # SheetChangeなどで単に「Excel」となる場合、メタデータのFile:から復元
                if wb_name.lower() == "excel":
                    fm = re.search(r"File:([^\,]+)", meta)
                    if fm:
                        wb_name = os.path.basename(fm.group(1).strip())
                    else:
                        wb_name = ""

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
    # 大幅な高速化のための設定
    try:
        excel.ScreenUpdating = False
        excel.EnableEvents = False
        excel.Calculation = -4135 # xlCalculationManual
    except:
        pass
    
    try:
        # 開いている・対象となるワークブックを探す
        if target_file_path and os.path.exists(target_file_path):
            wb_names = [os.path.basename(target_file_path)]
            target_map = {os.path.basename(target_file_path): target_file_path}
        else:
            wb_names = set([op["wb"] for op in operations if op["wb"] and op["wb"] != "EXCEL.EXE"])
            target_map = {name: os.path.join(base_dir, name) for name in wb_names}
        
        for wb_name in wb_names:
            wb_path = target_map.get(wb_name)
            if not wb_path or not os.path.exists(wb_path):
                continue
                
            print(f"対象ファイル: {wb_name} に図解を描画します...")
            wb = excel.Workbooks.Open(wb_path)
            
            # シートごとの時系列オフセット（不明なセルアドレス用）
            timeline_row_offset = {}
            
            for op_index, op in enumerate(operations, 1):
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
                match = re.search(r"Cell:([\$A-Za-z0-9:]+)", meta)
                if match:
                    cell_ref = match.group(1).strip().replace("$", "")
                    if ":" in cell_ref:
                        cell_ref = cell_ref.split(":")[0]
                
                try:
                    sh = wb.Sheets(sheet_name)
                except Exception:
                    sh = wb.ActiveSheet
                    
                sheet_name = sh.Name
                if sheet_name not in timeline_row_offset:
                    timeline_row_offset[sheet_name] = 2
                # 厳密な重なり回避のためのリストとカウント
                if "drawn_boxes" not in locals():
                    drawn_boxes = {}
                if sheet_name not in drawn_boxes:
                    drawn_boxes[sheet_name] = []
                    
                if "cell_draw_counts" not in locals():
                    cell_draw_counts = {}

                # セルが特定できない場合はタイムラインとして右側（AE列）に並べる
                is_timeline = False
                try:
                    if cell_ref:
                        cell = sh.Range(cell_ref)
                    else:
                        raise Exception("No cell")
                except Exception:
                    cell = sh.Cells(timeline_row_offset[sheet_name], 31) # 31=AE
                    timeline_row_offset[sheet_name] += 6
                    is_timeline = True
                
                cell_key = f"{sh.Name}!{cell.Address}"
                draw_count = cell_draw_counts.get(cell_key, 0)
                cell_draw_counts[cell_key] = draw_count + 1

                # セルの直上にステップ番号の丸を描画 (9 = msoShapeOval)
                try:
                    circle = sh.Shapes.AddShape(9, cell.Left - 5, cell.Top - 5, 20, 20)
                    circle.Fill.ForeColor.RGB = 16777215 # 白
                    circle.Line.ForeColor.RGB = 0 # 黒
                    circle.TextFrame.Characters().Text = str(op_index)
                    circle.TextFrame.Characters().Font.Color = 0 # 黒
                    circle.TextFrame.Characters().Font.Bold = True
                    circle.TextFrame.HorizontalAlignment = 2 # 中央揃え
                    circle.TextFrame.VerticalAlignment = 2 # 中央揃え
                except Exception:
                    pass

                # 吹き出しのテキストとサイズ（要約せずフルテキストで表示）
                text = f"【STEP {op_index}】\n{desc}"
                box_width = 300
                # 文字数に応じて高さを確保する
                box_height = max(50, len(text) * 1.5)

                # 画面右側にリストとして整列配置する
                current_left = 850
                
                # 最初は上から配置し、前の箱の高さに合わせて次のTopを決める
                if op_index == 1:
                    current_top = 20
                else:
                    # 雑な固定間隔ではなく、直前に配置した箱の底を基準にするためのオフセット
                    # ここでは一旦、op_indexを用いた動的計算で余裕を持たせる
                    pass
                    
                # 前の箱と重ならないようにY座標を管理
                if "next_top" not in locals() or op_index == 1:
                    next_top = 20
                    
                current_top = next_top
                next_top = current_top + box_height + 10
                
                try:
                    # 1 = 四角形 (msoShapeRectangle)
                    box = sh.Shapes.AddShape(1, current_left, current_top, box_width, box_height)
                    box.TextFrame.Characters().Text = text
                    box.TextFrame.Characters().Font.Name = "Meiryo UI"
                    # ご要望通り文字サイズを小さくする
                    box.TextFrame.Characters().Font.Size = 7.5
                    box.TextFrame.Characters().Font.Color = 0 # 黒
                    
                    # 背景は白に
                    box.Fill.ForeColor.RGB = 16777215 # 白
                    box.Line.ForeColor.RGB = 0 # 黒
                    box.Line.Weight = 1.0
                    
                    box.TextFrame.HorizontalAlignment = 1 # 左揃え
                    box.TextFrame.VerticalAlignment = 2 # 中央揃え
                except Exception:
                    pass

            out_path = os.path.join(log_dir, wb_name.replace(".xlsx", "_VisualReport_v2.xlsx").replace(".xlsb", "_VisualReport_v2.xlsb"))
            try:
                wb.SaveAs(out_path)
            except Exception as e:
                print(f"Excel保存エラー: {e}")
                out_path = out_path.replace("_v2", "_v3")
                wb.SaveAs(out_path)
            wb.Close(SaveChanges=False)
            print(f"図解レポートを出力しました: {out_path}")
            
    except Exception as e:
        print(f"Excel操作エラー: {e}")
        traceback.print_exc()
    finally:
        if excel:
            try:
                excel.ScreenUpdating = True
                excel.EnableEvents = True
                excel.Calculation = -4105 # xlCalculationAutomatic
            except:
                pass
            excel.Quit()

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        create_visual_report(sys.argv[1])
    else:
        create_visual_report()
