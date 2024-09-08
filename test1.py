import openai
import os
from typing_extensions import override
from openai import AssistantEventHandler
import firebase_admin
from firebase_admin import credentials, storage
from datetime import timedelta
from dotenv import load_dotenv

# 環境変数をロード
load_dotenv()

# OpenAI APIキーを設定
openai.api_key = os.getenv("OPENAI_API_KEY")

# Firebaseの設定
firebase_sdk_path = os.getenv("FIREBASE_ADMIN_SDK_PATH")
cred = credentials.Certificate(firebase_sdk_path)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'photoevaluationapp-41036.appspot.com'
})

def upload_file_to_firebase(file_path):
    """Firebaseにファイルをアップロードし、評価可能なURLを取得"""
    bucket = storage.bucket()
    blob = bucket.blob(os.path.basename(file_path))
    blob.upload_from_filename(file_path)
    # ダウンロードURLを生成（1時間有効）
    download_url = blob.generate_signed_url(expiration=timedelta(hours=1))
    return download_url

# 画像ファイルを指定してFirebaseにアップロード
file_path = "/Users/atarashi/downloads/your_image.jpg"  # ローカルの画像ファイルパスを指定
image_url = upload_file_to_firebase(file_path)
print(f"Firebase Download URL: {image_url}")

# スレッドを作成
thread = openai.beta.threads.create()
print(f"Thread created with ID: {thread.id}")

# メッセージをスレッドに追加し、Firebase Download URLを使用
message = openai.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content=[
        {"type": "image_url", "image_url": {"url": image_url}}
    ]
)
print(f"Message created with ID: {message.id}")

# スレッドを実行して応答を取得
class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)

# スレッドを実行し、応答をストリームとして取得
print("Starting stream...")
with openai.beta.threads.runs.stream(
    thread_id=thread.id,
    assistant_id='asst_BCZLRYCY163E5KjO4ASDbmQo',
    event_handler=EventHandler(),
) as stream:
    stream.until_done()
print("Stream completed")