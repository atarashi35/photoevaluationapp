import json
import tempfile
import re
import os
import openai
import logging
from flask import Flask, request, redirect, url_for, render_template, session, flash
from firebase_admin import credentials, initialize_app, storage, firestore
from werkzeug.utils import secure_filename
from datetime import timedelta
from dotenv import load_dotenv
from google.cloud import secretmanager

# Flaskアプリケーションを作成（テンプレートフォルダを指定）
app = Flask(__name__, template_folder='templates')
app.secret_key = os.urandom(24)  # セッション管理のための秘密鍵

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)

# OpenAI APIキーを設定
openai.api_key = os.getenv("OPENAI_API_KEY")

def get_firebase_credentials():
    client = secretmanager.SecretManagerServiceClient()
    secret_name = f"projects/357648496367/secrets/firebase-adminsdk/versions/latest"
    response = client.access_secret_version(name=secret_name)
    firebase_sdk_credentials = response.payload.data.decode('UTF-8')

    # JSONを一時ファイルに保存
    temp = tempfile.NamedTemporaryFile(delete=False)
    with open(temp.name, 'w') as f:
        f.write(firebase_sdk_credentials)
    
    return credentials.Certificate(temp.name)

# 認証情報の取得とFirebaseアプリの初期化
cred = get_firebase_credentials()
initialize_app(cred, {'storageBucket': 'photoevaluationapp-41036.appspot.com'})
db = firestore.client()

def upload_file_to_firebase(file):
    """Firebaseにファイルをアップロードし、評価可能なURLを取得"""
    bucket = storage.bucket()
    blob = bucket.blob(secure_filename(file.filename))
    blob.upload_from_file(file.stream, content_type=file.content_type)
    return blob.generate_signed_url(expiration=timedelta(hours=1))

@app.route('/')
def index():
    return redirect(url_for('upload_file'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            image_url = upload_file_to_firebase(file)
            return redirect(url_for('evaluate_photo', image_url=image_url))
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("ログアウトしました。")
    return redirect(url_for('upload_file'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    app.run(host='0.0.0.0', port=port)