# DX_Reverse_Engineering_Engine (DX推進アシスタント) 概要仕様書

## 1. アプリ概要
* **チャット名（会話ID）**: DX_Reverse_Engineering_Engine (最新の稼働チャット)
* **目的**: ユーザーのPC操作（Excel関数入力、コピペ、ウィンドウ操作等）をバックグラウンドでロギングし、AI（Gemini API）を用いて業務フローを分析。その結果を日報や可視化レポート（HTML、PowerPoint、Excelの吹き出し等）として自動生成する。

## 2. 構成ファイル一覧 (クリーンアップ後)

一時的な検証用スクリプト（ハードコードされたパスを持つ描画テストや結合テスト用のファイル）はすべて削除し、システムに必要な汎用ファイルのみを残しています。

### 🟢 コア・GUI・ロギング系
* **`gui_app.py`**
  * システムの本体画面。ログ記録の開始・停止、レポート生成の実行などを統括するアプリ。
* **`system_logger.py`**
  * バックグラウンドで動作し、キーボード入力・クリップボード履歴・アクティブウィンドウの変更を記録するコアエンジン。
* **`activity_logger.py`**
  * ctypesを用いたWindows APIベースの低レベルなロギング処理。

### 🧠 解析・レポート生成系 (AI処理・HTML)
* **`generate_daily_report.py`**
  * 蓄積されたログをGemini APIに送信し、業務フローの解析と日報（HTML形式）を生成するメイン処理。
* **`generate_unified_html.py`** / **`generate_integrated_html.py`**
  * 複数の日報や解析結果を、1つの見やすいHTMLファイルに統合・整形する処理群。

### 📊 プレゼン資料出力系 (PPTX生成)
以下のファイル群は、生成されたHTMLレポートから情報を抽出し、PowerPoint（.pptx）形式の提案資料やシステム構成図を自動生成するモジュールです。
* **`generate_integrated_pptx.py`** (統合版)
* **`generate_advanced_pptx.py`** (高度な装飾版)
* **`generate_ppt_detailed.py`** (詳細版)
* **`generate_ppt_proposal.py`** (提案書版)
* **`generate_system_architecture_ppt.py`** (システム構成図用)

### 📗 Excel解析・可視化系
* **`formula_analyzer.py`**
  * ExcelのCOMオブジェクトにアクセスし、シート内の数式を抽出・解析するツール。
* **`generate_visual_excel_report.py`**
  * 解析結果をもとに、Excelシート上にオートシェイプ（吹き出し）やフラグを描画し、視覚的な作業レポートを生成するモジュール。
