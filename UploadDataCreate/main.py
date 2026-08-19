import logging
import pandas as pd
from pathlib import Path

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# データディレクトリの設定
BASE_DATA_DIR = Path(r"C:\Users\フォーレスト026\Desktop\元データ")
OUTPUT_DIR = Path(r"c:\Users\フォーレスト026\MyProject\UploadDataCreate\output")

def setup_directories():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def truncate_to_byte_limit(text, limit=255, encoding='cp932'):
    """
    指定されたバイト数に収まるように、末尾から半角スペース区切りでキーワードを削除する
    """
    if not isinstance(text, str):
        return text
        
    while len(text.encode(encoding, errors='ignore')) > limit:
        parts = text.split(' ')
        if len(parts) <= 1:
            # スペース区切りがないのにオーバーしている場合はそのまま返すか、強制カットするか
            # ここでは安全のため強制スライスはせずログを出すだけに留める
            logger.warning(f"区切り文字なしで制限超過: {text[:20]}...")
            break
        # 一番最後のキーワード（要素）を削除
        parts.pop()
        text = ' '.join(parts)
    return text

def process_csv_data():
    """データの読み込み・前処理・除外処理メインロジック"""
    logger.info("データ処理を開始します。")

    # --- 1. ファイル読み込み ---
    base_file = BASE_DATA_DIR / "result_260812_135942.xlsx"
    exclude_keyword_file = BASE_DATA_DIR / "【2】社外キーワード追加対応.xlsx"
    stock_order_file = BASE_DATA_DIR / "111取り寄せ＋有効在庫有り.csv"
    price_change_file = BASE_DATA_DIR / "111倉庫_売価変更用.csv"
    
    logger.info("ベースデータを読み込んでいます...")
    df_base = pd.read_excel(base_file, sheet_name="Sheet1")
    
    logger.info("マスタデータを読み込んでいます...")
    df_exclude = pd.read_excel(exclude_keyword_file, sheet_name="更新除外")
    df_stock_order = pd.read_csv(stock_order_file, encoding="cp932")
    df_price_change = pd.read_csv(price_change_file, encoding="cp932")

    # --- 2. 前処理・除外処理 ---
    initial_count = len(df_base)
    logger.info(f"初期データ件数: {initial_count}件")

    df_base['compare_key_C'] = df_base.iloc[:, 2].astype(str).str.strip() # C列: 品目cd
    df_base['compare_key_D'] = df_base.iloc[:, 3].astype(str).str.strip() # D列: 注文番号

    # (1) 更新除外データの削除
    exclude_keys_B = df_exclude.iloc[:, 1].dropna().astype(str).str.strip().unique()
    df_base = df_base[~df_base['compare_key_C'].isin(exclude_keys_B)]
    exclude_keys_D = df_exclude.iloc[:, 3].dropna().astype(str).str.strip().unique()
    df_base = df_base[~df_base['compare_key_D'].isin(exclude_keys_D)]
    logger.info(f"更新除外後件数: {len(df_base)}件")

    # (2) 取り寄せ品の除外
    stock_order_keys = df_stock_order.iloc[:, 0].dropna().astype(str).str.strip().unique()
    df_base = df_base[~df_base['compare_key_C'].isin(stock_order_keys)]
    logger.info(f"取り寄せ品除外後件数: {len(df_base)}件")
    
    # (3), (4), (5) の欠損工程（プレースホルダー）
    # TODO: 現場に確認後、ここに「4の情報の除外」ロジックを追加する
    logger.info("欠損工程（3〜5）はスキップして進めます。")

    # 比較用の一時列を削除
    df_base = df_base.drop(columns=['compare_key_C', 'compare_key_D'])

    # (6) 医薬品の除外（AG列=インデックス32が40のもの）
    if len(df_base.columns) > 32:
        df_base = df_base[df_base.iloc[:, 32].astype(str).str.strip() != '40']
    logger.info(f"医薬品除外後件数: {len(df_base)}件")

    # (7) 特定文字列の削除（U列：インデックス20「足し算」に対して実施）
    df_base.iloc[:, 20] = df_base.iloc[:, 20].astype(str).replace({'【一医１】': '', '【管医１】': ''}, regex=True)
    logger.info("特定文字列の削除完了")

    # --- 3. 文字列操作・条件付与 ---
    logger.info("文字列操作・キーワード付与を開始します。")

    # (8) 「送料無料」の付与
    # df_price_changeの「注番」(インデックス3)と「倉庫cd」(インデックス5)を取得
    price_change_keys = df_price_change[df_price_change.iloc[:, 5] == 2].iloc[:, 3].dropna().astype(str).str.strip().unique()
    
    # ベースのD列（インデックス3）と照合し、一致する行のU列（インデックス20）の先頭に「送料無料 」を付与
    base_order_nums = df_base.iloc[:, 3].astype(str).str.strip()
    is_free_shipping = base_order_nums.isin(price_change_keys)
    df_base.loc[is_free_shipping, df_base.columns[20]] = "送料無料 " + df_base.loc[is_free_shipping, df_base.columns[20]].astype(str)
    logger.info(f"送料無料を付与した件数: {is_free_shipping.sum()}件")

    # (9) イベント別キーワード付与（プレースホルダー）
    # ※ここは「今後の改良」として、別CSVが用意された時に動的に処理するための枠です
    logger.info("イベントキーワード付与処理... (現在はマスターファイル未定義のためスキップ)")

    # (10) 文字数制限の調整 (楽天: 255バイト)
    logger.info("文字数制限（255バイト）の調整を実行します...")
    df_base.iloc[:, 20] = df_base.iloc[:, 20].apply(lambda x: truncate_to_byte_limit(x, 255))

    # --- 4. 最終フォーマット調整 (normal item) ---
    logger.info("最終フォーマット (normal item) の生成を開始します。")
    df_final = pd.DataFrame()
    
    # 商品管理番号（注文番号を小文字化）
    df_final['商品管理番号'] = df_base.iloc[:, 3].astype(str).str.lower()
    
    # 商品名（調整後のU列）
    df_final['商品名'] = df_base.iloc[:, 20].astype(str)
    
    # 降順に並び替え
    df_final = df_final.sort_values(by='商品管理番号', ascending=False).reset_index(drop=True)
    
    # 採番 (1, 2, 3...)
    df_final.insert(0, '採番', range(1, len(df_final) + 1))

    # 出力
    final_output = OUTPUT_DIR / "normal_item_result.xlsx"
    df_final.to_excel(final_output, index=False)
    logger.info(f"処理完了！最終データを保存しました: {final_output}")

def main():
    setup_directories()
    try:
        process_csv_data()
    except Exception as e:
        logger.error(f"予期せぬエラーが発生しました: {e}", exc_info=True)

if __name__ == "__main__":
    main()
