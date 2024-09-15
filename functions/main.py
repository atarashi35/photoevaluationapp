import json
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

# Flaskアプリケーションを作成
app = Flask(__name__)
app.secret_key = os.urandom(24)  # セッション管理のための秘密鍵

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)

# OpenAI APIキーを設定
openai.api_key = os.getenv("OPENAI_API_KEY")

# Firebaseの設定をSecret Managerから取得する関数
def get_firebase_credentials():
    client = secretmanager.SecretManagerServiceClient()
    secret_name = f"projects/357648496367/secrets/firebase-adminsdk/versions/latest"
    response = client.access_secret_version(name=secret_name)
    firebase_sdk_credentials = response.payload.data.decode('UTF-8')
    
    # JSON形式の文字列を辞書形式に変換
    firebase_sdk_dict = json.loads(firebase_sdk_credentials)
    return credentials.Certificate(firebase_sdk_dict)

# 認証情報の取得とFirebaseアプリの初期化
cred = get_firebase_credentials()
initialize_app(cred, {'storageBucket': 'photoevaluationapp-41036.appspot.com'})
db = firestore.client()

def upload_file_to_firebase(file):
    """Firebaseにファイルをアップロードし、評価可能なURLを取得"""
    bucket = storage.bucket()
    blob = bucket.blob(secure_filename(file.filename))
    
    # メモリ上のファイルデータをアップロード
    blob.upload_from_file(file.stream, content_type=file.content_type)
    
    # サイン付きURLを生成して返す
    return blob.generate_signed_url(expiration=timedelta(hours=1))

def extract_score(evaluation_text, category):
    """
    評価テキストから指定されたカテゴリのスコアを抽出します。
    """
    try:
        match = re.search(rf"{re.escape(category)}\s*:\s*(\d+)\s*(?:/10|点)?", evaluation_text)
        if match:
            return int(match.group(1))
        else:
            logging.warning(f"スコアが見つかりませんでした: {category}")
            return "スコアなし"
    except (IndexError, ValueError) as e:
        logging.error(f"スコア抽出エラー: {e}")
        return "スコアなし"

def extract_comment(evaluation_text, category, next_category=None):
    """
    指定されたカテゴリのコメントを抽出し、スコア部分や余計な文字を削除します。
    """
    try:
        if next_category:
            full_comment = evaluation_text.split(f"{category}:")[1].split(f"{next_category}:")[0].strip()
        else:
            full_comment = evaluation_text.split(f"{category}:")[1].strip()

        # スコア部分や余計な記号を削除
        comment = re.sub(r'\d+\s*/\s*\d+\s*点?', '', full_comment).strip()
        comment = re.sub(r'\*+', '', comment).strip()
        comment = re.sub(r'^0\s*点', '', comment).strip()
        comment = re.sub(r'###', '', comment).strip()
        comment = re.sub(r'\d+\.\s*$', '', comment).strip()

        return comment

    except (IndexError, ValueError) as e:
        logging.error(f"コメント抽出エラー: {e}")
        return "コメントの抽出中にエラーが発生しました。"

def parse_evaluation(response_text):
    """評価結果をスコアとコメントに分け、理想の形式で返します"""
    categories = [
        "構図", "照明", "被写体の明確さ", "色彩の使い方",
        "焦点とシャープネス", "背景の処理", "感情やストーリーテリング",
        "技術的な正確さ", "独創性", "編集の質", "総合評価"
    ]
    
    evaluation_dict = {}
    
    for i in range(len(categories) - 1):
        score = extract_score(response_text, categories[i])
        comment = extract_comment(response_text, categories[i], categories[i + 1])
        evaluation_dict[categories[i]] = {
            "score": score,
            "comment": comment
        }
    
    score = extract_score(response_text, "総合評価")
    comment = extract_comment(response_text, "総合評価")
    
    if score == "スコアなし":
        logging.warning("総合評価のスコアが抽出されませんでした。")
        score = ""  # スコアが無い場合は空欄にする
    
    evaluation_dict["総合評価"] = {
        "score": score,
        "comment": comment
    }
    
    return evaluation_dict

def save_evaluation_to_db(evaluation, user_id):
    """評価結果をFirestoreに保存"""
    try:
        doc_ref = db.collection('evaluations').document()
        doc_ref.set({
            "user_id": user_id,
            "evaluation_text": evaluation,
            "upload_date": firestore.SERVER_TIMESTAMP
        })
        logging.info("Firestoreに評価結果を保存しました")
    except Exception as e:
        logging.error(f"Firestore保存エラー: {e}")
        flash("評価結果の保存に失敗しました。")

@app.route('/')
def index():
    return redirect(url_for('upload_file'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            # ファイルをローカルに保存せず、直接Firebaseにアップロード
            image_url = upload_file_to_firebase(file)

            # Firebase Storageにアップロード後、評価ページへリダイレクト
            return redirect(url_for('evaluate_photo', image_url=image_url))
    return render_template('index.html')

@app.route('/evaluate_photo')
def evaluate_photo():
    image_url = request.args.get('image_url')
    if not image_url:
        flash("Image URLが存在しません。")
        return redirect(url_for('upload_file'))

    try:
        # OpenAIのスレッドを作成し、評価結果を取得
        thread = openai.beta.threads.create()
        openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=[{"type": "image_url", "image_url": {"url": image_url}}]
        )

        response_text = ""
        class EventHandler(openai.AssistantEventHandler):
            def on_text_created(self, text):
                nonlocal response_text
                response_text += str(text)

            def on_text_delta(self, delta, snapshot):
                nonlocal response_text
                response_text += str(delta.value)

        with openai.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id='asst_BCZLRYCY163E5KjO4ASDbmQo',
            event_handler=EventHandler(),
        ) as stream:
            stream.until_done()

        evaluation_dict = parse_evaluation(response_text)
        save_evaluation_to_db(evaluation_dict, user_id="example_user")

        return render_template('result.html', evaluation=evaluation_dict)

    except Exception as e:
        logging.error(f"評価エラー: {e}")
        flash("画像の評価に失敗しました。")
        return redirect(url_for('upload_file'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("ログアウトしました。")
    return redirect(url_for('upload_file'))

def main(request):
    return app(request)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))  # Cloud Runは環境変数PORTを使用します
    app.run(host='0.0.0.0', port=port)