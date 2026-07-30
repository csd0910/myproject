# Firebase セットアップ ＆ データ移行ガイド (組織ポリシー制限メモ付き)

Google Antigravity IDE と Firebase Firestore を連携させてマスタデータを安全に移行・構築するためのセットアップガイドです。

---

## 🔒 【手順 1】Firebase 秘密鍵の準備とセキュリティ対策

### ① サービスアカウントの秘密鍵取得
1. **Firebase コンソール** にアクセスし、プロジェクトを開きます。
2. 左上の歯車アイコン（プロジェクト設定） ➡️ **「サービス アカウント」** タブを選択します。
3. **「新しい秘密鍵の生成」** をクリックし、JSON ファイルをダウンロードします。
4. ダウンロードしたファイルの名称を **`firebase_credential.json`** に変更し、本プロジェクトの `ワークフローツール作成_アクセス頻度/` フォルダ直下に配置します。

> [!WARNING]
> **組織ポリシー制限への対処 (Google Cloud Org Policy)**
> 社内インフラの Google Cloud（Google Workspaceドメイン配下）の初期設定によっては、組織ポリシー **「サービス アカウントのキー作成を無効にする（constraints/iam.disableServiceAccountKeyCreation）」** が有効化されており、秘密鍵の作成・ダウンロードがブロックされる場合があります。
> この制限に遭遇した場合は、社内のGoogle Cloud管理者に依頼し、一時的に当該プロジェクトに対するポリシー制限を無効化（disable）する設定変更が必要になります。
> 参照リンク: [Google Cloud 組織ポリシーのセキュア化](https://docs.cloud.google.com/resource-manager/docs/secure-by-default-organizations?hl=ja#disable_organization_policies)

### ② セキュリティ漏洩防止対策 (Git対策)
この秘密鍵はデータベースに対するフルアクセス権限を持つため、GitHub 等の公開リポジトリに誤って送信（コミット）されないよう、事前に **`.gitignore`** に登録しておく必要があります。

同じフォルダ内の `.gitignore` に以下の行を追記しています：
```text
firebase_credential.json
```

---

## 📊 【手順 2】マスタデータの CSV 書き出し手順

Excel ファイル（`00_SystemMaster.xlsx`）からマスタデータを CSV 形式で出力します。

### ① `m_user`（ユーザーマスタ）の書き出し
1. Excel で `00_SystemMaster.xlsx` を開きます。
2. **`m_user`** シートを表示します。
3. `F12` キー（名前を付けて保存）を押し、ファイルの種類を **「CSV (カンマ区切り) (*.csv)」** に指定します。
4. ファイル名を **`m_user.csv`** として、`ワークフローツール作成_アクセス頻度/` フォルダに保存します。

### ② `m_route_form`（申請・初期経路マスタ）の書き出し
1. **`m_route_form`** シートを表示します。
2. 同様に `F12` を押し、ファイルの種類を **「CSV (カンマ区切り) (*.csv)」** に指定します。
3. ファイル名を **`m_route_form.csv`** として、同じフォルダに保存します。

---

## 🚀 【手順 3】移行スクリプトの実行 ＆ 接続設定コードの修正

マスタデータを Firebase Firestore に一括登録するための Python 移行スクリプトを実行します。

### ① 依存ライブラリのインストール
以下のコマンドで、Firebase Admin SDK などのライブラリをインストールします。
```powershell
pip install firebase-admin pandas openpyxl
```

### ② 接続設定の修正ポイント
Firebase のドキュメントから接続用の初期化コードをコピーして使用する際は、以下の構成になるよう手直しを行います。特に **Firestore クライアント（`firestore.client()`）の呼び出し部分** を追加する必要があります。

```python
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore  # 1. これを追加します

# 2. ダウンロードした秘密鍵のJSONパスを指定します
cred = credentials.Certificate("firebase_credential.json")
firebase_admin.initialize_app(cred)

# 3. これを追加することで、Firestoreが操作可能になります
db = firestore.client()
```

### ③ インポートスクリプトの実行
準備した CSV と秘密鍵が揃った状態で、以下のコマンドを実行します。
```powershell
python c:\Users\フォーレスト026\MyProject\ワークフローツール作成_アクセス頻度\migrate_to_firebase.py
```
実行が完了すると、Firestore 内に `users` と `forms` コレクションが自動生成され、マスタレコードがインポートされます。
