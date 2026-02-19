# 作業記録ツール Pro - セットアップガイド

このリポジトリは、作業を記録し、集計・分析およびExcelレポートを出力するためのツールです。
他のPCで同じ環境を構築するには、以下の手順に従ってください。

## 1. 事前準備
- **Python 3.10以上**がインストールされていることを確認してください。

## 2. セットアップ手順
コマンドプロンプトやPowerShellを開き、以下のコマンドを順番に実行します。

### (1) リポジトリのクローン（またはコピー）
リポジトリをダウンロードし、フォルダ（MyProject）へ移動します。

### (2) 仮想環境の作成
```powershell
python -m venv .venv
```

### (3) 仮想環境の有効化
```powershell
.venv\Scripts\activate
```

### (4) 依存ライブラリのインストール
```powershell
pip install -r requirements.txt
```

## 3. アプリの起動
以下のコマンドでアプリが起動します。
```powershell
python app/Workmemo.py
```

## フォルダ構造
- `app/` : アプリケーション本体 (`Workmemo.py`)
- `data/` : 作業データ (`work_log.csv`) と設定 (`config.json`)
- `tools/` : 補助ツールやドキュメント

## 注意事項
- **データについて**: `data/work_log.csv` が作業データ本体です。
- **設定について**: `data/config.json` に担当者名などが保存されます。
