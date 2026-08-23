import os
import subprocess

def run_cmd(cmd):
    print(f"\n[RUNNING] {cmd}")
    subprocess.run(cmd, shell=True, check=True)

# 1. Patch process_46_47_48.py
run_cmd("python patch.py")

# 2. Process PSE for 9,11,13
print("\n--- PSE Processing for 9,11,13 ---")
run_cmd("python csv_pse_processor.py")

# 3. Process PSE for 46,47,48
print("\n--- PSE Processing for 46,47,48 ---")
run_cmd("python process_46_47_48.py")

# 4. Split by supplier
print("\n--- Splitting by supplier ---")
# We need to split both. Let's write a python snippet inline to split 46,47,48 as well
split_script = """
import pandas as pd
import os

def split_by_supplier(file_path, output_dir, supplier_col_idx):
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return

    print(f"INFO: 仕入先ごとに分割しています: {file_path}")
    df = pd.read_csv(file_path, encoding='cp932')
    supplier_col = df.columns[supplier_col_idx]
    
    suppliers = df[supplier_col].unique()
    base_name = os.path.basename(file_path).replace(".csv", "")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for supplier in suppliers:
        if pd.isna(supplier) or str(supplier).strip() == "":
            supplier_name = "仕入先不明"
        else:
            supplier_name = str(supplier).replace("/", "／").replace("\\\\", "＼").replace(":", "：").replace("*", "＊").strip()
        
        new_file_name = f"{base_name}_{supplier_name}.csv"
        save_path = os.path.join(output_dir, new_file_name)
        
        supplier_df = df[df[supplier_col] == supplier]
        supplier_df.to_csv(save_path, index=False, encoding='cp932')
        print(f"  -> 保存完了: {new_file_name} ({len(supplier_df)}件)")

# Split 9,11,13 (Supplier is col index 10)
target_1 = r"C:\\Users\\フォーレスト026\\Desktop\\伊藤作業用\\PSE\\0512 大分類9と11と13　商品一覧(em310)_PSE付き.csv"
dir_1 = r"C:\\Users\\フォーレスト026\\Desktop\\伊藤作業用\\PSE\\大分類9と11と13"
split_by_supplier(target_1, dir_1, 10)

# Split 46,47,48 (Supplier is col index 10, check logic)
target_2 = r"C:\\Users\\フォーレスト026\\Desktop\\伊藤作業用\\PSE\\大分類46と47と48\\大分類46と47と48_PSE付き.csv"
dir_2 = r"C:\\Users\\フォーレスト026\\Desktop\\伊藤作業用\\PSE\\大分類46と47と48"
split_by_supplier(target_2, dir_2, 10)
"""
with open("temp_split.py", "w", encoding="utf-8") as f:
    f.write(split_script)

run_cmd("python temp_split.py")
print("ALL DONE!")
