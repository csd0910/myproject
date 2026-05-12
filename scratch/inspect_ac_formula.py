import openpyxl

path = r'C:\Users\フォーレスト026\Desktop\伊藤作業用\残業調査\20260427_ログ表示結果-20260416175217 - コピー.xlsx'
try:
    # data_only=False にして数式をそのまま読み込む
    wb = openpyxl.load_workbook(path, data_only=False, read_only=True)
    ws = wb['管理部提出用']
    print(f'Checking formulas in sheet: {ws.title}')
    for r_idx, row in enumerate(ws.iter_rows(max_row=100), 1):
        # AC列(29列目)を特定
        if len(row) >= 29:
            cell = row[28] # Index 28 = Col 29
            if cell.value:
                print(f"Row {r_idx}, Col 29 (AC) Value/Formula: {cell.value}")
except Exception as e:
    print(f"Error: {e}")
