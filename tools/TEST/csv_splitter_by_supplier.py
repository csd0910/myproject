import pandas as pd
import os

def split_by_supplier(file_path, output_dir):
    """指定されたファイルを読み込み、仕入先名（インデックス10）で分割保存する"""
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return

    print(f"INFO: 仕入先ごとに分割しています: {file_path}")
    
    df = pd.read_csv(file_path, encoding='cp932')
    
    # このファイル形式ではインデックス10が「仕入先名」
    supplier_col = df.columns[10]
    print(f"INFO: 分割キーワード列: {supplier_col}")

    # 仕入先ごとにグループ化
    suppliers = df[supplier_col].unique()
    
    base_name = os.path.basename(file_path).replace(".csv", "")

    for supplier in suppliers:
        if pd.isna(supplier) or str(supplier).strip() == "":
            supplier_name = "仕入先不明"
        else:
            # ファイル名に使えない文字を置換
            supplier_name = str(supplier).replace("/", "／").replace("\\", "＼").replace(":", "：").replace("*", "＊").strip()
        
        # 新しいファイル名: 元のファイル名＿仕入先名.csv
        new_file_name = f"{base_name}_{supplier_name}.csv"
        save_path = os.path.join(output_dir, new_file_name)
        
        # 抽出して保存
        supplier_df = df[df[supplier_col] == supplier]
        supplier_df.to_csv(save_path, index=False, encoding='cp932')
        print(f"  -> 保存完了: {new_file_name} ({len(supplier_df)}件)")

    print("\nすべての分割が完了しました。")

if __name__ == "__main__":
    # 判定が終わった後のファイル（大分類9,11,13用）
    target_file = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\0512 大分類9と11と13　商品一覧(em310)_PSE付き.csv"
    # 保存先サブフォルダ
    sub_dir = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\大分類9と11と13"
    
    if not os.path.exists(target_file):
        print(f"Error: {target_file} not found.")
    else:
        split_by_supplier(target_file, sub_dir)
