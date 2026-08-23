import win32com.client
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

wb_path = r"C:\Users\フォーレスト026\MyProject\業務自動化分析ツール\0810長期欠品管理表.xlsb"
excel = win32com.client.Dispatch("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False

try:
    wb = excel.Workbooks.Open(wb_path, ReadOnly=True)
    for i in range(1, wb.Sheets.Count + 1):
        print(f"Index {i}: {wb.Sheets(i).Name}")
finally:
    wb.Close(False)
    excel.Quit()
