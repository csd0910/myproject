import sys
import time
import re
import os
import polars as pl
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableView, QVBoxLayout, QWidget, 
    QFileDialog, QStatusBar, QHeaderView, QAbstractItemView, QMenu,
    QDialog, QLineEdit, QLabel, QPushButton, QHBoxLayout, QMessageBox,
    QTabWidget, QToolBar, QToolButton, QStyle, QFrame, QGridLayout,
    QFontComboBox, QComboBox, QColorDialog
)
from PySide6.QtCore import Qt, QAbstractTableModel, QThread, Signal, QModelIndex, QSize, QSettings
from PySide6.QtGui import QAction, QGuiApplication, QColor, QPalette, QKeySequence, QIcon, QFont

# =================================================================
# 1. ExcelEngine (Polars演算コア)
# =================================================================
class ExcelEngine:
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
        return self.df

    def save_file(self, path=None):
        target = path if path else self.current_file_path
        if not target: return False
        self.df.write_csv(target if target.lower().endswith(".csv") else target.replace(".xlsx", ".csv"))
        return True

    def reorder_columns(self, visual_order):
        if self.df.width == 0: return
        self.df = self.df.select([self.df.columns[i] for i in visual_order])

    def apply_excel_func(self, func_name, col_indices, params=None):
        if self.df.width == 0: return
        cols = [self.df.columns[i] for i in col_indices] if col_indices else self.df.columns
        exprs = []
        for c in cols:
            col_expr = pl.col(c).cast(pl.Utf8)
            if func_name == "TRIM": e = col_expr.str.strip_chars()
            elif func_name == "CLEAN": e = col_expr.str.replace_all(r"[\x00-\x1F\x7F-\x9F]", "")
            elif func_name == "VALUE": e = col_expr.cast(pl.Float64, strict=False)
            elif func_name == "LEFT": e = col_expr.str.slice(0, int(params[0] if params else 1))
            elif func_name == "RIGHT": e = col_expr.str.slice(-int(params[0] if params else 1))
            elif func_name == "SUBSTITUTE": e = col_expr.str.replace_all(params[0], params[1])
            else: continue
            exprs.append(e.alias(c))
        if exprs: self.df = self.df.with_columns(exprs)

# =================================================================
# 2. UndoManager
# =================================================================
class UndoManager:
    def __init__(self, max_history=20):
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = max_history

    def push(self, df):
        self.undo_stack.append(df.clone())
        if len(self.undo_stack) > self.max_history: self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self, current_df):
        if not self.undo_stack: return None
        self.redo_stack.append(current_df.clone())
        return self.undo_stack.pop()

    def redo(self, current_df):
        if not self.redo_stack: return None
        self.undo_stack.append(current_df.clone())
        return self.redo_stack.pop()

# =================================================================
# 3. FastTableModel
# =================================================================
class FastTableModel(QAbstractTableModel):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.style_map = {}

    def rowCount(self, parent=QModelIndex()): return self.engine.df.height
    def columnCount(self, parent=QModelIndex()): return self.engine.df.width

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        r, c = index.row(), index.column()
        if role in (Qt.DisplayRole, Qt.EditRole):
            val = self.engine.df.item(r, c)
            return str(val) if val is not None else ""
        style = self.style_map.get((r, c), {})
        if role == Qt.FontRole:
            font = QFont(style.get("family", "Meiryo UI"))
            font.setBold(style.get("bold", False))
            return font
        if role == Qt.BackgroundRole:
            if r == 0: return QColor(50, 50, 50)
            if r % 2 == 0: return QColor(30, 30, 30)
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            try:
                self.engine.df[index.row(), index.column()] = value
                self.dataChanged.emit(index, index, [Qt.DisplayRole])
                return True
            except: return False
        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                res = ""; n = section
                while n >= 0: res = chr(n % 26 + ord('A')) + res; n = n // 26 - 1
                return res
            else: return str(section + 1)
        return None

