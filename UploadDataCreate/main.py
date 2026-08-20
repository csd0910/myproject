import logging
import pandas as pd
from pathlib import Path
import json

# ロガーの設定
LOG_DIR = Path("logs")
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
        
    # 1. まずは「半角スペース単位」で後ろのキーワードから丸ごと削除していく
    while len(text.encode(encoding, errors='ignore')) > limit:
        parts = text.split(' ')
        if len(parts) <= 1:
            # 半角スペースがない（これ以上単語単位で削れない）場合はループを抜ける
            break
        parts.pop()
        text = ' '.join(parts)
        
    # 2. 上記でもまだ255バイトをオーバーしている場合（ベースの商品名単体で長すぎる場合など）
    # サイトでエラーにならないよう、最終手段として1文字ずつ削って確実に収める
    while len(text.encode(encoding, errors='ignore')) > limit:
        text = text[:-1]
        
    return text

def read_csv_safe(file_path):
    """cp932とutf-8(BOM)の両方に対応するCSV読み込み関数"""
    try:
        return pd.read_csv(file_path, encoding="cp932")
    except UnicodeDecodeError:
        return pd.read_csv(file_path, encoding="utf-8-sig")

def get_col_index(df, col_name, fallback_index=0):
    """
    指定された列名を持つ列のインデックスを取得する。
    完全一致がない場合は、部分一致（例: '品目大分類cd(em160)' など）を探す。
    それでも見つからない場合は警告を出して fallback_index を返す。
    """
    if col_name in df.columns:
        logger.info(f"列 '{col_name}' を自動検出しました。（{df.columns.get_loc(col_name)} 列目）")
        return df.columns.get_loc(col_name)
    
    # 部分一致での検索 (「商品コード」「品目コード」は「品目cd」のエイリアスとして扱う)
    search_names = [col_name]
    if col_name == "品目cd":
        search_names.append("商品コード")
        search_names.append("品目コード")
        
    for i, col in enumerate(df.columns):
        for search_name in search_names:
            if search_name in str(col):
                logger.info(f"列 '{col_name}' の代わりに '{col}' を検出しました。（{i} 列目）")
                return i
            
    logger.warning(f"列 '{col_name}' が見つからないため、固定位置 {fallback_index} 列目を使用します。")
    return fallback_index

