# FlashSheet Pro - 最終仕様書

## 1. 共通要件
- PySide6 + Polars (calamine) を使用
- 100万行でもカクつかない仮想レンダリング
- ダークモードUI
- 前回開いたファイルの自動復元 (QSettings)

## 2. リボンUI (Flash Ribbon)
- **ファイル**: 開く, 保存(CSV/Excel)
- **ホーム**: 太字, コピー, 貼り付け, Undo/Redo, 検索, 置換
- **数式**: fxボタン, SUM, AVERAGE, VLOOKUP (Polars演算)
- **データ**: 昇順/降順ソート, テキストフィルター, 重複削除, トリム(空白除去), 改行削除
- **表示**: ウィンドウ枠固定(先頭行/先頭列), テーマ切替

## 3. 数式バー (Formula Bar)
- 名前ボックス (A1形式の現在地表示)
- 𝑓𝑥ボタン (装飾)
- 数式入力バー (セルとの双方向同期)

## 4. ヘッダー表示
- 上部ヘッダー: 列記号 (A, B, C...)
- データ1行目: 実際の項目名を表示

## 5. ショートカット・操作
- Ctrl+F (検索) / Ctrl+H (置換)
- Ctrl+Z (Undo) / Ctrl+Y (Redo)
- Ctrl+S (保存) / Ctrl+A (全選択)
- F2 (編集開始)
- Shift+Space (行選択) / Ctrl+Space (列選択)
- Ctrl+矢印キー (データ端までジャンプ)

## 6. ステータスバー
- 読込秒数表示
- 選択範囲の合計値 (SUM) をリアルタイム表示
- 行数・列数の表示

以下が5/13　10：22時点の仕様書
# 最終ミッション: FlashSheet Pro の完全実装
あなたはPythonのGUI開発(PySide6)と高速演算(Polars)の極みを知るエンジニアです。これまでの断片的な指示をすべて統合し、実用的な「Excelクローン・クレンジングツール」を単一スクリプトで作成してください。

# 1. コアスタック
- UI: PySide6 (QMainWindow)
- Data: Polars (エンジンは calamine を使用して読み込み)
- Architecture: 以下のクラスに分割して疎結合に設計せよ。
  - ExcelEngine (計算・IO・Polars操作)
  - RibbonUI (QTabWidgetによるリボンメニュー)
  - FormulaBar (数式入力・番地表示)
  - FastTableModel (QAbstractTableModelの仮想化実装)
  - UndoManager (スナップショット管理)

# 2. リボンメニューのタブと機能 (image_73797e.png を参照)
- ファイル: 新規, 開く, 上書き保存
- ホーム: フォント(名,サイズ,太字), 文字色, 塗りつぶし, 配置, 表示形式
- 数式: SUM, VLOOKUPをPolarsのベクトル演算で実装。入力バーを常に同期。
- データ: 昇順/降順並べ替え, フィルタ機能, クレンジング(空白・改行削除, 重複削除)
- 表示: ウィンドウ枠固定(先頭行・先頭列) ※QTableViewの分割又はオーバーレイ手法
- ヘルプ: 操作説明とショートカット一覧の表示

# 3. ショートカット (Excel Native)
- Ctrl+F: 検索 / Ctrl+H: 置換 (Polarsでミリ秒実行)
- Ctrl+Z/Y: Undo/Redo
- F2/Double Click: セル編集
- Ctrl+Arrow: データ端までジャンプ
- Shift+Space / Ctrl+Space: 行・列選択

# 4. 実行性能とデザイン
- 100MB超の読み込み速度をステータスバーに表示。
- デザインはExcelライクなダークモードQSSを適用。
- セル単位のループ処理は禁止。置換や計算はすべてPolarsの列演算で行うこと。

上記要件をすべて満たし、コード内に「なぜその実装が高速なのか」の解説を日本語でコメントとして充実させて出力せよ。

