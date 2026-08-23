import win32com.client
import os

def create_test_file():
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    
    wb = excel.Workbooks.Add()
    
    # Sheet 1: マスタデータ (Product Master)
    ws_master = wb.Sheets(1)
    ws_master.Name = "商品マスタ"
    data = [
        ["商品コード", "商品名", "単価"],
        ["A001", "ノートPC", 120000],
        ["A002", "マウス", 3500],
        ["A003", "キーボード", 8000],
        ["A004", "モニター", 25000],
    ]
    for row_idx, row_data in enumerate(data, start=1):
        for col_idx, value in enumerate(row_data, start=1):
            ws_master.Cells(row_idx, col_idx).Value = value
            
    # Sheet 2: 入力用シート
    ws_input = wb.Sheets.Add()
    ws_input.Name = "発注データ入力"
    input_data = [
        ["発注日", "商品コード", "商品名", "単価", "数量", "合計金額", "備考"],
        ["2026/08/10", "A001", "", "", 2, "", "急ぎ（手入力）"],
        ["2026/08/10", "A003", "", "", 5, "", ""],
        ["2026/08/10", "A002", "", "", 10, "", ""],
        ["2026/08/10", "", "", "", "", "", "ここにコードと数量を手入力"],
    ]
    for row_idx, row_data in enumerate(input_data, start=1):
        for col_idx, value in enumerate(row_data, start=1):
            ws_input.Cells(row_idx, col_idx).Value = value
            
    # VLOOKUPと計算式の挿入
    for r in range(2, 6):
        ws_input.Cells(r, 3).Formula = f'=IF(B{r}="","",VLOOKUP(B{r},商品マスタ!A:C,2,FALSE))'
        ws_input.Cells(r, 4).Formula = f'=IF(B{r}="","",VLOOKUP(B{r},商品マスタ!A:C,3,FALSE))'
        ws_input.Cells(r, 6).Formula = f'=IF(OR(D{r}="",E{r}=""),"",D{r}*E{r})'
        
    path = os.path.abspath("テスト発注業務.xlsx")
    if os.path.exists(path):
        os.remove(path)
    wb.SaveAs(path)
    wb.Close()
    excel.Quit()
    print(f"Created: {path}")

if __name__ == "__main__":
    create_test_file()
