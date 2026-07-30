# ワークフローシステム Python ＆ Firebase 移行計画書

既存の GAS ＋ Google スプレッドシートで稼働している「ForestWorkFlowSystem」を、同時アクセスに強くスケーラブルな **Python (FastAPI) ＋ Firebase (Firestore)** 構成に移行するための設計・計画書です。

---

## 🏗 システム構成図
スプレッドシートの同時書き込み制限（最大同時リクエストでエラー）を解決するため、Firebase のクラウド分散 NoSQL データベースを採用します。

```mermaid
graph TD
    User[ユーザーブラウザ (HTML/JS)] -->|APIリクエスト / Fetch| BE[Python API Server (FastAPI)]
    BE -->|Firebase Admin SDK| DB[(Firebase Firestore)]
    BE -->|SMTP| MailServer[外部SMTPメールサーバー]
    
    subgraph Firebase Cloud
        DB
    end
```

---

## 📊 データベース設計 (Firestore コレクション)

スプレッドシート上のシート群（`m_user`, `m_route_form`, `t_application`, `t_route`）を、NoSQLのドキュメントモデルに最適化してマッピングします。

### 1. `users` コレクション (ユーザーマスタ)
* **ドキュメントID**: `email` (例: `yumi.ikeda@forest.co.jp`)
* **フィールド**:
  * `name`: 文字列 (例: `"池田 友香"`)
  * `dept`: 文字列 (例: `"顧客課"`)
  * `title`: 文字列 (例: `"主任"`)
  * `isAdmin`: 真偽値 (`true`/`false`)
  * `isAllowedUser`: 真偽値 (`true`/`false`)

### 2. `forms` コレクション (申請フォーム＆初期経路マスタ)
* **ドキュメントID**: `formId` (例: `form_usb_apply`)
* **フィールド**:
  * `name`: 文字列 (例: `"申請⑦: 業務端末/SCAWメニュー/USB申請"`)
  * `description`: 文字列 (説明文)
  * `folderId`: 文字列 (Google Driveの保管フォルダID)
  * `sortOrder`: 数値 (表示順)
  * `routes`: 配列 (オブジェクトの配列)
    * `step`: 数値 (工程番号)
    * `role`: 文字列 (役割名、例: `"所属長"`)
    * `type`: 文字列 (承認タイプ、例: `"承認（全員）"` / `"承認（誰か1人）"`)
    * `defaultApprovers`: 配列 (初期設定される承認者のメールアドレス一覧)

### 3. `applications` コレクション (申請・承認履歴データ)
月別スプレッドシートへの分割は不要になり、単一のコレクションで一元管理します。
* **ドキュメントID**: `appNumber` (例: `2026071001`)
* **フィールド**:
  * `formId`: 文字列 (紐づく `forms` のID)
  * `formName`: 文字列
  * `title`: 文字列 (申請標題)
  * `applicant`: 文字列 (申請者メールアドレス)
  * `createdAt`: タイムスタンプ (作成日時)
  * `pdfName`: 文字列 (添付PDFファイル名)
  * `pdfUrl`: 文字列 (PDFの保存先URL)
  * `currentStep`: 数値 (現在の進行工程番号)
  * `globalStatus`: 文字列 (全体のステータス: `"進行中"` / `"決裁"` / `"差し戻し"` / `"引き戻し"` / `"却下"`)
  * `routes`: 配列 (各工程の承認・アクション履歴)
    * `step`: 数値
    * `role`: 文字列
    * `approver`: 文字列 (担当承認者のメールアドレス。誰か1人承認の場合は動的に決定)
    * `status`: 文字列 (`"未到達"` / `"進行中"` / `"承認"` / `"決裁"` / `"確認"` / `"差し戻し"`)
    * `actionAt`: タイムスタンプまたはnull
    * `comment`: 文字列

---

## 🚀 移行ステップ

### 【STEP 1】データベースの初期化とデータ移行（今回実施）
* 現行のスプレッドシートに保存されている「ユーザーマスタ（`m_user`）」や「フォーム・ルートマスタ（`m_route_form`）」のデータを読み込み、Firebase Firestore に移行（インポート）するための Python 移行スクリプトを作成します。

### 【STEP 2】Python バックエンドAPI (FastAPI) の構築
* Firebase Admin SDK を接続し、フロントエンドからの申請・承認リクエストを安全に処理する API を構築します。
* SMTP設定を用いた自動メール通知関数を移植します。

### 【STEP 3】フロントエンド HTML/JS の修正
* 従来の `google.script.run` を、Pythonサーバーを叩く `fetch("/api/...")` に書き換えます。
