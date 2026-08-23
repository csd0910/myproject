import pandas as pd
import os

dir_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\20260526"
f1 = os.path.join(dir_path, "0512 大分類46と47と48　商品一覧(em310)_PSE付き.csv")
f2 = os.path.join(dir_path, "0512 大分類9と11と13　商品一覧(em310)_PSE付き.csv")
out_file = os.path.join(dir_path, "PSE対象抽出_合算リスト.csv")

print("ファイルを読み込み中...")

# f1の処理
df1 = pd.read_csv(f1, encoding='cp932')
df1_target = df1[df1['PSE判定'] == 'PSE対象'].copy()

# 余分な URL_TEMP 列があれば削除（バグ対応）
cols_to_drop = [c for c in df1_target.columns if 'URL_TEMP' in c]
if cols_to_drop:
    df1_target = df1_target.drop(columns=cols_to_drop)
if 'Unnamed: 0' in df1_target.columns:
    df1_target = df1_target.drop(columns=['Unnamed: 0'])

# f2の処理
df2 = pd.read_csv(f2, encoding='cp932')
df2_target = df2[df2['PSE判定'] == 'PSE対象'].copy()

if 'Unnamed: 0' in df2_target.columns:
    df2_target = df2_target.drop(columns=['Unnamed: 0'])

print("結合中...")
# カラム名が異なる部分（f2だけにある列など）は自動で NaN (空欄) として結合されます
merged_df = pd.concat([df1_target, df2_target], ignore_index=True)

print("保存中...")
merged_df.to_csv(out_file, index=False, encoding='cp932')
print(f"完了しました！ 対象件数: {len(merged_df):,} 件 -> {out_file}")
