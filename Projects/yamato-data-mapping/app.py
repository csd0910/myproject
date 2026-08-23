import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import re
import yaml
import os
import sys

def get_base_dir():
    # exe化されている場合とスクリプト実行の場合でパスを切り替え
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

YAML_PATH = os.path.join(get_base_dir(), "Settings.yaml")

DEFAULT_YAML = {
    "固定値設定": {
        "A列_依頼種別": "1",
        "C列_入力者氏名姓": "",
        "D列_入力者氏名名": "",
        "P列_変更後_郵便番号1": "",
        "Q列_変更後_郵便番号2": "",
        "R列_変更後_都道府県名": "",
        "S列_変更後_市区町村": "",
        "T列_変更後_番地": "",
        "U列_変更後_お届け先姓": "",
        "V列_変更後_お届け先名": "",
        "W列_変更後_電話番号1": "",
        "X列_変更後_電話番号2": "",
        "Y列_変更後_電話番号3": "",
        "Z列_着払い発送了承済み": ""
    }
}

def load_or_create_yaml():
    if not os.path.exists(YAML_PATH):
        try:
            with open(YAML_PATH, 'w', encoding='utf-8') as f:
                yaml.dump(DEFAULT_YAML, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            messagebox.showwarning("警告", f"設定ファイルの作成に失敗しました。\n{e}")
            return DEFAULT_YAML
    try:
        with open(YAML_PATH, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or DEFAULT_YAML
    except Exception as e:
        messagebox.showwarning("警告", f"設定ファイルの読み込みに失敗しました。\n{e}")
        return DEFAULT_YAML

def split_address(address):
    if pd.isna(address):
        return "", "", ""
    match = re.match(r'^(...?[都道府県])(.*?)([0-9０-９].*)$', str(address))
    if match:
        return match.group(1), match.group(2), match.group(3)
    else:
        match_pref = re.match(r'^(...?[都道府県])(.*)$', str(address))
        if match_pref:
            return match_pref.group(1), match_pref.group(2), ""
        return "", str(address), ""

def process_data(template_path, source_path):
    # YAML読み込み
    settings = load_or_create_yaml()
    fixed_vals = settings.get("固定値設定", {})

    df_src = pd.read_excel(source_path)
    df_dst = pd.read_excel(template_path)
    
    df_out = pd.DataFrame(columns=df_dst.columns)
    
    # 基本マッピング (B列, K列)
    df_out['伝票番号 ※半角数字12文字'] = df_src['Qno'].astype(str)
    df_out['変更前：お届け先姓　※全角文字列15文字'] = df_src['Shp Pl Nam'].astype(str)
    
    # 住所分割 (H, I, J列)
    prefs, cities, streets = zip(*df_src['Shp Pl Add1'].apply(split_address))
    df_out['変更前：都道府県名　※全角文字列4文字'] = prefs
    df_out['変更前：市区町村/大字通称/字丁目　※全角文字列42文字'] = cities
    df_out['変更前：番地　※全角文字列40文字'] = streets

    # 郵便番号分割 (F, G列)
    def split_zip(z):
        z_str = str(z).replace(".0", "").zfill(7) if pd.notna(z) and str(z).strip() != "" else ""
        if len(z_str) >= 7:
            return z_str[:3], z_str[3:7]
        return "", ""
    zip1, zip2 = zip(*df_src['Shp Pl Post No'].apply(split_zip))
    df_out['変更前：郵便番号１　※半角数字3文字'] = zip1
    df_out['変更前：郵便番号２　※半角数字4文字'] = zip2

    # 電話番号分割 (M, N, O列)
    def split_tel(t):
        if pd.isna(t): return "", "", ""
        parts = str(t).split('-')
        if len(parts) == 3:
            return parts[0], parts[1], parts[2]
        return str(t), "", ""
    tel1, tel2, tel3 = zip(*df_src['Shp Pl Tel No'].apply(split_tel))
    df_out['変更前：電話番号１　※半角数字6文字'] = tel1
    df_out['変更前：電話番号２　※半角数字4文字'] = tel2
    df_out['変更前：電話番号３　※半角数字4文字'] = tel3

    # YAML設定からの固定値反映
    col_mapping = {
        "A列_依頼種別": df_out.columns[0],
        "C列_入力者氏名姓": df_out.columns[2],
        "D列_入力者氏名名": df_out.columns[3],
        "P列_変更後_郵便番号1": df_out.columns[15],
        "Q列_変更後_郵便番号2": df_out.columns[16],
        "R列_変更後_都道府県名": df_out.columns[17],
        "S列_変更後_市区町村": df_out.columns[18],
        "T列_変更後_番地": df_out.columns[19],
        "U列_変更後_お届け先姓": df_out.columns[20],
        "V列_変更後_お届け先名": df_out.columns[21],
        "W列_変更後_電話番号1": df_out.columns[22],
        "X列_変更後_電話番号2": df_out.columns[23],
        "Y列_変更後_電話番号3": df_out.columns[24],
        "Z列_着払い発送了承済み": df_out.columns[25]
    }

    for yaml_key, col_name in col_mapping.items():
        val = fixed_vals.get(yaml_key, "")
        if val is not None and str(val).strip() != "":
            df_out[col_name] = str(val)

    df_out = df_out.fillna("")
    
    # 出力
    out_dir = os.path.dirname(source_path)
    csv_path = os.path.join(out_dir, "出力_結果.csv")
    xlsx_path = os.path.join(out_dir, "出力_結果_Excel確認用.xlsx")
    
    df_out.to_csv(csv_path, index=False, encoding='utf-8-sig')
    df_out.to_excel(xlsx_path, index=False)
    
    return csv_path, xlsx_path

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ヤマト マッピングツール")
        self.geometry("600x300")
        
        # 起動時にYAMLの存在確認・生成
        load_or_create_yaml()
        
        self.template_path = tk.StringVar()
        self.source_path = tk.StringVar()
        
        tk.Label(self, text="① 出力_配達中止・転送依頼.xlsx を選択してください").pack(pady=(15, 5))
        frame1 = tk.Frame(self)
        frame1.pack()
        tk.Entry(frame1, textvariable=self.template_path, width=60).pack(side=tk.LEFT, padx=5)
        tk.Button(frame1, text="参照", command=self.select_template).pack(side=tk.LEFT)
        
        tk.Label(self, text="② 出荷数_物流sv情報【問番】.xlsx を選択してください").pack(pady=(15, 5))
        frame2 = tk.Frame(self)
        frame2.pack()
        tk.Entry(frame2, textvariable=self.source_path, width=60).pack(side=tk.LEFT, padx=5)
        tk.Button(frame2, text="参照", command=self.select_source).pack(side=tk.LEFT)
        
        tk.Button(self, text="処理開始", bg="lightblue", font=("", 12, "bold"), command=self.run_process).pack(pady=30)
        
    def select_template(self):
        path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if path:
            self.template_path.set(path)
            
    def select_source(self):
        path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if path:
            self.source_path.set(path)
            
    def run_process(self):
        tp = self.template_path.get()
        sp = self.source_path.get()
        
        if not tp or not sp:
            messagebox.showerror("エラー", "両方のファイルを選択してください。")
            return
            
        try:
            csv_out, xlsx_out = process_data(tp, sp)
            messagebox.showinfo("完了", f"処理が完了しました。\n\nCSV出力先:\n{csv_out}\n\nExcel出力先:\n{xlsx_out}")
        except Exception as e:
            messagebox.showerror("エラー", f"処理中にエラーが発生しました。\n{e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
