import win32com.client
import os

def analyze_and_save(file_path=None, output_path=None):
    excel = win32com.client.Dispatch("Excel.Application")
    excel_was_visible = excel.Visible
    excel.Visible = False
    
    wb = None
    opened_by_script = False
    
    try:
        if file_path and os.path.exists(file_path):
            wb = excel.Workbooks.Open(file_path, ReadOnly=True)
            opened_by_script = True
            print(f"[{os.path.basename(file_path)}] の解析を開始します...")
        else:
            try:
                wb = excel.ActiveWorkbook
                if not wb:
                    print("エラー: アクティブなExcelブックが見つかりません。")
                    return
                print(f"[アクティブブック: {wb.Name}] の解析を開始します...")
            except Exception:
                print("エラー: Excelに接続できません。")
                return

        output_lines = [f"# Excel数式・関数 リバースエンジニアリング解析レポート", f"対象ファイル: {wb.Name}\n"]
        
        for sh in wb.Sheets:
            sheet_header_added = False
            
            try:
                used_range = sh.UsedRange
                try:
                    formula_cells = used_range.SpecialCells(-4123)
                except Exception:
                    continue
                
                if formula_cells:
                    if not sheet_header_added:
                        output_lines.append(f"## シート名: 【{sh.Name}】")
                        sheet_header_added = True
                    
                    for area in formula_cells.Areas:
                        for cell in area:
                            address = str(cell.Address).replace("$", "")
                            formula = str(cell.Formula)
                            output_lines.append(f"- セル{address}　計算式、関数：{formula}")
                            
            except Exception as e:
                output_lines.append(f"- シート「{sh.Name}」の解析中にエラー: {e}")
        
        if output_path:
            report_path = output_path
        else:
            output_dir = os.path.dirname(file_path) if file_path else os.getcwd()
            report_path = os.path.join(output_dir, "formulas_extracted_report.md")
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(output_lines))
            
        print(f"解析完了！レポートを出力しました: {report_path}")

    except Exception as e:
        print(f"システムエラー: {e}")
    finally:
        if opened_by_script and wb:
            wb.Close(False)
        if opened_by_script:
            excel.Quit()
        else:
            excel.Visible = excel_was_visible

extract_formulas_from_excel = analyze_and_save

if __name__ == "__main__":
    target_file = r"C:\Users\フォーレスト026\MyProject\業務自動化分析ツール\0810長期欠品管理表.xlsb"
    analyze_and_save(target_file)