2026/05/13　10：37時点の仕様書
追加されいない機能があるので必ず確認して実装すること。漏らさずチェックをすること。
・A列B列の部分をドラッグして列の入替をできるようにしたい。
・セルの直接入力編集ができるようにしたい。セルをクリックした後にセル内に入力できるようにしたい。
・関数を以下のものを追加しExcelと同じように動かしたい。
　よく使う関数
   TRIM: 余分なスペースを削除します 。
   CLEAN: 改行などの印刷できない文字を削除します 。
   SUBSTITUTE: 特定の文字列を置換・削除します 。
   LEFT / RIGHT / MID: 必要な部分だけ切り出します 。
   VALUE: 文字列の数字を数値に変換します 。
   TEXT: 日付や数値の表示形式をそろえます 。
   IFERROR: エラー値を空欄や別値に置き換えます 。
   COUNTIF: 重複や条件一致の確認に使います 。

・動作速度の改善。100万行でもカクつかないようにできないか。

2026/05/13　10：56時点での変更
# Role
あなたは大規模デスクトップアプリのアーキテクトです。
現在1つのファイルにまとまっているコードを、保守性と拡張性を高めるために「マルチファイル・モジュール構成」へリファクタリングしてください。

ファイル名,クラス名（例）,役割
fast_excel_viewer_main.py,FlashSheetApp,司令塔。アプリの起動、各部品の組み立て、イベントの橋渡しを行う。
fast_excel_viewer_engine.py,DataEngine,データ層。Polarsによる読込・保存・ソート・フィルタ・一括クレンジング計算を担当。
fast_excel_viewer_ui_ribbon.py,RibbonWidget,表示層（上部）。リボンUIの配置とボタンクリック時のシグナル発火を担当。
fast_excel_viewer_ui_table.py,DataTable / DataModel,表示層（中央）。仮想スクロール、セルの描画、Excelライクな操作感の制御。
fast_excel_viewer_logic_formula.py,FormulaParser,"論理層。Excel関数（SUM, VLOOKUP等）の解析とPolars演算への変換。"
fast_excel_viewer_logic_history.py,HistoryStack,管理層。Undo/Redo（元に戻す/やり直し）のスナップショット管理。
# Constraints: Naming Convention
すべての部品（ファイル名）は `fast_excel_viewer_*******.py` という形式で統一し、機能ごとに独立したクラスとして定義せよ。

# Directory & Class Structure
以下の6つのファイルに分割し、お互いにシグナル(Signal/Slot)で通信する設計にせよ。

1. **fast_excel_viewer_main.py**:
   - 全体のエントリーポイント。
   - 他のすべてのモジュールをインポートし、メインウィンドウに配置する。
2. **fast_excel_viewer_engine.py (Class: DataEngine)**:
   - Polarsを用いた高速演算ロジックをカプセル化せよ。UIに関するコードは一切含めないこと。
3. **fast_excel_viewer_ui_ribbon.py (Class: RibbonWidget)**:
   - image_73797e.png のタブ構成を再現したUIコンポーネント。
   - 各ボタンは押下時にカスタムシグナルを送信せよ。
4. **fast_excel_viewer_ui_table.py (Class: FastTableView / FastTableModel)**:
   - QTableViewとQAbstractTableModelを実装。
   - 数百万行をフリーズさせずに表示する仮想描画ロジックを保持せよ。
5. **fast_excel_viewer_logic_formula.py (Class: FormulaProcessor)**:
   - 入力された数式文字列をパースし、DataEngineに計算を依頼するロジック。
6. **fast_excel_viewer_logic_history.py (Class: UndoManager)**:
   - 編集履歴をスタック管理し、メモリ使用量に配慮したUndo/Redo機能。

# Requirements
- **Loose Coupling**: 各クラスは直接お互いの内部変数に触れず、メソッドやシグナルを通じてやり取りすること。
- **Import Logic**: `from fast_excel_viewer_engine import DataEngine` のような形式で正しく呼び出せるコードにせよ。
- **Fast Execution**: ファイルを分割しても、Polarsの読み込み速度やスクロールの軽快さを損なわないこと。

# Output
- 各ファイルの内容を順番に出力せよ。
- 最後に、これらのファイルを1つのフォルダに配置して実行する方法を解説せよ。

重要：自分の生成する内容をまず疑え。
重要：遅いものを速くして効率化図りたいからとにかく最速で動くものを。
重要：ミスは減らして効率化を。
重要：一度実装してうまくいったものを使えなくするな。