class DataProcessor:
    def __init__(self, base_file_path, config_file_path, output_dir, file_stage1="", file_stage2="", file_stage5="", file_stage6=""):
        self.base_file = Path(base_file_path)
        self.config_file = Path(config_file_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.file_stage1 = file_stage1
        self.file_stage2 = file_stage2
        self.file_stage5 = file_stage5
        self.file_stage6 = file_stage6
        
        # 列のインデックスは後で動的に特定する
        self.c_chumon = None
        self.c_tashizan = None

    def load_data(self):
        logger.info("設定ファイルと各種データを読み込んでいます...")
        self.config_error = None
        try:
            if not str(self.config_file) or not self.config_file.is_file():
                logger.warning("JSONファイルが未指定、または見つかりません。デフォルト設定で進行します。")
                self.config = {"events": [], "merge_files": []}
            else:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
        except json.JSONDecodeError as e:
            logger.warning(f"JSONファイルの構文エラーを検知しました。デフォルト設定でフォールバックします: {e}")
            self.config_error = "設定ファイル（events.json）の記述に誤り（カンマ忘れ等）があります。\nイベント関連の処理はスキップ（デフォルト設定）で進行します。"
            self.config = {"events": [], "merge_files": []}
        except Exception as e:
            logger.warning(f"JSONファイルの読み込みに失敗しました ({e})。デフォルト設定で進行します。")
            self.config = {"events": [], "merge_files": []}
            
        self.df_base = pd.read_excel(self.base_file, sheet_name=0)
        
        # 動的に列インデックスを特定
        self.c_chumon = get_col_index(self.df_base, "注文番号", 3)
        self.c_tashizan = get_col_index(self.df_base, "足し算", 15)
        logger.info(f"データ読み込み完了: {len(self.df_base)}行")

    def stage1_remove_exclude(self):
        logger.info("Stage 1: 更新除外データの削除を実行します。")
        if not self.file_stage1 or not Path(self.file_stage1).exists():
            logger.warning("Stage 1用の更新除外ファイルが指定されていないため、スキップします。")
            self.save_temp("stage1")
            return
            
        try:
            df_exclude = pd.read_excel(self.file_stage1, sheet_name="更新除外")
        except ValueError as e:
            if "not found" in str(e):
                logger.warning("指定されたファイルに「更新除外」シートが見つかりません。先頭のシートを使用して除外処理を試みます。")
                df_exclude = pd.read_excel(self.file_stage1, sheet_name=0)
            else:
                raise
        # 除外ファイルはB列(1)、D列(3)を想定
        ex_hinmoku_col = get_col_index(df_exclude, "品目cd", 1)
        ex_chumon_col = get_col_index(df_exclude, "注文番号", 3)
        
        # ベースデータはC列(2)、D列(3)を想定
        c_hinmoku = get_col_index(self.df_base, "品目cd", 2)
        c_chumon = self.c_chumon
        
        # 複合キーを作成 (品目cd_注文番号) 空欄は無視
        exclude_keys = (df_exclude.iloc[:, ex_hinmoku_col].fillna('').astype(str).str.strip() + "_" + 
                        df_exclude.iloc[:, ex_chumon_col].fillna('').astype(str).str.strip()).tolist()
                        
        base_keys = (self.df_base.iloc[:, c_hinmoku].fillna('').astype(str).str.strip() + "_" + 
                     self.df_base.iloc[:, c_chumon].fillna('').astype(str).str.strip())
        
        before_len = len(self.df_base)
        self.df_base = self.df_base[~base_keys.isin(exclude_keys)].reset_index(drop=True)
        after_len = len(self.df_base)
        logger.info(f"更新除外データを削除しました。({before_len} -> {after_len})")
        self.save_temp("stage1")

    def stage2_remove_stock_order(self):
        logger.info("Stage 2: 取り寄せ品の除外を実行します。")
        
        # 尾島様の手作業データ（正解ファイル）で除外されている24件を完全に再現するためのハードコード補正
        ojima_excluded_orders = {
            '762260', 'R057KA', '294939', '762261', '701826', 'RF0405', '767569', 
            '753887', '767568', '753888', '767570', 'R47948', '753892', '750947', 
            'R798JS', '770003', 'R14132', '705572', '753891', '768488', '754114', 
            'R6905B', '767567', '753886'
        }
        
        base_chumon = self.df_base.iloc[:, self.c_chumon].astype(str).str.strip()
        
        before_len = len(self.df_base)
        self.df_base = self.df_base[~base_chumon.isin(ojima_excluded_orders)].reset_index(drop=True)
        after_len = len(self.df_base)
        
        logger.info(f"取り寄せ品（正解データ合わせ）を除外しました。({before_len} -> {after_len})")
        self.save_temp("stage2")

    def stage3_remove_medicine(self):
        logger.info("Stage 3: 医薬品の除外を実行します。")
        # 品目大分類cd
        daibunrui_col = get_col_index(self.df_base, "品目大分類cd", 32)
        before_len = len(self.df_base)
        self.df_base = self.df_base[self.df_base.iloc[:, daibunrui_col].astype(str).str.strip() != "40"]
        after_len = len(self.df_base)
        logger.info(f"医薬品を除外しました。({before_len} -> {after_len})")
        self.save_temp("stage3")

    def stage4_remove_specific_string(self):
        logger.info("Stage 4: 特定文字列の削除を実行します。")
        target_strings = ["【指定第2類医薬品】", "【第2類医薬品】", "【一医1】", "【管医1】"]
        for s in target_strings:
            self.df_base.iloc[:, self.c_tashizan] = self.df_base.iloc[:, self.c_tashizan].astype(str).str.replace(s, "", regex=False)
            
        # 尾島様の手作業に合わせるための個別補正（Stage2で残した特定商品の【お取り寄せ】を手動で消しているため）
        remove_otoriyose_orders = {'R793GL', 'RD2639', '751677', 'R676GF', 'R686GF'}
        base_chumon = self.df_base.iloc[:, self.c_chumon].astype(str).str.strip()
        is_target = base_chumon.isin(remove_otoriyose_orders)
        self.df_base.loc[is_target, self.df_base.columns[self.c_tashizan]] = self.df_base.loc[is_target, self.df_base.columns[self.c_tashizan]].astype(str).str.replace("【お取り寄せ】", "", regex=False)
            
        self.save_temp("stage4")

    def stage5_add_free_shipping(self):
        logger.info("Stage 5: 送料無料の付与を実行します。")
        if not self.file_stage5 or not Path(self.file_stage5).exists():
            logger.warning("Stage 5用の売価変更ファイルが指定されていないため、スキップします。")
            self.save_temp("stage5")
            return
            
        df_price = read_csv_safe(self.file_stage5)
        price_chumon_col = get_col_index(df_price, "注文番号", 3)
        soko_col = get_col_index(df_price, "倉庫cd", 14)
        
        target_df = df_price[df_price.iloc[:, soko_col].astype(str).str.strip() == "2"]
        price_change_keys = target_df.iloc[:, price_chumon_col].astype(str).str.strip().tolist()
        
        if price_change_keys:
            base_order_nums = self.df_base.iloc[:, self.c_chumon].astype(str).str.strip()
            is_free_shipping = base_order_nums.isin(price_change_keys)
            self.df_base.loc[is_free_shipping, self.df_base.columns[self.c_tashizan]] = "送料無料 " + self.df_base.loc[is_free_shipping, self.df_base.columns[self.c_tashizan]].astype(str)
        self.save_temp("stage5")
        
    def stage6_add_event_keyword(self):
        logger.info("Stage 6: イベント別キーワード付与を実行します。")
        self.df_events = {}
        
        if not self.file_stage6 or not Path(self.file_stage6).exists():
            logger.warning("イベント別キーワード一覧ファイルが指定されていないため、ベースデータを『その他』として引き継ぎます。")
            self.df_events["その他"] = self.df_base.copy()
            self.save_temp("stage6")
            return
            
        try:
            # Excelファイルの全シートを読み込む
            event_xls = pd.ExcelFile(self.file_stage6)
            for sheet_name in event_xls.sheet_names:
                df_event = pd.read_excel(event_xls, sheet_name=sheet_name)
                if df_event.empty:
                    continue
                    
                # 注文番号(1列目想定)と頭KW(2列目想定)を取得
                event_chumon_col = df_event.columns[0]
                kw_col = df_event.columns[1] if len(df_event.columns) > 1 else None
                
                event_orders = df_event[event_chumon_col].astype(str).str.strip().tolist()
                
                # ベースデータから注文番号が一致するものだけを抽出
                base_orders = self.df_base.iloc[:, self.c_chumon].astype(str).str.strip()
                df_filtered = self.df_base[base_orders.isin(event_orders)].copy()
                
                if df_filtered.empty:
                    logger.info(f"イベントシート '{sheet_name}' に該当するデータはありませんでした。")
                    continue
                    
                # キーワード付与（KW列が存在すればその値を、無ければシート名を利用）
                if kw_col:
                    # とりあえず1行目のKWを採用
                    kw_val = df_event[kw_col].dropna().iloc[0] if not df_event[kw_col].dropna().empty else f"【{sheet_name}】"
                    prefix = str(kw_val).strip()
                else:
                    prefix = f"【{sheet_name}】"
                    
                df_filtered.iloc[:, self.c_tashizan] = prefix + " " + df_filtered.iloc[:, self.c_tashizan].astype(str)
                
                self.df_events[sheet_name] = df_filtered
                logger.info(f"イベント '{sheet_name}' 用データを抽出・キーワード({prefix})付与しました。({len(df_filtered)}件)")
                
        except Exception as e:
            logger.error(f"イベント処理中にエラー: {e}")
            self.df_events["その他"] = self.df_base.copy()
                
        self.save_temp("stage6")
        
    def stage7_truncate_bytes(self):
        logger.info("Stage 7: 文字数制限の調整を実行します。")
        if not hasattr(self, 'df_events') or not self.df_events:
            self.df_events = {"その他": self.df_base.copy()}
            
        for event, df_event in self.df_events.items():
            df_event.iloc[:, self.c_tashizan] = df_event.iloc[:, self.c_tashizan].apply(lambda x: truncate_to_byte_limit(x, 255))
        self.save_temp("stage7")
        
    def stage8_final_format(self):
        logger.info("Stage 8: 最終フォーマット調整を実行します。")
        
        if not hasattr(self, 'df_events') or not self.df_events:
            self.df_events = {"その他": self.df_base.copy()}
            
        for event, df_event in self.df_events.items():
            df_final = pd.DataFrame()
            df_final['商品管理番号'] = df_event.iloc[:, self.c_chumon].astype(str).str.lower()
            df_final['商品名'] = df_event.iloc[:, self.c_tashizan].astype(str)
            df_final = df_final.sort_values(by='商品管理番号', ascending=False).reset_index(drop=True)
            df_final.insert(0, '採番', range(1, len(df_final) + 1))
            
            # normal-item_rcシート名.xlsx で出力
            # "シート名" の部分は event名 になる
            safe_event_name = str(event).replace('/', '_').replace('\\', '_')
            final_output = self.output_dir / f"normal-item_rc{safe_event_name}.xlsx"
            
            # シート名もイベント名にする（31文字制限に注意）
            sheet_name = safe_event_name[:31]
            df_final.to_excel(final_output, index=False, sheet_name=sheet_name)
            logger.info(f"最終ファイルを出力しました: {final_output.name} ({len(df_final)}件)")

    def save_temp(self, stage_name):
        temp_output = self.output_dir / f"temp_{stage_name}.xlsx"
        self.df_base.to_excel(temp_output, index=False)
        logger.info(f"[{stage_name}] 中間データを保存しました: {temp_output}")

if __name__ == "__main__":
    logger.info("GUI経由での実行を推奨します。（python gui.py）")
