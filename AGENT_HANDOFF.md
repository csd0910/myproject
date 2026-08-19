# Agent Handoff (Antigravity 2.0 連携用プロンプト)

## 今回のプロジェクト概要
現場が手作業で行っていたExcel/CSVのデータ加工業務を自動化するPythonツールを作成しています。
プロジェクト名：`UploadDataCreate`

## 完了した内容と意図
- 現場の担当者が作業内容を書き残したExcelの吹き出し（Shapes）をPythonで抽出し、業務プロセスを解読（`process_specification.md` を作成）。
- `main.py` に `pandas` を用いたファイル読み込みと、前半（Stage 1〜4: 更新除外、取り寄せ品除外、医薬品除外、特定文字列削除）のベースロジックを実装しました。
- ユーザー要望を受け、Tkinterを用いたステップバイステップ実行用のUI（`gui.py`）を作成し、全8工程のステータス管理機能を持たせました。
- マージファイルの増減やイベント条件への柔軟な対応のため、各種設定を外部ファイルに分離し、UIから `config_sample.json` を読み込むアーキテクチャに変更しました。

## 関連ファイル・パス一覧
* **実装対象（メイン処理）**: `c:\Users\フォーレスト026\MyProject\UploadDataCreate\main.py`
* **実装対象（UI）**: `c:\Users\フォーレスト026\MyProject\UploadDataCreate\gui.py`
* **設定ファイルサンプル**: `c:\Users\フォーレスト026\MyProject\UploadDataCreate\config_sample.json`
* **要件定義書**: `c:\Users\フォーレスト026\MyProject\UploadDataCreate\process_specification.md`

---

## 次に行うべきタスク (Antigravity 2.0 へのお願い)
UIのプロトタイプ実装および設定ファイルの構造が定まったため、今後は以下の手順で開発を進めてください。

1. **UIとロジックの結合**:
   - `gui.py` の「作業開始」ボタン押下時に、`config_sample.json` の内容を読み込み、`main.py` のデータ処理クラス/関数へ引き渡す処理を実装。
2. **後半ロジック（Stage 5〜8）の実装**:
   - JSON設定で定義したイベント情報に基づき、「3. 文字列操作・条件付与」（送料無料、キーワード付与、文字数制限）および「4. 最終フォーマット調整」を実装。
3. **ステップごとのプレビュー（中間出力）**:
   - ユーザーが各Stage完了時に内容を確認できるよう、中間データをファイル出力するか、Pandera等を用いた簡易ビューを表示する仕組みを組み込む。

※ 一度に全て実装すると不具合の切り分けが難しくなるため、段階的にコードを構築してください。
