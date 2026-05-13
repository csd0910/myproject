import re
import polars as pl

class FormulaProcessor:
    """
    Excel風の数式をパースし、Polarsの式(Expression)に変換する。
    """
    @staticmethod
    def evaluate_sum(df, range_str):
        # 簡易実装: =SUM(A1:A10) のような形式を想定
        # 実際には A1 -> Index 変換が必要
        pass

    @staticmethod
    def get_column_letter(n):
        res = ""
        while n >= 0:
            res = chr(n % 26 + ord('A')) + res
            n = n // 26 - 1
        return res
