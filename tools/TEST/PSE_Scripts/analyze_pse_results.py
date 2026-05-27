import pandas as pd
import os

def analyze_pse():
    input_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\0512 大分類9と11と13　商品一覧(em310)_PSE付き.csv"
    report_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\pse_analysis_report.md"
    
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found")
        return

    # 列名で指定（日本語ヘッダーが文字化けしている可能性を考慮し、全読み込み後にリネーム）
    print("INFO: データを読み込んでいます...", flush=True)
    df_full = pd.read_csv(input_path, encoding='cp932')
    
    # 必要な列を特定（名前で探す）
    # 大分類、中分類、品目名などは元のマスタに依存
    # PSE判定などの追加列は最後の方にある
    cols = df_full.columns.tolist()
    target_cols = {
        "大分類": cols[1],
        "中分類": cols[2],
        "品目名": cols[4],
        "電源AN": cols[39],
        "除外AO": cols[40],
        "判定AQ": "PSE判定",
        "要確認AV": "PSE要人手確認",
        "根拠AW": "PSE判定根拠"
    }
    
    df = df_full[[target_cols[k] for k in target_cols]].copy()
    df.columns = ["大分類", "中分類", "品目名", "電源AN", "除外AO", "判定AQ", "要確認AV", "根拠AW"]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# PSE判定精度 分析レポート\n\n")
        f.write(f"解析日時: {pd.Timestamp.now()}\n")
        f.write(f"解析対象件数: {len(df):,} 件\n\n")

        # ---------------------------------------------------------
        # 1. 判定結果の全体サマリー
        # ---------------------------------------------------------
        f.write("## 1. 判定結果サマリー\n")
        summary = df["判定AQ"].value_counts()
        f.write("| 判定結果 | 件数 | 割合 |\n| :--- | :--- | :--- |\n")
        for k, v in summary.items():
            f.write(f"| {k} | {v:,} | {v/len(df)*100:.1f}% |\n")
        
        check_count = df["要確認AV"].sum()
        f.write(f"\n**人手による確認が必要な件数: {int(check_count):,} 件**\n\n")

        # ---------------------------------------------------------
        # 2. マスタ漏れ（AC100Vなのに対象外）の分析
        # ---------------------------------------------------------
        f.write("## 2. マスタ漏れ候補（AC100V駆動なのに対象外）\n")
        f.write("AC100V駆動かつ、医療・産業用などの除外キーワードが含まれないのに対象外となった商品です。\nこれらをマスタに追加することで精度が向上します。\n\n")
        
        ao_exclude = "医療|産業|工業|車載|自動車"
        miss_df = df[
            (df["判定AQ"] == "PSE対象外") & 
            (df["電源AN"].str.contains("AC100V|交流100V", na=False, case=False)) &
            (~df["除外AO"].str.contains(ao_exclude, na=False)) &
            (~df["品目名"].str.contains(ao_exclude, na=False))
        ]

        if not miss_df.empty:
            f.write("### 分類別・未ヒット件数（上位20件）\n")
            top_miss = miss_df.groupby(["大分類", "中分類"]).size().sort_values(ascending=False).head(20)
            f.write("| 大分類 | 中分類 | 未ヒット件数 |\n| :--- | :--- | :--- |\n")
            for (big, mid), count in top_miss.items():
                f.write(f"| {big} | {mid} | {count:,} |\n")
            
            f.write("\n### 具体的な商品例（一部）\n")
            f.write("| 品目名 | 電源仕様(AN) | 判定根拠 |\n| :--- | :--- | :--- |\n")
            for _, row in miss_df.head(30).iterrows():
                # 長すぎるテキストをカット
                p_name = str(row["品目名"])[:40] + "..." if len(str(row["品目名"])) > 40 else str(row["品目名"])
                f.write(f"| {p_name} | {str(row['電源AN'])[:20]} | {row['根拠AW']} |\n")
        else:
            f.write("該当なし\n")

        # ---------------------------------------------------------
        # 3. 除外理由の分析
        # ---------------------------------------------------------
        f.write("\n## 3. 除外判定の主な理由\n")
        reason_summary = df[df["判定AQ"] == "PSE対象外"]["根拠AW"].value_counts().head(20)
        f.write("| 除外・判定根拠 | 件数 |\n| :--- | :--- |\n")
        for k, v in reason_summary.items():
            f.write(f"| {k} | {v:,} |\n")

    print(f"Report generated: {report_path}")

if __name__ == "__main__":
    analyze_pse()
