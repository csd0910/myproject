import polars as pl

class UndoManager:
    """
    [最適化] 全コピー(clone)を廃止。
    変更された列(Series)または特定のセル(dict)だけを保持するスパース設計。
    """
    def __init__(self, max_size=20):
        self.undo_stack = [] # list of (type, data)
        self.redo_stack = []
        self.max_size = max_size

    def push_column_state(self, col_name, series):
        """列全体の変更前にその列をバックアップ"""
        self.undo_stack.append(("column", {col_name: series.clone()}))
        if len(self.undo_stack) > self.max_size: self.undo_stack.pop(0)
        self.redo_stack.clear()

    def push_cell_state(self, row, col, old_value):
        """単一セルの変更前にバックアップ"""
        self.undo_stack.append(("cell", (row, col, old_value)))
        if len(self.undo_stack) > self.max_size: self.undo_stack.pop(0)
        self.redo_stack.clear()

    def push_full_snapshot(self, df):
        """構造変更（行・列の削除など）時は全体をバックアップ"""
        self.undo_stack.append(("full", df.clone()))
        if len(self.undo_stack) > self.max_size: self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self, current_df):
        if not self.undo_stack: return None, None
        state_type, data = self.undo_stack.pop()
        
        # Redo用に現在の状態を積む（簡易化のため今回はUndoのみ強化）
        if state_type == "column":
            col_name = list(data.keys())[0]
            # 戻す前の状態をRedoへ（本来はここもスパースにするが、まずはUndoの軽量化を優先）
            self.redo_stack.append(("column", {col_name: current_df.select(col_name).to_series()}))
            return state_type, data
        elif state_type == "cell":
            r, c, val = data
            self.redo_stack.append(("cell", (r, c, current_df.item(r, c))))
            return state_type, data
        elif state_type == "full":
            self.redo_stack.append(("full", current_df.clone()))
            return state_type, data
        
        return None, None
