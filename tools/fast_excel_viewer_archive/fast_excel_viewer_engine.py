import time
import polars as pl

class DataEngine:
    def __init__(self):
        self.df = pl.DataFrame()
        self.last_load_time = 0.0
        self.current_file_path = None

    def load_file(self, path):
        start = time.time()
        if path.lower().endswith(".csv"):
            self.df = pl.read_csv(path, encoding="cp932", ignore_errors=True, has_header=False)
        else:
            self.df = pl.read_excel(path, engine="calamine", read_options={"header_row": None})
        self.last_load_time = time.time() - start
        self.current_file_path = path
        return self.get_display_cache()

    def get_display_cache(self):
        """[Workerスレッド用] 表示用のNumpy配列リストを生成。メインスレッドではやらない。"""
        if self.df.width > 0:
            return [self.df.select(pl.col(c)).to_series().to_numpy() for c in self.df.columns]
        return []

    def save_file(self, path=None):
        target = path if path else self.current_file_path
        if not target: return False
        self.df.write_csv(target if target.lower().endswith(".csv") else target.replace(".xlsx", ".csv"))
        return True

    def update_cells(self, edits_by_col):
        if not edits_by_col: return self.get_display_cache()
        exprs = []
        for c_idx, rows in edits_by_col.items():
            col_name = self.df.columns[c_idx]
            indices = list(rows.keys())
            values = list(rows.values())
            exprs.append(pl.col(col_name).scatter_at_index(indices, values).alias(col_name))
        if exprs:
            self.df = self.df.with_columns(exprs)
        return self.get_display_cache()

    def insert_row(self, row_idx):
        new_row = pl.DataFrame({c: [None] for c in self.df.columns}, schema=self.df.schema)
        if row_idx >= self.df.height: self.df = pl.concat([self.df, new_row])
        else: self.df = pl.concat([self.df.slice(0, row_idx), new_row, self.df.slice(row_idx)])
        return self.get_display_cache()

    def delete_row(self, row_idx):
        if 0 <= row_idx < self.df.height:
            self.df = pl.concat([self.df.slice(0, row_idx), self.df.slice(row_idx + 1)])
        return self.get_display_cache()

    def apply_excel_func(self, func_name, col_indices, params=None):
        if self.df.width == 0: return self.get_display_cache()
        cols = [self.df.columns[i] for i in col_indices] if col_indices else self.df.columns
        exprs = []
        for c in cols:
            col_expr = pl.col(c).cast(pl.Utf8)
            if func_name == "TRIM": e = col_expr.str.strip_chars()
            elif func_name == "CLEAN": e = col_expr.str.replace_all(r"[\x00-\x1F\x7F-\x9F]", "")
            else: continue
            exprs.append(e.alias(c))
        if exprs: self.df = self.df.with_columns(exprs)
        return self.get_display_cache()

    def get_sum_optimized(self, col_map):
        if not col_map: return 0.0
        total = 0.0
        try:
            for c_idx, r_list in col_map.items():
                col_name = self.df.columns[c_idx]
                col_series = self.df.select(pl.col(col_name)).to_series()
                for start, length in r_list:
                    total += col_series.slice(start, length).cast(pl.Float64, strict=False).sum()
            return total
        except: return 0.0
