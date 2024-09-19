# ベースイメージを指定 (Python 3.10)
FROM python:3.10

# 作業ディレクトリを設定
WORKDIR /app

# 必要なファイルをコピー
COPY requirements.txt requirements.txt
COPY main.py main.py

# 依存パッケージをインストール
RUN pip install --no-cache-dir -r requirements.txt

# Flaskの環境変数を設定
ENV FLASK_APP=main.py

# ポートを指定
ENV PORT 8081

# Flaskサーバーを起動
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 main:app