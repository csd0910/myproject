import win32com.client
import os

file1 = r"C:\Users\フォーレスト026\MyProject\業務自動化分析ツール\0807長期欠品管理表.xlsb"
file2 = r"C:\Users\フォーレスト026\MyProject\業務自動化分析ツール\0810長期欠品管理表.xlsb"

excel = win32com.client.Dispatch("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False

print(f"Comparing: {os.path.basename(file1)} -> {os.path.basename(file2)}")

try:
    wb1 = excel.Workbooks.Open(file1, UpdateLinks=0, ReadOnly=True)
    wb2 = excel.Workbooks.Open(file2, UpdateLinks=0, ReadOnly=True)
    
    sheets1 = {sh.Name: sh for sh in wb1.Sheets}
    sheets2 = {sh.Name: sh for sh in wb2.Sheets}
    
    all_sheets = set(sheets1.keys()).union(set(sheets2.keys()))
    
    for sh_name in all_sheets:
        if sh_name not in sheets1:
            print(f"【新規シート】: {sh_name}")
            continue
        if sh_name not in sheets2:
            print(f"【削除シート】: {sh_name}")
            continue
            
        sh1 = sheets1[sh_name]
        sh2 = sheets2[sh_name]
        
        try:
            used1 = sh1.UsedRange
            used2 = sh2.UsedRange
            
            # 範囲を合わせる
            max_r = max(used1.Rows.Count, used2.Rows.Count)
            max_c = max(used1.Columns.Count, used2.Columns.Count)
            
            # 大きすぎるシートはスキップするか制限する（メモリ対策）
            if max_r > 50000 or max_c > 100:
                print(f"[{sh_name}] シートが大きすぎます (Rows:{max_r}, Cols:{max_c})")
                
            rng1 = sh1.Range(sh1.Cells(1, 1), sh1.Cells(max_r, max_c))
            rng2 = sh2.Range(sh2.Cells(1, 1), sh2.Cells(max_r, max_c))
            
            val1 = rng1.Value
            val2 = rng2.Value
            fml1 = rng1.Formula
            fml2 = rng2.Formula
            
            if not isinstance(val1, tuple) or not isinstance(val2, tuple):
                continue
                
            diff_count = 0
            diff_samples = []
            
            for r in range(len(val1)):
                for c in range(len(val1[0])):
                    v1 = val1[r][c]
                    v2 = val2[r][c]
                    fm1 = fml1[r][c]
                    fm2 = fml2[r][c]
                    
                    if v1 != v2 or fm1 != fm2:
                        diff_count += 1
                        if len(diff_samples) < 15:
                            # Excelの列文字変換
                            col_str = sh1.Cells(1, c+1).Address.split('$')[1]
                            cell_addr = f"{col_str}{r+1}"
                            
                            diff_type = []
                            if v1 != v2: diff_type.append(f"値変更 ({v1} -> {v2})")
                            if fm1 != fm2: diff_type.append(f"数式変更 ({fm1} -> {fm2})")
                            
                            diff_samples.append(f"  {cell_addr}: " + ", ".join(diff_type))
                            
            if diff_count > 0:
                print(f"\n--- シート【{sh_name}】の変更点 ({diff_count}箇所) ---")
                for samp in diff_samples:
                    print(samp)
                if diff_count > 15:
                    print(f"  ...他 {diff_count - 15} 箇所")
            else:
                print(f"\n--- シート【{sh_name}】--- 変更なし")
                
        except Exception as e:
            print(f"[{sh_name}] エラー: {e}")
            
finally:
    try:
        wb1.Close(False)
        wb2.Close(False)
    except:
        pass
    excel.Quit()