# =================================================================
# 4. RibbonUI (全てのボタンを再定義)
# =================================================================
class RibbonUI(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(145)
        self.setup_tabs()

    def setup_tabs(self):
        # ファイル
        file_tab = QWidget(); f_lay = QHBoxLayout(file_tab)
        self.btn_open = self.create_tool("開く", QStyle.SP_DialogOpenButton, f_lay)
        self.btn_save = self.create_tool("上書き", QStyle.SP_DialogSaveButton, f_lay)
        f_lay.addStretch(); self.addTab(file_tab, "ファイル")

        # ホーム
        home_tab = QWidget(); h_lay = QHBoxLayout(home_tab)
        self.btn_undo = self.create_tool("Undo", QStyle.SP_ArrowBack, h_lay)
        self.btn_redo = self.create_tool("Redo", QStyle.SP_ArrowForward, h_lay)
        self.btn_bold = self.create_tool("太字", QStyle.SP_DialogYesButton, h_lay)
        h_lay.addStretch(); self.addTab(home_tab, "ホーム")

        # データ
        data_tab = QWidget(); d_lay = QHBoxLayout(data_tab)
        self.btn_trim = self.create_tool("TRIM", QStyle.SP_BrowserReload, d_lay)
        self.btn_clean = self.create_tool("重複削除", QStyle.SP_TrashIcon, d_lay)
        d_lay.addStretch(); self.addTab(data_tab, "データ")

    def create_tool(self, text, icon_std, layout):
        btn = QToolButton()
        btn.setText(text); btn.setIcon(self.style().standardIcon(icon_std))
        btn.setIconSize(QSize(32, 32)); btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setFixedWidth(80); layout.addWidget(btn); return btn

# =================================================================
# 5. FormulaBar
# =================================================================
class FormulaBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(35)
        layout = QHBoxLayout(self); layout.setContentsMargins(5, 2, 5, 2)
        self.name_box = QLineEdit("A1"); self.name_box.setFixedWidth(80); self.name_box.setReadOnly(True); self.name_box.setAlignment(Qt.AlignCenter)
        self.fx_label = QLabel(" 𝑓𝑥 "); self.fx_label.setStyleSheet("font-weight: bold; color: #107c41; font-size: 16px;")
        self.input_field = QLineEdit()
        layout.addWidget(self.name_box); layout.addWidget(self.fx_label); layout.addWidget(self.input_field)

# =================================================================
# 6. FlashSheet Pro (Main Window)
# =================================================================
class FlashSheetPro(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FlashSheet Pro - Ultimate Performance Edition")
        self.resize(1500, 1000)
        
        self.engine = ExcelEngine()
        self.undo_manager = UndoManager()
        self.settings = QSettings("MyCompany", "FlashSheetPro")
        
        self.setup_ui()
        self.apply_qss()
        self.set_model(FastTableModel(self.engine))
        
        header = self.table_view.horizontalHeader()
        header.setSectionsMovable(True)
        header.sectionMoved.connect(self.on_column_moved)
        
        self.setup_events()
        
        last_path = self.settings.value("last_path")
        if last_path and os.path.exists(last_path): self.load_file(last_path)

    def setup_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        layout = QVBoxLayout(central); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        self.ribbon = RibbonUI(); layout.addWidget(self.ribbon)
        self.formula_bar = FormulaBar(); layout.addWidget(self.formula_bar)
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table_view.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        layout.addWidget(self.table_view)
        self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar)
        self.stat_label = QLabel("Ready"); self.status_bar.addPermanentWidget(self.stat_label)
        self.sum_label = QLabel("SUM: 0"); self.sum_label.setStyleSheet("color: #107c41; font-weight: bold; margin-right: 20px;")
        self.status_bar.addPermanentWidget(self.sum_label)

    def set_model(self, model):
        self.model = model; self.table_view.setModel(self.model)

    def setup_events(self):
        self.table_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.ribbon.btn_open.clicked.connect(self.action_open)
        self.ribbon.btn_save.clicked.connect(lambda: self.engine.save_file())
        self.ribbon.btn_undo.clicked.connect(self.action_undo)
        self.ribbon.btn_redo.clicked.connect(self.action_redo)
        self.ribbon.btn_bold.clicked.connect(self.action_toggle_bold)
        self.ribbon.btn_trim.clicked.connect(lambda: self.apply_func("TRIM"))
        self.ribbon.btn_clean.clicked.connect(lambda: self.apply_func("CLEAN"))
        self.formula_bar.input_field.returnPressed.connect(self.action_submit_formula)

    def apply_qss(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QTabWidget::pane { border-top: 1px solid #444; }
            QTabBar::tab { background: #333; color: #ccc; padding: 10px 20px; }
            QTabBar::tab:selected { background: #107c41; color: white; }
            QTableView { background-color: #1e1e1e; color: #ddd; gridline-color: #333; selection-background-color: #107c41; }
            QLineEdit { background-color: #333; color: white; border: 1px solid #555; padding: 4px; }
            QHeaderView::section { background-color: #333; color: #bbb; border: 1px solid #444; }
        """)

    def load_file(self, path):
        try:
            self.engine.load_file(path)
            self.set_model(FastTableModel(self.engine))
            self.table_view.selectionModel().selectionChanged.connect(self.on_selection_changed)
            self.stat_label.setText(f"{self.engine.last_load_time:.2f}s | {self.engine.df.height:,} rows")
            self.settings.setValue("last_path", path)
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def action_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "開く", "", "Data (*.xlsx *.xlsm *.csv)")
        if path: self.load_file(path)

    def action_undo(self):
        prev = self.undo_manager.undo(self.engine.df)
        if prev is not None:
            self.model.beginResetModel(); self.engine.df = prev; self.model.endResetModel()

    def action_redo(self):
        nxt = self.undo_manager.redo(self.engine.df)
        if nxt is not None:
            self.model.beginResetModel(); self.engine.df = nxt; self.model.endResetModel()

    def on_column_moved(self, logicalIndex, oldVisualIndex, newVisualIndex):
        header = self.table_view.horizontalHeader()
        visual_order = [header.logicalIndex(i) for i in range(header.count())]
        self.engine.reorder_columns(visual_order)

    def apply_func(self, func, params=None):
        self.undo_manager.push(self.engine.df)
        self.model.beginResetModel()
        sel = list(set(idx.column() for idx in self.table_view.selectionModel().selectedIndexes()))
        self.engine.apply_excel_func(func, col_indices=sel if sel else None, params=params)
        self.model.endResetModel()

    def on_selection_changed(self):
        curr = self.table_view.currentIndex()
        if curr.isValid():
            n = curr.column(); res = ""
            while n >= 0: res = chr(n % 26 + ord('A')) + res; n = n // 26 - 1
            self.formula_bar.name_box.setText(f"{res}{curr.row()+1}")
            self.formula_bar.input_field.setText(self.model.data(curr, Qt.DisplayRole))
            self.update_sum_status()

    def update_sum_status(self):
        idxs = self.table_view.selectionModel().selectedIndexes()
        if len(idxs) < 2: self.sum_label.setText("SUM: 0"); return
        try:
            col_idx = idxs[0].column()
            row_start = min(idx.row() for idx in idxs)
            row_end = max(idx.row() for idx in idxs)
            total = self.engine.df.select(pl.col(self.engine.df.columns[col_idx]).slice(row_start, row_end-row_start+1).cast(pl.Float64, strict=False).sum()).item()
            self.sum_label.setText(f"SUM: {total:,.2f}" if total else "SUM: 0")
        except: pass

    def action_submit_formula(self):
        curr = self.table_view.currentIndex()
        if curr.isValid():
            self.undo_manager.push(self.engine.df)
            self.model.setData(curr, self.formula_bar.input_field.text(), Qt.EditRole)

    def action_toggle_bold(self):
        for idx in self.table_view.selectionModel().selectedIndexes():
            r, c = idx.row(), idx.column()
            s = self.model.style_map.get((r,c), {}); s["bold"] = not s.get("bold", False)
            self.model.style_map[(r,c)] = s
        self.model.layoutChanged.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F2: self.table_view.edit(self.table_view.currentIndex())
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_Z: self.action_undo()
            if event.key() == Qt.Key_Y: self.action_redo()
        super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FlashSheetPro()
    window.show()
    sys.exit(app.exec())
