from PySide6.QtWidgets import QTableView, QAbstractItemView, QMenu, QHeaderView, QStyledItemDelegate, QStyle
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from fast_excel_viewer_logic_formula import FormulaProcessor
import polars as pl

class ExcelItemDelegate(QStyledItemDelegate):
    """
    [最適化] セルの描画（色・配置）をDelegate側で制御。
    Python側のdata()呼び出し回数を減らし、描画を高速化する。
    """
    def paint(self, painter, option, index):
        # 数値なら右詰め、それ以外は左詰め（簡易判定）
        text = index.data(Qt.DisplayRole)
        try:
            float(text)
            option.displayAlignment = Qt.AlignRight | Qt.AlignVCenter
        except:
            option.displayAlignment = Qt.AlignLeft | Qt.AlignVCenter
        
        super().paint(painter, option, index)

class FastTableModel(QAbstractTableModel):
    COLOR_HEADER = QColor(60, 60, 60)
    COLOR_ALT = QColor(35, 35, 35)
    COLOR_NORMAL = QColor(25, 25, 25)
    FONT_DEFAULT = QFont("Meiryo UI", 9)

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.edit_cache = {}
        self._col_letters = [FormulaProcessor.get_column_letter(i) for i in range(1000)]
        self._numpy_columns = []
        self.refresh_column_cache_immediate()

    def refresh_column_cache_immediate(self):
        if self.engine.df.width > 0:
            self._numpy_columns = [self.engine.df.select(pl.col(c)).to_series().to_numpy() for c in self.engine.df.columns]
        else:
            self._numpy_columns = []

    def rowCount(self, parent=QModelIndex()): return self.engine.df.height
    def columnCount(self, parent=QModelIndex()): return self.engine.df.width

    def flags(self, index):
        if not index.isValid(): return Qt.NoItemFlags
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        r, c = index.row(), index.column()
        
        # テキスト表示のみに集中
        if role in (Qt.DisplayRole, Qt.EditRole):
            if (r, c) in self.edit_cache: return self.edit_cache[(r, c)]
            try:
                val = self._numpy_columns[c][r]
                return str(val) if val is not None else ""
            except: return ""
        
        if role == Qt.BackgroundRole:
            if r == 0: return self.COLOR_HEADER
            return self.COLOR_ALT if r % 2 == 0 else self.COLOR_NORMAL
        if role == Qt.FontRole: return self.FONT_DEFAULT
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            r, c = index.row(), index.column()
            # 変更前の値を個別に返す（スパースUndo用）
            old_val = self.data(index, Qt.DisplayRole)
            self.edit_cache[(r, c)] = value
            try: self._numpy_columns[c][r] = value
            except: pass
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            return old_val # 以前の値を返す
        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self._col_letters[section] if section < len(self._col_letters) else "?"
            return str(section + 1)
        return None

class FastTableView(QTableView):
    insertRowRequested = Signal(int); deleteRowRequested = Signal(int)
    insertColRequested = Signal(int); deleteColRequested = Signal(int)
    copyRequested = Signal(); pasteRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(25)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setDefaultSectionSize(100)
        
        # 【重要】Delegateを適用し、描画を高速化
        self.setItemDelegate(ExcelItemDelegate(self))
        
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerItem)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.show_col_menu)
        self.verticalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.verticalHeader().customContextMenuRequested.connect(self.show_row_menu)

    def show_row_menu(self, pos):
        row = self.verticalHeader().logicalIndexAt(pos)
        menu = QMenu(self); menu.addAction("挿入", lambda: self.insertRowRequested.emit(row))
        menu.addAction("削除", lambda: self.deleteRowRequested.emit(row)); menu.exec(self.verticalHeader().mapToGlobal(pos))

    def show_col_menu(self, pos):
        col = self.horizontalHeader().logicalIndexAt(pos)
        menu = QMenu(self); menu.addAction("挿入", lambda: self.insertColRequested.emit(col))
        menu.addAction("削除", lambda: self.deleteColRequested.emit(col)); menu.exec(self.horizontalHeader().mapToGlobal(pos))
