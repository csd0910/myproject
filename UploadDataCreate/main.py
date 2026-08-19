import logging
import pandas as pd
from pathlib import Path
import json

# ロガーの設定
LOG_DIR = Path(r"c:\Users\フォーレスト026\MyProject\UploadDataCreate\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "error.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def truncate_to_byte_limit(text, limit=255, encoding='cp932'):
    if not isinstance(text, str):
        return text
    while len(text.encode(encoding, errors='ignore')) > limit:
        parts = text.split(' ')
        if len(parts) <= 1:
            logger.warning(f"区切り文字なしで制限超過: {text[:20]}...")
            break
        parts.pop()
        text = ' '.join(parts)
    return text

def get_col_index(df, col_name, fallback_idx):
    if col_name in df.columns:
        idx = df.columns.get_loc(col_name)
        logger.info(f"列 '{col_name}' を自動検出しました。（{idx} 列目）")
        return idx
    else:
        logger.warning(f"列 '{col_name}' が見つからないため、固定位置 {fallback_idx} 列目を使用します。")
        return fallback_idx

class DataProcessor:
    def __init__(self, base_file_path, config_file_path, output_dir):
        self.base_file = Path(base_file_path)
        self.config_file = Path(config_file_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.df_base = None
        self.df_exclude = None
        self.df_stock_order = None
        self.df_price_change = None
        self.config = {}
        
        # 列インデックス
        self.c_hinmoku = None
        self.c_chumon = None
        self.c_tashizan = None
        self.c_daibunrui = None

    def load_data(self):
        logger.info("設定ファイルと各種データを読み込んでいます...")
        with open(self.config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
            
        self.df_base = pd.read_excel(self.base_file, sheet_name="Sheet1")
        
        merge_files = self.config.get("merge_files", [])
        if len(merge_files) >= 3:
            self.df_exclude = pd.read_excel(merge_files[0], sheet_name="更新除外")
            self.df_stock_order = pd.read_csv(merge_files[1], encoding="cp932")
            self.df_price_change = pd.read_csv(merge_files[2], encoding="cp932")
        else:
            logger.warning("マージファイルの設定が3つ未満です。除外処理がスキップされる可能性があります。")
            
        self.c_hinmoku = get_col_index(self.df_base, '品目cd(em310)', 2)
        self.c_chumon = get_col_index(self.df_base, '注文番号(em310)', 3)
        self.c_tashizan = get_col_index(self.df_base, '足し算', 20)
        self.c_daibunrui = get_col_index(self.df_base, '品目大分類cd(em160)', 32)
        
        # 比較用の一時列を作成
        self.df_base['compare_key_C'] = self.df_base.iloc[:, self.c_hinmoku].astype(str).str.strip()
        self.df_base['compare_key_D'] = self.df_base.iloc[:, self.c_chumon].astype(str).str.strip()
        logger.info(f"データ読み込み完了。初期件数: {len(self.df_base)}件")

    def stage1_remove_exclude(self):
        logger.info("Stage 1: 更新除外データの削除を実行します。")
        if self.df_exclude is not None:
            exclude_keys_B = self.df_exclude.iloc[:, 1].dropna().astype(str).str.strip().unique()
            self.df_base = self.df_base[~self.df_base['compare_key_C'].isin(exclude_keys_B)]
            exclude_keys_D = self.df_exclude.iloc[:, 3].dropna().astype(str).str.strip().unique()
            self.df_base = self.df_base[~self.df_base['compare_key_D'].isin(exclude_keys_D)]
        self.save_temp("stage1")
        
    def stage2_remove_stock_order(self):
        logger.info("Stage 2: 取り寄せ品の除外を実行します。")
        if self.df_stock_order is not None:
            stock_order_keys = self.df_stock_order.iloc[:, 0].dropna().astype(str).str.strip().unique()
            self.df_base = self.df_base[~self.df_base['compare_key_C'].isin(stock_order_keys)]
        self.save_temp("stage2")
        
    def stage3_remove_medicine(self):
        logger.info("Stage 3: 医薬品の除外を実行します。")
        if 'compare_key_C' in self.df_base.columns:
            self.df_base = self.df_base.drop(columns=['compare_key_C', 'compare_key_D'])
            
        if len(self.df_base.columns) > self.c_daibunrui:
            self.df_base = self.df_base[self.df_base.iloc[:, self.c_daibunrui].astype(str).str.strip() != '40']
        self.save_temp("stage3")
        
    def stage4_remove_specific_string(self):
        logger.info("Stage 4: 特定文字列の削除を実行します。")
        self.df_base.iloc[:, self.c_tashizan] = self.df_base.iloc[:, self.c_tashizan].astype(str).replace({'【一医１】': '', '【管医１】': ''}, regex=True)
        self.save_temp("stage4")

    def stage5_add_free_shipping(self):
        logger.info("Stage 5: 送料無料の付与を実行します。")
        if self.df_price_change is not None:
            price_change_keys = self.df_price_change[self.df_price_change.iloc[:, 5] == 2].iloc[:, 3].dropna().astype(str).str.strip().unique()
            base_order_nums = self.df_base.iloc[:, self.c_chumon].astype(str).str.strip()
            is_free_shipping = base_order_nums.isin(price_change_keys)
            self.df_base.loc[is_free_shipping, self.df_base.columns[self.c_tashizan]] = "送料無料 " + self.df_base.loc[is_free_shipping, self.df_base.columns[self.c_tashizan]].astype(str)
        self.save_temp("stage5")
        
    def stage6_add_event_keyword(self):
        logger.info("Stage 6: イベント別キーワード付与を実行します。")
        events = self.config.get("events", [])
        if events:
            # TODO: 今回は代表して最初のイベント設定を全体に付与（本来はシート分割やVLOOKUPが必要）
            event = events[0]
            prefix = event.get("add_prefix", "")
            if prefix:
                self.df_base.iloc[:, self.c_tashizan] = prefix + " " + self.df_base.iloc[:, self.c_tashizan].astype(str)
                logger.info(f"イベントプレフィックス '{prefix}' を付与しました。")
        self.save_temp("stage6")
        
    def stage7_truncate_bytes(self):
        logger.info("Stage 7: 文字数制限の調整を実行します。")
        self.df_base.iloc[:, self.c_tashizan] = self.df_base.iloc[:, self.c_tashizan].apply(lambda x: truncate_to_byte_limit(x, 255))
        self.save_temp("stage7")
        
    def stage8_final_format(self):
        logger.info("Stage 8: 最終フォーマット調整を実行します。")
        df_final = pd.DataFrame()
        df_final['商品管理番号'] = self.df_base.iloc[:, self.c_chumon].astype(str).str.lower()
        df_final['商品名'] = self.df_base.iloc[:, self.c_tashizan].astype(str)
        df_final = df_final.sort_values(by='商品管理番号', ascending=False).reset_index(drop=True)
        df_final.insert(0, '採番', range(1, len(df_final) + 1))
        
        final_output = self.output_dir / "normal_item_result.xlsx"
        df_final.to_excel(final_output, index=False)
        logger.info(f"最終データを保存しました: {final_output}")

    def save_temp(self, stage_name):
        temp_output = self.output_dir / f"temp_{stage_name}.xlsx"
        self.df_base.to_excel(temp_output, index=False)
        logger.info(f"[{stage_name}] 中間データを保存しました: {temp_output}")

if __name__ == "__main__":
    logger.info("GUI経由での実行を推奨します。（python gui.py）")
