# TaskMining System デプロイ手順書（Google Cloud Run & Cloud SQL）

## 1. サーバー環境の準備ファイル作成
Cloud Run（コンテナ環境）で動かすために、以下の2つのファイルを作成しました。
- `requirements.txt`: 必要なPythonライブラリ（fastapi, uvicorn, psycopg2-binary, google-genaiなど）のリスト
- `Dockerfile`: Cloud Runでサーバーを起動するためのコンテナ構築手順

## 2. データベース（Cloud SQL / PostgreSQL）の準備
Firebaseの「SQL Connect」機能の裏側で動いているGoogle Cloud SQLの画面にアクセスし、接続情報を確認しました。

* **アクセス先**: [Google Cloud Console (SQL)](https://console.cloud.google.com/sql/instances?project=forest-taskminingsystem-992da)
* **接続名**: `forest-taskminingsystem-992da:asia-northeast1:forest-taskminingsystem`
* **データベース名**: `postgres`
* **ユーザー名**: `postgres`
* **パスワード**: `Forest0720!`

これらを組み合わせ、Cloud Runから接続するためのURL（`DATABASE_URL`）を作成しました。
> `postgresql://postgres:Forest0720!@/postgres?host=/cloudsql/forest-taskminingsystem-992da:asia-northeast1:forest-taskminingsystem`

## 3. デプロイ用ツール（Google Cloud CLI）のインストール
手元のPCから直接Google Cloudにソースコードをアップロードするため、公式ツールをインストールしました。
1. 公式サイトからインストーラーをダウンロードし、実行。（※展開に数分〜10分程度時間がかかる場合があります）
2. インストール完了後、**VSCodeを完全に再起動**してコマンドを反映。
3. VSCodeのターミナルで以下を実行し、Googleアカウントの認証とプロジェクトの設定を行う。
   ```powershell
   gcloud auth login
   gcloud config set project forest-taskminingsystem-992da
   ```

## 4. Cloud Run へのデプロイ実行（現在待機中）
認証が完了次第、ターミナルで以下のデプロイコマンドを実行します。
これにより、ソースコードがクラウド上にアップロードされ、URLが発行されます。

```powershell
gcloud run deploy task-mining-server --source . --region asia-northeast1 --allow-unauthenticated --add-cloudsql-instances="forest-taskminingsystem-992da:asia-northeast1:forest-taskminingsystem" --set-env-vars="DATABASE_URL=postgresql://postgres:Forest0720!@/postgres?host=/cloudsql/forest-taskminingsystem-992da:asia-northeast1:forest-taskminingsystem,GEMINI_API_KEY=【あなたのGemini_APIキー】"
```

※ コマンド内の `【あなたのGemini_APIキー】` は、AI Studioで取得した実際のキーに置き換えて実行します。
