import pandas as pd
import re

def clean_phone(phone_str):
    if pd.isna(phone_str):
        return ""
    # "（共有）"などの全角括弧や不要な文字を削除
    # 基本的に数字とハイフンだけを残すか、"共有"という文字を消す
    # ここでは "共有" や括弧を取り除くアプローチにします
    phone = str(phone_str)
    phone = re.sub(r'[（\(]共有[）\)]', '', phone)  # （共有）を消す
    phone = re.sub(r'[^\d-]', '', phone)  # 数字とハイフン以外を全て消す
    return phone.strip()

def clean_department(dept_str):
    if pd.isna(dept_str):
        return ""
    dept = str(dept_str)
    # "/04_管理統括部/01_管理部" -> 最後の "_" 以降を抽出
    if "_" in dept:
        return dept.split("_")[-1]
    return dept

def generate_vcf():
    source_file = r"C:\Users\フォーレスト026\Downloads\User_Download_18082026_094807_File.xlsx"
    output_file = r"C:\Users\フォーレスト026\Desktop\contacts.vcf"
    
    print(f"Loading data from {source_file}...")
    df = pd.read_excel(source_file)
    
    vcf_content = ""
    
    for index, row in df.iterrows():
        # インデックスに基づく取得
        # A列: 0 (名)
        # B列: 1 (姓)
        # C列: 2 (メール)
        # F列: 5 (部門)
        # P列: 15 (電話番号)
        try:
            first_name = str(row.iloc[0]) if not pd.isna(row.iloc[0]) else ""
            last_name = str(row.iloc[1]) if not pd.isna(row.iloc[1]) else ""
            email = str(row.iloc[2]) if not pd.isna(row.iloc[2]) else ""
            dept_raw = str(row.iloc[5]) if not pd.isna(row.iloc[5]) else ""
            phone_raw = str(row.iloc[15]) if not pd.isna(row.iloc[15]) else ""
            
            # データのクレンジング
            phone = clean_phone(phone_raw)
            dept = clean_department(dept_raw)
            
            # 名前も電話番号もない場合はスキップ
            if not first_name and not last_name and not phone:
                continue
                
            # vCardエントリ作成
            vcard = f"BEGIN:VCARD\nVERSION:3.0\n"
            vcard += f"N:{last_name};{first_name};;;\n"
            vcard += f"FN:{last_name} {first_name}\n"
            if dept:
                vcard += f"ORG:{dept}\n"
            if phone:
                vcard += f"TEL;TYPE=CELL:{phone}\n"
            if email:
                vcard += f"EMAIL;TYPE=INTERNET;TYPE=WORK:{email}\n"
            vcard += "END:VCARD\n"
            
            vcf_content += vcard
            
            # 確認用（最初の1件だけ表示）
            if index == 0:
                print("【先頭1件の出力イメージ】")
                print(vcard)
                
        except IndexError:
            print("列の数が足りません。ファイルのフォーマットを確認してください。")
            break
            
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(vcf_content)
        
    print(f"\n処理完了: {output_file} に保存しました。")

if __name__ == "__main__":
    generate_vcf()
