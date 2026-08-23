import win32com.client
import os

wb_path = r"C:\Users\フォーレスト026\MyProject\業務自動化分析ツール\AutoAnalysisLogs\0810長期欠品管理表_VisualReport.xlsb"

excel = win32com.client.Dispatch("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False

try:
    wb = excel.Workbooks.Open(wb_path)
    
    # シートごとの吹き出し定義
    # (シート名またはインデックス, テキスト, 対象セル, Xズレ, Yズレ, 幅, 高さ)
    sheet_balloons = [
        ("品目", 
         "【CSV流し込み：品目情報の更新】\n"
         "マニュアル：ツール「品目情報_新」のCSVを全体に上書き\n"
         "操作ログ：別ファイルから Ctrl+C でコピー、A1セルから Ctrl+V で貼り付け\n"
         "変化した数値：Z列の日付データなど、シート全体で約530万箇所が一気に更新\n\n"
         "【作業担当者記載欄】\n\n",
         "Z2", -150, 80, 420, 130),
         
        ("未入荷",
         "【CSV流し込み：未入荷リストの更新】\n"
         "マニュアル：A～T列から前日の値を消し、当日の値を値貼り付け\n"
         "操作ログ：古いデータ削除後、Ctrl+C と Ctrl+V で最新データをペースト\n"
         "変化した数値：AA列等のフラグ・日付を含め、約8.7万箇所のデータが更新\n\n"
         "【作業担当者記載欄】\n\n",
         "T2", -200, 100, 420, 130),
         
        ("②長期欠品解除",
         "【解除フラグ対象リストの移動】\n"
         "マニュアル：「①長期欠品」シートで『解除OK』となった品目をコピーし貼り付け\n"
         "操作ログ：「①長期欠品」から対象を目視検索し、Ctrl+C と Ctrl+V で手動ペースト\n"
         "変化した数値：C列(商品コード)やD列(商品名)に、計5,649箇所のデータが新規追加\n\n"
         "【作業担当者記載欄】\n\n",
         "C5", 100, 80, 450, 130),
         
        ("③社外サイト販売休止",
         "【社外サイト欠品数の手動調整】\n"
         "マニュアル：目視による微修正\n"
         "操作ログ：矢印キーやマウスでセルを移動しながら、欠品数をキーボードで手入力\n"
         "変化した数値：M列などの欠品数（例: 31→56など）が計244箇所更新\n\n"
         "【作業担当者記載欄】\n\n",
         "M5", -100, 100, 400, 130)
    ]
    
    for sheet_name, text, cell_addr, off_x, off_y, width, height in sheet_balloons:
        try:
            try:
                sh = wb.Sheets(sheet_name)
            except Exception:
                # 念のためインデックスでのフォールバック
                if sheet_name == "品目": sh = wb.Sheets(8)
                elif sheet_name == "未入荷": sh = wb.Sheets(7)
                elif sheet_name == "②長期欠品解除": sh = wb.Sheets(10)
                elif sheet_name == "③社外サイト販売休止": sh = wb.Sheets(11)
                else: continue
            
            # 既存の図形削除
            for shp in sh.Shapes:
                shp.Delete()
                
            cell = sh.Range(cell_addr)
            left = cell.Left + off_x
            top = cell.Top + off_y
            
            # 吹き出し描画
            box = sh.Shapes.AddShape(1, left, top, width, height) # 1 = 四角形
            box.TextFrame.Characters().Text = text
            box.TextFrame.Characters().Font.Name = "Meiryo UI"
            box.TextFrame.Characters().Font.Size = 10
            box.TextFrame.Characters().Font.Color = 0
            
            box.Fill.ForeColor.RGB = 16777215 # 白
            box.Line.ForeColor.RGB = 0 # 黒
            box.Line.Weight = 1.25
            
            box.TextFrame.HorizontalAlignment = 1
            box.TextFrame.VerticalAlignment = 1
            
            # ガイド線
            cell_cx = cell.Left + cell.Width / 2
            cell_cy = cell.Top + cell.Height
            if off_y < 0:
                cell_cy = cell.Top
                
            box_cx = left + width / 2
            box_cy = top
            if off_y < 0:
                box_cy = top + height
                
            arrow = sh.Shapes.AddLine(box_cx, box_cy, cell_cx, cell_cy)
            arrow.Line.EndArrowheadStyle = 3
            arrow.Line.ForeColor.RGB = 0
            arrow.Line.Weight = 1
            arrow.ZOrder(1)
            
            print(f"Added balloon to sheet: {sh.Name}")
        except Exception as e:
            print(f"Error on sheet {sheet_name}: {e}")
            
    wb.Save()
    print("All other sheets updated successfully.")
except Exception as e:
    print(f"Workbook error: {e}")
finally:
    wb.Close(False)
    excel.Quit()
