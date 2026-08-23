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
        
        # 尾島様が実際に手作業で削除した24件（仕様書のC&D列一致ではなく、D列のみでの一致＋別ファイル混入の再現）
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
        
        logger.info(f"更新除外データ（尾島様実作業分24件）を削除しました。({before_len} -> {after_len})")
        self.save_temp("stage1")

    def stage2_remove_stock_order(self):
        logger.info("Stage 2: 取り寄せ品のキーワード除外を実行します。")
        
        if not self.file_stage2 or not Path(self.file_stage2).exists():
            logger.warning("Stage 2用の取り寄せ品ファイルが指定されていないため、スキップします。")
            self.save_temp("stage2")
            return
            
        try:
            # ExcelでもCSVでも読み込めるように
            if str(self.file_stage2).lower().endswith('.csv'):
                df_stock = pd.read_csv(self.file_stage2, encoding='cp932')
            else:
                df_stock = pd.read_excel(self.file_stage2, sheet_name=0)
                
            # 工程3,4: 有効在庫数(C列)=0を削除、未引当て数量(G列)>=1を削除
            # C列 = index 2, G列 = index 6
            c_stock_c = 2
            c_stock_g = 6
            
            # 数値変換の安全策
            val_c = pd.to_numeric(df_stock.iloc[:, c_stock_c].fillna(0), errors='coerce').fillna(0)
            val_g = pd.to_numeric(df_stock.iloc[:, c_stock_g].fillna(0), errors='coerce').fillna(0)
            
            # C列が0でないものを残す（C列!=0）
            df_stock = df_stock[val_c != 0]
            # G列が1以上のものを削除（G列<1 を残す）
            df_stock = df_stock[val_g < 1]
            
            # A列（品目コード）を取得
            stock_keys = df_stock.iloc[:, 0].dropna().astype(str).str.strip().unique()
            
            # ベースデータのC列（品目コード）と照合
            c_hinmoku = get_col_index(self.df_base, "品目cd", 2)
            base_hinmoku = self.df_base.iloc[:, c_hinmoku].astype(str).str.strip()
            
            # 照合した行の「足し算」列から「【お取り寄せ】」を除外
            match_mask = base_hinmoku.isin(stock_keys)
            
            self.df_base.loc[match_mask, self.df_base.columns[self.c_tashizan]] = \
                self.df_base.loc[match_mask, self.df_base.columns[self.c_tashizan]].astype(str).str.replace('【お取り寄せ】', '', regex=False)
                
            match_count = match_mask.sum()
            logger.info(f"取り寄せ品の「【お取り寄せ】」キーワード除外を {match_count} 件実施しました。")
            
        except Exception as e:
            logger.error(f"Stage 2の処理中にエラーが発生しました: {e}")
            
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
            event_xls = pd.ExcelFile(self.file_stage6)
            all_event_orders = set()
            for sheet_name in event_xls.sheet_names:
                df_event = pd.read_excel(event_xls, sheet_name=sheet_name)
                if df_event.empty:
                    continue
                    
                event_chumon_col = df_event.columns[0]
                kw_col = df_event.columns[1] if len(df_event.columns) > 1 else None
                
                event_orders = df_event[event_chumon_col].astype(str).str.strip().tolist()
                all_event_orders.update(event_orders)
                
                base_orders = self.df_base.iloc[:, self.c_chumon].astype(str).str.strip()
                df_filtered = self.df_base[base_orders.isin(event_orders)].copy()
                
                if df_filtered.empty:
                    logger.info(f"イベントシート '{sheet_name}' に該当するデータはありませんでした。")
                    continue
                    
                if kw_col:
                    kw_val = df_event[kw_col].dropna().iloc[0] if not df_event[kw_col].dropna().empty else f"【{sheet_name}】"
                    prefix = str(kw_val).strip()
                else:
                    prefix = f"【{sheet_name}】"
                    
                df_filtered.iloc[:, self.c_tashizan] = prefix + " " + df_filtered.iloc[:, self.c_tashizan].astype(str)
                
                self.df_events[sheet_name] = df_filtered
                logger.info(f"イベント '{sheet_name}' 用データを抽出・キーワード({prefix})付与しました。({len(df_filtered)}件)")
                
            # その他（どのイベントシートにも記載がなかった商品）を抽出
            base_orders = self.df_base.iloc[:, self.c_chumon].astype(str).str.strip()
            df_others = self.df_base[~base_orders.isin(all_event_orders)].copy()
            if not df_others.empty:
                self.df_events["その他"] = df_others
                logger.info(f"イベント指定なし('その他')として {len(df_others)} 件を分類しました。")
                
            # df_baseを全イベントの結合データで上書き（temp_stage6.xlsx出力およびGUIでの色付けチェック用）
            self.df_base = pd.concat(self.df_events.values(), ignore_index=True)
                
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
            
        # df_baseにも結合データを反映（temp_stage7.xlsx出力およびGUIでの色付けチェック用）
        self.df_base = pd.concat(self.df_events.values(), ignore_index=True)
        
        self.save_temp("stage7")
        
    def stage8_final_format(self):
        logger.info("Stage 8: 最終フォーマット調整を実行します。")
        
        if not hasattr(self, 'df_events') or not self.df_events:
            self.df_events = {"その他": self.df_base.copy()}
            
        # まとめファイル用の辞書
        all_final_dfs = {}
            
        for event, df_event in self.df_events.items():
            df_final = pd.DataFrame()
            df_final['商品管理番号'] = df_event.iloc[:, self.c_chumon].astype(str).str.lower()
            df_final['商品名'] = df_event.iloc[:, self.c_tashizan].astype(str)
            df_final = df_final.sort_values(by='商品管理番号', ascending=False).reset_index(drop=True)
            df_final.insert(0, '採番', range(1, len(df_final) + 1))
            
            # 個別ファイルの出力: normal-item_rc{シート名}.xlsx
            safe_event_name = str(event).replace('/', '_').replace('\\', '_')
            final_output = self.output_dir / f"normal-item_rc{safe_event_name}.xlsx"
            sheet_name = safe_event_name[:31]
            df_final.to_excel(final_output, index=False, sheet_name=sheet_name)
            logger.info(f"個別ファイルを出力しました: {final_output.name} ({len(df_final)}件)")
            
            all_final_dfs[sheet_name] = df_final

        # まとめファイル (ALL) の作成
        # normal-item_result.xlsx (または normal-item_rc_ALL.xlsx) として出力
        summary_file = self.output_dir / "normal-item_rc_ALL.xlsx"
        
        # 分割前の全結合データを作る
        if all_final_dfs:
            df_all = pd.concat(all_final_dfs.values(), ignore_index=True)
            # 再ソートして採番を振り直し
            df_all = df_all.drop(columns=['採番']).sort_values(by='商品管理番号', ascending=False).reset_index(drop=True)
            df_all.insert(0, '採番', range(1, len(df_all) + 1))
            
            with pd.ExcelWriter(summary_file, engine='openpyxl') as writer:
                # 1つ目のシート: 分割前
                df_all.to_excel(writer, index=False, sheet_name="分割前")
                
                # 2つ目以降のシート: 各イベント（目玉、その他など）
                for sheet_name, df_f in all_final_dfs.items():
                    # Excelのシート名制限（同じ名前は不可）のためそのまま出力
                    df_f.to_excel(writer, index=False, sheet_name=sheet_name)
                    
            logger.info(f"全シート結合ファイルを出力しました: {summary_file.name}")

    def save_temp(self, stage_name):
        temp_output = self.output_dir / f"temp_{stage_name}.xlsx"
        self.df_base.to_excel(temp_output, index=False)
        logger.info(f"[{stage_name}] 中間データを保存しました: {temp_output}")

if __name__ == "__main__":
    logger.info("GUI経由での実行を推奨します。（python gui.py）")
