import win32com.client
import os

wb_path = r"C:\Users\フォーレスト026\MyProject\業務自動化分析ツール\AutoAnalysisLogs\0810長期欠品管理表_VisualReport.xlsb"

excel = win32com.client.Dispatch("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False

try:
    wb = excel.Workbooks.Open(wb_path)
    try:
        sh = wb.Sheets("①長期欠品")
    except Exception:
        sh = wb.Sheets(9)
        
    # 既存の図形（古い吹き出し）をすべて削除して綺麗にする
    for shp in sh.Shapes:
        shp.Delete()
        
    # テキスト, 対象セル, Xズレ, Yズレ, 幅, 高さ
    balloons = [
        (
            "【手順1・2：最新データの流し込みと数式展開】\n"
            "マニュアル：品目・未入荷を上書きし、数式(I3～AF3)をオートフィルして値貼り付け\n"
            "操作：CSVコピペ → Ctrl+Shift+Downで数十万行オートフィル\n"
            "結果：約530万箇所更新（※1分フリーズ）\n"
            "取得元：I列は「品目」シートの「発注ランク」を取得\n\n"
            "【作業担当者記載欄】\n\n\n", 
            "I3", -200, 150, 420, 140
        ),
        (
            "【判定用データ取得：有効在庫・発注残】\n"
            "マニュアル手順2による自動計算\n"
            "取得元：「品目」シートからQ列(有効在庫)とO列(発注残)を取得\n\n"
            "【作業担当者記載欄】\n\n\n",
            "P3", -50, 220, 350, 120
        ),
        (
            "【判定用データ取得：納期回答】\n"
            "マニュアル手順2による自動計算\n"
            "取得元：「未入荷」シートからV列(納期回答)を取得\n\n"
            "【作業担当者記載欄】\n\n\n",
            "V3", 50, 280, 350, 120
        ),
        (
            "【手順3・4：フラグ判定① (終売による解除)】\n"
            "フラグ条件：I列(発注ランク) が『9997』なら『解除OK』\n"
            "操作：AC～AE列が解除OKのものをCtrl+F等で探し、\n"
            "　　　商品コードと商品名を「②長期欠品解除」へコピペ移動\n\n"
            "【作業担当者記載欄】\n\n\n",
            "AC3", -350, 320, 400, 140
        ),
        (
            "【手順3・4：フラグ判定② (有効在庫あり)】\n"
            "フラグ条件①：Q列(有効在庫)>0 かつ V列(納期)空欄 なら『解除OK』\n"
            "フラグ条件②：Q列>0 だが V列あり かつ O列(発注残)=0 なら『在庫に余裕あればOK』\n"
            "※『在庫に余裕あればOK』は目視確認対象\n\n"
            "【作業担当者記載欄】\n\n\n",
            "AD3", -50, 380, 420, 140
        ),
        (
            "【手順3・4：フラグ判定③ (受発注・入荷済)】\n"
            "フラグ条件：S列(手配区分)=2 かつ N列(入荷済)>0 \n"
            "　　　　　　かつ Q列(有効在庫)=0 かつ V列(納期)空欄\n"
            "全て満たせば『解除OK』\n\n"
            "【作業担当者記載欄】\n\n\n",
            "AE3", 250, 320, 380, 140
        )
    ]
    
    for text, cell_addr, off_x, off_y, width, height in balloons:
        try:
            cell = sh.Range(cell_addr)
            
            left = cell.Left + off_x
            top = cell.Top + off_y
            
            # msoShapeRectangle (四角形)
            box = sh.Shapes.AddShape(1, left, top, width, height)
            box.TextFrame.Characters().Text = text
            box.TextFrame.Characters().Font.Name = "Meiryo UI"
            box.TextFrame.Characters().Font.Size = 10
            box.TextFrame.Characters().Font.Color = 0 # 黒
            
            # 背景色: 白, 枠線: 黒 (添付画像と同じデザイン)
            box.Fill.ForeColor.RGB = 16777215 # 白
            box.Line.ForeColor.RGB = 0 # 黒
            box.Line.Weight = 1.25
            
            # テキストの配置設定（左揃え、上揃え）
            box.TextFrame.HorizontalAlignment = 1 # xlHAlignLeft
            box.TextFrame.VerticalAlignment = 1 # xlVAlignTop
            
            # ガイド線 (直線+矢印)
            cell_cx = cell.Left + cell.Width / 2
            cell_cy = cell.Top + cell.Height
            if off_y < 0:
                cell_cy = cell.Top
                
            # ガイド線の起点を吹き出しの上辺中央にする
            box_cx = left + width / 2
            box_cy = top
            if off_y < 0:
                box_cy = top + height
                
            arrow = sh.Shapes.AddLine(box_cx, box_cy, cell_cx, cell_cy)
            arrow.Line.EndArrowheadStyle = 3 # 三角形
            arrow.Line.ForeColor.RGB = 0 # 黒
            arrow.Line.Weight = 1
            arrow.ZOrder(1) # 背面へ移動
        except Exception as e:
            print(f"Error adding shape to {cell_addr}: {e}")
            
    wb.Save()
    print("Detailed balloons added successfully.")
except Exception as e:
    print(f"Workbook error: {e}")
finally:
    wb.Close(False)
    excel.Quit()
