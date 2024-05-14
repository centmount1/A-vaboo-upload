# A-vabooファイルアップロード版
- ファイルアップロードの動作確認用に作成
- 元の処理をほぼ書き換えず、そのまま残しています。
- フロントエンドからのAPIアクセス、DBのタイムコード処理など
最適化できていません。

## 起動方法

### リポジトリのクローン
- `git clone git@github.com:centmount1/A-vaboo-upload.git`

### 環境変数の設定
- `.env.sample`ファイルをコピーして、`.env`ファイルを作成
- メール送信用に`GMAIL_PASSWORD`の入力 
- 日本語翻訳用に`OPENAI_API_KEY`の入力

### Dockerコンテナの起動
- `cd A-vaboo-upload`でdocker-compose.ymlのディレクトリに移動
- `docker compose build --no-cache`でイメージ作成
- `docker compose up`でコンテナ起動
- app（バックエンド）、frontend, db, nginxが起動されます。
- ブラウザで`http://localhost:8080`で動作確認

## 主なファイルの構成

### ①frontend/*
フロントアプリ(vue)

### ②backend/flask/whisper_api_request.py
- API(flask)
- 映像ファイルをアップロードAPI<br>
- `PostgreSQL`(request_operation_listテーブル)登録API<br>
- 映像ファイルが存在するかチェックAPI<br>
- 結果送信先のメールアドレス追加API<br>
- 処理中のファイルの残時間取得API<br>

### ③backend/folder_watch/watch_ts_req.py
- バックエンド常時起動アプリ１<br>
- DB登録されたファイルをDL・DB更新<br>

### ④backend/whisper_req.py
- バックエンド常時起動アプリ２<br>
- `faster-whisper`により文字起こし<br>
- 文字起こし結果と各タイムコードを`request_operation_list`テーブルのIDと紐づいた、
　`request_transcriptions`テーブルに登録<br>
- 各文字起こし結果は`MeCab`で形態素解析し、文末表現まで文字起こし結果をつなげる<br>
- `ja`以外は`ChatGPTのAPI`で翻訳結果を付与<br>

