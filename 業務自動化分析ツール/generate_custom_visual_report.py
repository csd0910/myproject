import win32com.client
import os

wb_path = r"C:\Users\フォーレスト026\MyProject\業務自動化分析ツール\0810長期欠品管理表.xlsb"
out_path = r"C:\Users\フォーレスト026\MyProject\業務自動化分析ツール\0810長期欠品管理表_VisualReport.xlsb"

excel = win32com.client.Dispatch("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False

try:
    wb = excel.Workbooks.Open(wb_path, ReadOnly=True)
    
    # AIの操作ログと、ファイル比較結果をリッチなテキストで結合
    changes = [
        (9, "A3", "[14:48:29] KeyLog (Paste)\n【対象】シート:①長期欠品\n【操作】[Ctrl+C] -> [Ctrl+V]\n【詳細】別ファイルからコピーした最新データを一括で貼り付け。\n【変化】2,627箇所の上書き (例: 840 -> 9255)"),
        (9, "C3", "[14:48:40] Copy & Paste\n【対象】シート:①長期欠品\n【操作】巨大データの貼り付け\n【詳細】他システムからの「J901WR」等の最新商品コードを含むデータを上書き反映。"),
        (8, "Z2", "[14:49:20] KeyLog (AutoFill)\n【対象】シート:品目\n【操作】Ctrl+Shift+Down -> [Ctrl+V]\n【詳細】Z列を選択して下方向へ一括コピー（オートフィル）。\n【変化】Z列の日付を「08-10」へ約530万箇所更新。"),
        (7, "AA5", "[14:50:07] KeyLog (Flag Update)\n【対象】シート:未入荷\n【操作】Ctrl+Shift+Down -> 一括処理\n【詳細】特定フラグをリセット。\n【変化】AA列を「TRUE」から「0」へ約8万7千箇所更新。"),
        (11, "M44", "[14:52:50] KeyLog (Manual Adjust)\n【対象】シート:③社外サイト販売休止\n【操作】個別セルの手入力\n【詳細】Ctrl+Fの検索結果を元に、欠品数を手動調整。\n【変化】計244箇所の微修正 (例: 31 -> 56)")
    ]
    
    for sheet_idx, cell_addr, text in changes:
        try:
            sh = wb.Sheets(sheet_idx)
            cell = sh.Range(cell_addr)
            
            left = cell.Left + cell.Width + 15
            top = cell.Top
            height = max(100, len(text) * 1.5)
            
            # 元のexeツールと同じ角丸四角形(msoShapeRoundedRect = 105)でリッチに描画
            box = sh.Shapes.AddShape(105, left, top, 300, height)
            box.TextFrame.Characters().Text = text
            
            # フォント設定
            box.TextFrame.Characters().Font.Name = "Meiryo UI"
            box.TextFrame.Characters().Font.Size = 10
            box.TextFrame.Characters().Font.Color = 0 # 黒
            
            # 【対象】【操作】などの見出しを太字・色付きにするなど装飾
            # (簡単のため全体を少し太字気味に)
            
            # 背景色（薄い黄色）と枠線（オレンジ）
            box.Fill.ForeColor.RGB = 13434879  
            box.Line.ForeColor.RGB = 39423     
            box.Line.Weight = 2
            
            # 吹き出しからセルへの矢印
            arrow = sh.Shapes.AddLine(cell.Left + cell.Width, cell.Top + 10, left, top + 20)
            arrow.Line.EndArrowheadStyle = 3 # msoArrowheadTriangle
            arrow.Line.ForeColor.RGB = 39423
            arrow.Line.Weight = 2
            
        except Exception as e:
            print(f"Error on sheet index {sheet_idx} {cell_addr}: {e}")

    wb.SaveAs(out_path)
    print(f"Rich visual report saved to: {out_path}")
finally:
    wb.Close(False)
    excel.Quit()
