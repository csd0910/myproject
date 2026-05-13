from PySide6.QtWidgets import QTabWidget, QWidget, QHBoxLayout, QToolButton, QStyle, QLineEdit, QLabel, QFontComboBox, QComboBox
from PySide6.QtCore import Qt, QSize, Signal

class RibbonWidget(QTabWidget):
    openRequested = Signal()
    saveRequested = Signal()
    undoRequested = Signal()
    redoRequested = Signal()
    boldRequested = Signal()
    colorRequested = Signal()
    fillRequested = Signal()
    fontChanged = Signal(str) # フォント名
    sizeChanged = Signal(str) # サイズ
    sumRequested = Signal()
    sortAscRequested = Signal()
    sortDescRequested = Signal()
    trimRequested = Signal()
    cleanRequested = Signal()
    uniqueRequested = Signal()
    helpRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(145)
        self.setup_tabs()

    def setup_tabs(self):
        # ファイル
        file_tab = QWidget(); f_lay = QHBoxLayout(file_tab)
        self.create_tool("開く", QStyle.SP_DialogOpenButton, f_lay, self.openRequested)
        self.create_tool("上書き", QStyle.SP_DialogSaveButton, f_lay, self.saveRequested)
        f_lay.addStretch(); self.addTab(file_tab, "ファイル")

        # ホーム
        home_tab = QWidget(); h_lay = QHBoxLayout(home_tab)
        self.create_tool("Undo", QStyle.SP_ArrowBack, h_lay, self.undoRequested)
        self.create_tool("Redo", QStyle.SP_ArrowForward, h_lay, self.redoRequested)
        self.create_tool("太字", QStyle.SP_DialogYesButton, h_lay, self.boldRequested)
        self.create_tool("色", QStyle.SP_DialogResetButton, h_lay, self.colorRequested)
        self.create_tool("塗りつぶし", QStyle.SP_DesktopIcon, h_lay, self.fillRequested)
        
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(lambda f: self.fontChanged.emit(f.family()))
        h_lay.addWidget(self.font_combo)
        
        self.size_combo = QComboBox()
        self.size_combo.addItems(["9","10","11","12","14","16","18","20"])
        self.size_combo.currentTextChanged.connect(self.sizeChanged.emit)
        h_lay.addWidget(self.size_combo)
        
        h_lay.addStretch(); self.addTab(home_tab, "ホーム")

        # データ
        data_tab = QWidget(); d_lay = QHBoxLayout(data_tab)
        self.create_tool("昇順", QStyle.SP_ArrowUp, d_lay, self.sortAscRequested)
        self.create_tool("降順", QStyle.SP_ArrowDown, d_lay, self.sortDescRequested)
        self.create_tool("TRIM", QStyle.SP_BrowserReload, d_lay, self.trimRequested)
        self.create_tool("重複削除", QStyle.SP_TrashIcon, d_lay, self.uniqueRequested)
        d_lay.addStretch(); self.addTab(data_tab, "データ")

        # ヘルプ
        help_tab = QWidget(); hl_lay = QHBoxLayout(help_tab)
        self.create_tool("説明書", QStyle.SP_MessageBoxQuestion, hl_lay, self.helpRequested)
        hl_lay.addStretch(); self.addTab(help_tab, "ヘルプ")

    def create_tool(self, text, icon_std, layout, signal):
        btn = QToolButton()
        btn.setText(text); btn.setIcon(self.style().standardIcon(icon_std))
        btn.setIconSize(QSize(32, 32)); btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setFixedWidth(80); btn.clicked.connect(signal.emit); layout.addWidget(btn); return btn

class FormulaBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(35)
        layout = QHBoxLayout(self); layout.setContentsMargins(5, 2, 5, 2)
        self.name_box = QLineEdit("A1"); self.name_box.setFixedWidth(80); self.name_box.setReadOnly(True); self.name_box.setAlignment(Qt.AlignCenter)
        self.fx_label = QLabel(" 𝑓𝑥 "); self.fx_label.setStyleSheet("font-weight: bold; color: #107c41; font-size: 16px;")
        self.input_field = QLineEdit()
        layout.addWidget(self.name_box); layout.addWidget(self.fx_label); layout.addWidget(self.input_field)
