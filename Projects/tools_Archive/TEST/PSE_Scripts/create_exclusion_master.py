import pandas as pd

def create_exclusion_master():
    # ユーザー提供のテキストデータをパースしてCSV化
    data = [
        ["E062", "直流機器本体", "キーボード", "name", ""],
        ["E063", "直流機器本体", "ヘッドセット", "name", ""],
        ["E064", "直流機器本体", "ヘッドホン", "name", ""],
        ["E065", "直流機器本体", "Webカメラ", "name", ""],
        ["E067", "直流機器本体", "PC用", "category", ""],
        ["E068", "直流機器本体", "パソコン本体", "name", ""],
        ["E080", "業務用・産業用", "自動車用", "desc", "自動車用途の機器・バッテリーはPSE対象外"],
        ["E081", "業務用・産業用", "車載用", "desc", ""],
        ["E083", "業務用・産業用", "医療用", "desc", ""],
        ["E084", "業務用・産業用", "産業用", "desc", ""],
        ["E100", "リチウムイオン蓄電池対象外", "自動車用リチウムイオン", "desc", ""],
        ["E120", "ACアダプタ二次側機器", "USB給電専用", "desc", "USB電源のみで動作する直流機器本体"],
        ["E121", "ACアダプタ二次側機器", "DC5V専用", "desc", ""],
        ["E122", "ACアダプタ二次側機器", "DC12V専用", "desc", ""],
        ["E140", "その他明らかに対象外", "ぬいぐるみ", "name", "電気部品なし"],
        ["E143", "その他明らかに対象外", "文庫本", "name", ""],
        ["E144", "その他明らかに対象外", "雑誌", "name", ""],
    ]
    
    df = pd.DataFrame(data, columns=["exclude_id", "exclude_reason", "keyword", "keyword_type", "notes"])
    output_path = r"C:\Users\フォーレスト026\Desktop\伊藤作業用\PSE\除外マスタ.csv"
    df.to_csv(output_path, index=False, encoding='cp932')
    print(f"Exclusion Master created at: {output_path}")

if __name__ == "__main__":
    create_exclusion_master()
