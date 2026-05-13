import pandas as pd
import os

def convert_txt_to_csv():
    txt_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\除外マスタ.txt"
    csv_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\除外マスタ.csv"
    
    if not os.path.exists(txt_path):
        print("Error: txt file not found")
        return

    # テキストファイルを読み込んで、カンマ区切りでパースする
    rows = []
    # 日本語環境なので cp932 で読み込み
    with open(txt_path, 'r', encoding='cp932', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            # カンマで分割（最大5列分）
            parts = line.split(',')
            if len(parts) >= 3:
                # 不足している列を空文字で埋める
                while len(parts) < 5:
                    parts.append("")
                rows.append(parts[:5])

    df = pd.DataFrame(rows, columns=["exclude_id", "exclude_reason", "keyword", "keyword_type", "notes"])
    df.to_csv(csv_path, index=False, encoding='cp932')
    print(f"Successfully converted {len(df)} rules to {csv_path}")

if __name__ == "__main__":
    convert_txt_to_csv()
