# セットアップガイド

このプロジェクトを他のPCで動かすための手順です。

## 1. リポジトリのクローン
Gitがインストールされていることを確認し、リポジトリをダウンロードします。

```powershell
git clone <リポジトリのURL>
cd MyProject
```

## 2. Python仮想環境の構築
プロジェクト専用の実行環境を作成します。

```powershell
# 仮想環境の作成
python -m venv .venv

# 仮想環境の有効化 (Windows PowerShell)
.\.venv\Scripts\activate
```

## 3. ライブラリのインストール
必要なパッケージを一括でインストールします。

```powershell
pip install -r requirements.txt
```

## 4. プログラムの実行
メインプログラムを起動します。

```powershell
python app/Workmemo.py
```

---
> [!NOTE]
> `.venv` フォルダや `data/` 内の個別ログ、一時ファイルはGitの管理対象外（.gitignore）に設定されています。
