import pandas as pd
import re

def clean_phone(phone_str):
    if pd.isna(phone_str):
        return ""
    phone = str(phone_str)
    phone = re.sub(r'[（\(]共有[）\)]', '', phone)
    phone = re.sub(r'[^\d-]', '', phone)
    return phone.strip()

source_file = r"C:\Users\フォーレスト026\Downloads\User_Download_18082026_094807_File.xlsx"
df = pd.read_excel(source_file)
count = 0
for i, row in df.iterrows():
    p = clean_phone(row.iloc[15])
    if p:
        print(f"Raw: {row.iloc[15]} -> Cleaned: {p}")
        count += 1
        if count > 5: break
