FROM python:3.11-slim

WORKDIR /app

# 必要なパッケージをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードと静的ファイルをコピー
COPY . .

# Cloud Run はPORT環境変数(デフォルト8080)を使用します
ENV PORT=8080

# アプリケーションの起動
CMD sh -c "uvicorn app:app --host 0.0.0.0 --port ${PORT}"
