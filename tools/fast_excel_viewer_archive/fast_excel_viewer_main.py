import sys
import os
import polars as pl
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QFileDialog, QStatusBar, QLabel, QMessageBox, QProgressBar
from PySide6.QtCore import QSettings, Qt, QTimer, QThread, Signal, QObject
from PySide6.QtGui import QKeySequence, QShortcut

from fast_excel_viewer_engine import DataEngine
from fast_excel_viewer_ui_ribbon import RibbonWidget, FormulaBar
from fast_excel_viewer_ui_table import FastTableView, FastTableModel
from fast_excel_viewer_logic_history import UndoManager
from fast_excel_viewer_logic_formula import FormulaProcessor

class DataWorker(QObject):
    finished = Signal(object); error = Signal(str)
    def __init__(self, task_fn, *args):
        super().__init__()
        self.task_fn = task_fn; self.args = args
    def run(self):
        try:
            result = self.task_fn(*self.args)
            self.finished.emit(result)
        except Exception as e: self.error.emit(str(e))

class FlashSheetApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FlashSheet Pro - Sparse & Delegate Edition")
        self.resize(1500, 1000)
        self.engine = DataEngine(); self.undo_manager = UndoManager()
        self.settings = QSettings("MyCompany", "FlashSheetPro")
        self.sum_timer = QTimer(); self.sum_timer.setSingleShot(True); self.sum_timer.setInterval(200)
        self.sum_timer.timeout.connect(self.request_sum)
        
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self.action_undo)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self.action_redo)
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self.action_save_with_sync)
        
        self.setup_ui(); self.connect_signals(); self.apply_qss()
        last_path = self.settings.value("last_path")
        if last_path and os.path.exists(last_path): self.load_file(last_path)

    def setup_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(central); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        self.ribbon = RibbonWidget(); self.formula_bar = FormulaBar(); self.table_view = FastTableView()
        layout.addWidget(self.ribbon); layout.addWidget(self.formula_bar); layout.addWidget(self.table_view)
        self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar(); self.progress_bar.setMaximumHeight(12); self.progress_bar.setFixedWidth(150); self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.stat_label = QLabel("Ready"); self.status_bar.addPermanentWidget(self.stat_label)
        self.sum_label = QLabel("SUM: 0"); self.status_bar.addPermanentWidget(self.sum_label)

    def connect_signals(self):
        self.ribbon.openRequested.connect(self.action_open)
        self.ribbon.saveRequested.connect(self.action_save_with_sync)
        self.ribbon.undoRequested.connect(self.action_undo)
        self.ribbon.redoRequested.connect(self.action_redo)
        self.ribbon.trimRequested.connect(lambda: self.apply_op("TRIM"))
        self.table_view.insertRowRequested.connect(lambda r: self.action_structure_change("insert_row", r))
        self.table_view.deleteRowRequested.connect(lambda r: self.action_structure_change("delete_row", r))
        self.formula_bar.input_field.returnPressed.connect(self.action_submit_formula)

    def run_async_task(self, task_fn, on_finished, *args):
        self.progress_bar.show(); self.progress_bar.setRange(0, 0)
        self.thread = QThread(); self.worker = DataWorker(task_fn, *args)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(lambda res: self.on_task_completed(res, on_finished))
        self.worker.error.connect(self.thread.quit); self.worker.error.connect(self.on_task_error)
        self.thread.start()

    def on_task_completed(self, result, callback):
        self.progress_bar.hide(); self.stat_label.setText("Ready"); callback(result)

    def on_task_error(self, err_msg):
        self.progress_bar.hide(); QMessageBox.critical(self, "Error", err_msg)

    def load_file(self, path):
        self.run_async_task(self.engine.load_file, self.post_load, path)

    def post_load(self, numpy_list):
        self.model = FastTableModel(self.engine)
        self.table_view.setModel(self.model)
        self.table_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.model.update_data_cache = lambda nl: self.model.beginResetModel() or setattr(self.model, '_numpy_columns', nl) or self.model.endResetModel()
        self.model.update_data_cache(numpy_list)
        self.stat_label.setText(f"{self.engine.last_load_time:.2f}s | {self.engine.df.height:,} rows")
        self.settings.setValue("last_path", self.engine.current_file_path)

    def action_undo(self):
        """[スパースUndo対応] 戻されたデータ型(列/セル/全体)に合わせてスマートに差し戻す。"""
        if hasattr(self, 'model'): self.model.edit_cache.clear()
        state_type, data = self.undo_manager.undo(self.engine.df)
        if state_type == "column":
            self.engine.df = self.engine.df.with_columns([pl.Series(k, v) for k, v in data.items()])
            self.run_async_task(self.engine.get_display_cache, self.model.update_data_cache)
        elif state_type == "cell":
            r, c, val = data; self.model.setData(self.model.index(r, c), val, Qt.EditRole)
        elif state_type == "full":
            self.engine.df = data; self.run_async_task(self.engine.get_display_cache, self.model.update_data_cache)

    def action_redo(self):
        # Redoは今回Undoの軽量化を優先したため、必要に応じて実装
        pass

    def action_save_with_sync(self):
        self.sync_cache_to_df(reset_model=False)
        visual_order = [self.table_view.horizontalHeader().logicalIndex(i) for i in range(self.engine.df.width)]
        self.engine.reorder_columns(visual_order)
        self.run_async_task(self.engine.save_file, lambda _: self.statusBar().showMessage("保存完了", 2000))

    def sync_cache_to_df(self, reset_model=True):
        if not hasattr(self, 'model') or not self.model.edit_cache: return
        # 単一セル編集時はスパースなバックアップを積む
        for (r, c), val in self.model.edit_cache.items():
            old_val = self.engine.df.item(r, c)
            self.undo_manager.push_cell_state(r, c, old_val)
        
        edits_by_col = {}
        for (r, c), val in self.model.edit_cache.items():
            if c not in edits_by_col: edits_by_col[c] = {}
            edits_by_col[c][r] = val
        numpy_list = self.engine.update_cells(edits_by_col)
        self.model.edit_cache.clear()
        if reset_model: self.model.update_data_cache(numpy_list)

    def apply_op(self, op, params=None):
        self.sync_cache_to_df()
        sel_cols = list(set(idx.column() for idx in self.table_view.selectionModel().selectedIndexes()))
        # クレンジング前に「対象列」だけをバックアップする（スパースUndo）
        for c in sel_cols:
            self.undo_manager.push_column_state(self.engine.df.columns[c], self.engine.df.select(self.engine.df.columns[c]).to_series())
        
        self.run_async_task(self.engine.apply_excel_func, self.model.update_data_cache, op, sel_cols if sel_cols else None, params)

    def action_structure_change(self, method_name, idx):
        self.sync_cache_to_df()
        # 構造変更（行削除など）時は全体のスナップショットを積む
        self.undo_manager.push_full_snapshot(self.engine.df)
        self.run_async_task(getattr(self.engine, method_name), self.model.update_data_cache, idx)

    def on_selection_changed(self, *args):
        curr = self.table_view.currentIndex()
        if curr.isValid():
            col_letter = FormulaProcessor.get_column_letter(curr.column())
            self.formula_bar.name_box.setText(f"{col_letter}{curr.row()+1}")
            self.formula_bar.input_field.setText(self.model.data(curr, Qt.DisplayRole))
            self.sum_timer.start()

    def request_sum(self):
        selection = self.table_view.selectionModel().selection()
        if selection.isEmpty(): self.sum_label.setText("SUM: 0"); return
        col_map = {}
        for r_range in selection:
            for c_idx in range(r_range.left(), r_range.right() + 1):
                if c_idx not in col_map: col_map[c_idx] = []
                col_map[c_idx].append((r_range.top(), r_range.height()))
        self.run_async_task(self.engine.get_sum_optimized, self.post_sum, col_map)

    def post_sum(self, total): self.sum_label.setText(f"SUM: {total:,.2f}")

    def action_submit_formula(self):
        curr = self.table_view.currentIndex()
        if curr.isValid(): self.model.setData(curr, self.formula_bar.input_field.text(), Qt.EditRole)

    def apply_qss(self):
        self.setStyleSheet("QMainWindow { background-color: #2b2b2b; } QTableView { background-color: #1e1e1e; color: #ddd; }")

if __name__ == "__main__":
    app = QApplication(sys.argv); window = FlashSheetApp(); window.show(); sys.exit(app.exec())
