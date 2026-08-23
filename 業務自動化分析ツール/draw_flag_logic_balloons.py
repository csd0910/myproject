import win32com.client
import os

wb_path = r"C:\Users\フォーレスト026\MyProject\業務自動化分析ツール\AutoAnalysisLogs\0810長期欠品管理表_VisualReport.xlsb"

excel = win32com.client.Dispatch("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False

try:
    wb = excel.Workbooks.Open(wb_path)
    
    # ①長期欠品 シート (名前でエラーになる場合はインデックス9を使用)
    try:
        sh = wb.Sheets("①長期欠品")
    except Exception:
        sh = wb.Sheets(9)
    
    # テキスト, 対象セル, Xズレ, Yズレ
    balloons = [
        ("【VLOOKUP取得①: 終売確認】\n「品目」シートから発注ランクを取得。\n※9997なら終売", "I3", -60, 100),
        ("【VLOOKUP取得②: 在庫確認】\n「品目」から有効在庫(Q)と発注残(O)等を取得。", "P3", -40, -80),
        ("【VLOOKUP取得③: 納期確認】\n「未入荷」シートから仕入先の納期回答を取得", "V3", -30, 110),
        ("【フラグ判定①: 終売】\n数式: =IF(I3=9997, \"解除OK\", \"NG\")\n判定: I列が9997なら無条件で解除。", "AC3", -180, -90),
        ("【フラグ判定②: 有効在庫】\n数式: =IF(AND(Q3>0,V3=\"\")...\n判定: 有効在庫(Q)>0 かつ 納期(V)が空欄なら解除", "AD3", -50, 130),
        ("【フラグ判定③: 受発注済】\n数式: =IF(AND(S3=2,N3>0...\n判定: 受発注品(S=2) かつ 入荷済(N)>0等で解除", "AE3", 80, -110)
    ]
    
    for text, cell_addr, off_x, off_y in balloons:
        try:
            cell = sh.Range(cell_addr)
            
            left = cell.Left + off_x
            top = cell.Top + off_y
            width = 240
            height = 70
            
            # msoShapeRoundedRect (角丸四角形)
            box = sh.Shapes.AddShape(105, left, top, width, height)
            box.TextFrame.Characters().Text = text
            box.TextFrame.Characters().Font.Name = "Meiryo UI"
            box.TextFrame.Characters().Font.Size = 9
            box.TextFrame.Characters().Font.Color = 0
            box.TextFrame.Characters().Font.Bold = True
            
            # 背景色: 薄い黄色, 枠線: 赤
            box.Fill.ForeColor.RGB = 13434879
            box.Line.ForeColor.RGB = 255
            box.Line.Weight = 2
            
            # セルから吹き出しへのガイド線
            cell_cx = cell.Left + cell.Width / 2
            cell_cy = cell.Top + cell.Height
            if off_y < 0:
                cell_cy = cell.Top
                
            box_cx = left + width / 2
            box_cy = top
            if off_y < 0:
                box_cy = top + height
                
            arrow = sh.Shapes.AddLine(box_cx, box_cy, cell_cx, cell_cy)
            arrow.Line.EndArrowheadStyle = 3 # 三角形
            arrow.Line.ForeColor.RGB = 255
            arrow.Line.Weight = 1.5
            arrow.ZOrder(1) # msoSendToBack
        except Exception as e:
            print(f"Error adding shape to {cell_addr}: {e}")
            
    wb.Save()
    print("Balloons added successfully.")
except Exception as e:
    print(f"Workbook error: {e}")
finally:
    wb.Close(False)
    excel.Quit()
