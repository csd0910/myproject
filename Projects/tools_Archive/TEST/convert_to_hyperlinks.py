import pandas as pd
import glob
import os

def convert_urls_to_hyperlinks(dirs):
    for target_dir in dirs:
        if not os.path.exists(target_dir):
            print(f"Skip: {target_dir} not found")
            continue
            
        print(f"Processing folder: {target_dir}")
        csv_files = glob.glob(os.path.join(target_dir, "*.csv"))
        
        for file_path in csv_files:
            # 判定根拠マスタ等は除外（商品データのみ対象）
            if "マスタ" in file_path or "説明書" in file_path:
                continue
                
            try:
                # データを読み込み
                df = pd.read_csv(file_path, encoding='cp932')
                
                # 「自社商品URL」という列を探す
                target_col = "自社商品URL"
                if target_col in df.columns:
                    # 空欄でないURLをハイパーリンク形式に変換
                    # 形式: =HYPERLINK("URL", "URL")
                    df[target_col] = df[target_col].apply(
                        lambda x: f'=HYPERLINK("{x}", "{x}")' if pd.notna(x) and str(x).startswith("http") else x
                    )
                    
                    # 上書き保存
                    df.to_csv(file_path, index=False, encoding='cp932')
                    print(f"  -> Hyperlinked: {os.path.basename(file_path)}")
                else:
                    print(f"  -> Skip (No URL col): {os.path.basename(file_path)}")
            except Exception as e:
                print(f"  -> Error processing {os.path.basename(file_path)}: {e}")

if __name__ == "__main__":
    target_dirs = [
        r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\大分類46と47と48",
        r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\大分類9と11と13"
    ]
    convert_urls_to_hyperlinks(target_dirs)
    print("\nすべてのハイパーリンク変換が完了しました。")
