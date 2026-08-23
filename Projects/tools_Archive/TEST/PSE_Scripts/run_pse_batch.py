import os
import sys

# Ensure the module can be imported
sys.path.append(r"c:\Users\フォーレスト026\MyProject\tools\TEST\PSE_Scripts")
from csv_pse_processor import process_pse_csv

master_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\PSE判定用ルールマスタ.csv"
exclude_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\除外マスタ.csv"
output_dir = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\20260526"

files_to_process = [
    r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\0512 大分類46と47と48　商品一覧(em310).csv",
    r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\0512 大分類9と11と13　商品一覧(em310).csv"
]

print(f"Output Directory: {output_dir}")
for file_path in files_to_process:
    print(f"\n=================================")
    print(f"Processing File: {file_path}")
    print(f"=================================")
    try:
        process_pse_csv(file_path, master_path, exclude_path, output_dir=output_dir)
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

print("\nAll tasks finished.")
