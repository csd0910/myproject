import pandas as pd
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

# プログラムの出力ディレクトリ
prog_dir = r'C:\Users\フォーレスト026\MyProject\UploadDataCreate\output'
# 尾島様の手作業ディレクトリ
manu_dir = r'C:\Users\フォーレスト026\MyProject\UploadDataCreate\【テスト用】商品名作成 尾島手作業'

# 比較ペアの定義
# 先ほどの確認でStage1出力は【手順2】ファイルと一致していたため、その法則（処理完了後の次のファイル）でマッピング
pairs = [
    {
        "name": "Stage 1 (除外データ削除)",
        "prog": "diff_stage1.xlsx",
        "manu": "【手順2】result_260819_154419.xlsx"
    },
    {
        "name": "Stage 2 (手順2,3,4,5合算: キーワード除外等)",
        "prog": "diff_stage2.xlsx",
        "manu": "【手順6】result_260819_154419.xlsx"  # 手順5が終わった時点のファイルと推測
    },
    # Stage 3, 4 は内部処理のためパス
    {
        "name": "Stage 5 (手順8: 送料無料付与)",
        "prog": "diff_stage5.xlsx",
        "manu": "【手順9】シート分け＆キーワード付与まで.xlsx" # 手順8が終わった後のファイルと推測
    },
    {
        "name": "Stage 6 (手順9: イベント別KW付与)",
        "prog": "diff_stage6.xlsx",
        "manu": "【手順10-1】文字数調整直後.xlsx" # 手順9が終わった後のファイルと推測
    },
    {
        "name": "Stage 7 (手順10: バイト数制限調整)",
        "prog": "diff_stage7.xlsx",
        "manu": "【手順10-2】CSVツールにかける直前.xlsx" # 最終手前と推測
    }
]

def check_pair(prog_file, manu_file, stage_name):
    print(f"\n=========================================")
    print(f"■ {stage_name} のクロスチェック")
    print(f"=========================================")
    
    if not os.path.exists(prog_file):
        print(f"スキップ: プログラム出力 {os.path.basename(prog_file)} が見つかりません。")
        return
    if not os.path.exists(manu_file):
        print(f"スキップ: 手作業ファイル {os.path.basename(manu_file)} が見つかりません。")
        return
        
    try:
        df1 = pd.read_excel(prog_file)
        df2 = pd.read_excel(manu_file)
        
        c_col = df1.columns[2]
        
        # 文字列としてソート
        df1[c_col] = df1[c_col].astype(str)
        df2[c_col] = df2[c_col].astype(str)
        df1 = df1.sort_values(by=c_col).reset_index(drop=True)
        df2 = df2.sort_values(by=c_col).reset_index(drop=True)
        
        # 件数の比較
        if len(df1) != len(df2):
            print(f"⚠ 行数が一致しません！ (プログラム: {len(df1)}行, 手作業: {len(df2)}行)")
            # 続行するが警告
            
        common_cols = [c for c in df1.columns if c in df2.columns]
        diff_records = []
        
        # 少ない方の行数で比較
        check_len = min(len(df1), len(df2))
        
        for col in common_cols:
            for i in range(check_len):
                val1 = str(df1.loc[i, col]).strip() if pd.notna(df1.loc[i, col]) else ''
                val2 = str(df2.loc[i, col]).strip() if pd.notna(df2.loc[i, col]) else ''
                
                if val1.endswith('.0'): val1 = val1[:-2]
                if val2.endswith('.0'): val2 = val2[:-2]
                
                if val1 != val2:
                    item_cd = df1.loc[i, c_col]
                    diff_records.append(f"品目cd: {item_cd}, 列: {col} => プログラム: [{val1}], 手作業: [{val2}]")
        
        if not diff_records and len(df1) == len(df2):
            print("✨ 結果: 完全に一致しました！(共通列の文字データ)")
        elif not diff_records:
            print("⚠ 共通している行・列の文字データは一致していますが、行数が異なります。")
        else:
            print(f"❌ 結果: 差異が {len(diff_records)} 件見つかりました。")
            for r in diff_records[:5]:
                print(f"  {r}")
            if len(diff_records) > 5:
                print(f"  ... 他 {len(diff_records) - 5} 件")
                
    except Exception as e:
        print(f"エラー発生: {e}")

for p in pairs:
    prog_path = os.path.join(prog_dir, p["prog"])
    manu_path = os.path.join(manu_dir, p["manu"])
    check_pair(prog_path, manu_path, p["name"])
