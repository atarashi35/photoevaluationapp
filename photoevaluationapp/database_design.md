# データベース設計

## 評価データスキーマ

各写真の評価データを以下のスキーマでFirestoreに保存します。

### ドキュメント構造
```json
{
  "user_id": "user_identifier",
  "filename": "uploaded_image.jpg",
  "upload_date": "timestamp",
  "composition": {
    "score": "8",
    "comment": "三分割構図が効果的に使用されています。"
  },
  "lighting": {
    "score": "7",
    "comment": "影のコントロールが少し不足しています。"
  },
  ...
  "summary": "全体的に非常に良い写真ですが、背景の処理に若干の改良が必要です。",
  "overall_score": "78/100"
}
