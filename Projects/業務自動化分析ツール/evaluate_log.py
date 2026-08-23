import os
from google import genai

# APIキー設定
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)
GEMINI_MODEL = "gemini-2.5-flash"

log_file = r"C:\Users\フォーレスト026\MyProject\業務自動化分析ツール\activity_logs\system_log_20260810.csv"
output_file = r"C:\Users\フォーレスト026\MyProject\業務自動化分析ツール\activity_logs\system_log_ai_evaluated.csv"

def main():
    if not os.path.exists(log_file):
        print(f"エラー: {log_file} が見つかりません。")
        return

    print("ログを読み込んでいます...")
    with open(log_file, "r", encoding="utf-8-sig") as f:
        log_content = f.read()

    prompt = f"""
以下のシステムログ（CSV形式）は、ユーザーがPC（主にExcel）で操作した生の記録です。
このログの全行をそのまま出力しつつ、各行の右端（F列）に「AIの要約（人間が具体的に何をしているのかの解説）」を追加したCSVを出力してください。

【要件】
1. F列のヘッダーは「AI解析要約」としてください。
2. セル番地や数式（VLOOKUP等）、コピペなどの生データを読み解き、「VLOOKUP関数を組んで商品マスタからデータを引いている」「外部からテキストをコピペしている」など、人間らしい自然な言葉でF列に要約を書いてください。
3. 出力は必ずカンマ区切りのCSV形式のプレーンテキストのみとしてください（```csv などのMarkdown記号は絶対に含めないでください）。

【対象ログ】
{log_content}
"""

    print("AIに分析を依頼しています（数秒かかります）...")
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        
        # 不要なMarkdown装飾を削除
        csv_text = response.text.replace("```csv", "").replace("```", "").strip()

        with open(output_file, "w", encoding="utf-8-sig") as f:
            f.write(csv_text)
            
        print(f"【成功】AIによる評価結果を付与したCSVを作成しました！")
        print(f"出力先: {output_file}")
        
    except Exception as e:
        print(f"AI解析エラー: {e}")

if __name__ == "__main__":
    main()
