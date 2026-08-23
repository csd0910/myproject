import re

def convert_iphone_to_android_vcf():
    input_file = r"C:\Users\フォーレスト026\Downloads\すべての連絡先 (2).vcf"
    output_file = r"C:\Users\フォーレスト026\Desktop\Android用_すべての連絡先(2).vcf"

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"ファイルの読み込みに失敗しました: {e}")
        return

    output_lines = []
    
    for line in lines:
        # iPhoneのVCFにはBase64の画像データなどが含まれており、
        # 行の先頭の空白（スペース）が重要な意味を持つため、strip()は使わない。
        
        # ただし、TELから始まる行だけは電話番号の不要なスペースを消す
        if line.startswith("TEL"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                prefix = parts[0]
                number = parts[1].replace(" ", "").replace("-", "") # 電話番号内の空白とハイフンを削除
                # 元の行の末尾の改行コードを保持
                newline = "\n" if line.endswith("\n") else ""
                number = number.strip() # 番号自体の前後の空白改行を消す
                line = f"{prefix}:{number}{newline}"

        output_lines.append(line)

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(output_lines)
        print(f"変換成功: {output_file} に保存しました。")
    except Exception as e:
        print(f"ファイルの保存に失敗しました: {e}")

if __name__ == "__main__":
    convert_iphone_to_android_vcf()
