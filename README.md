# ディレクトリ＆ファイル作成が必要
- ログ保存ファイル<br> 
./backend/log/request_api.log<br>
./backend/log/ts_smb_watcher.log<br>
./backend/log/whisper_req_ope.log<br>
- 動画ファイルアップロード先ディレクトリ<br> 
./backend/remote_dir<br>
- 動画ファイル処理用の一時ディレクトリ<br> 
./backend/tmp_req<br>

# 環境変数の設定
.env.sampleファイルのAPI等を書き換え

# ①frontend/*
フロントアプリ(vue)

# ②backend/flask/whisper_api_request.py
API(flask)
<br>
ー映像ファイルをアップロードAPI<br>
ーPostgreSQL(request_operation_listテーブル)登録API<br>
ー映像ファイルが存在するかチェックAPI<br>
ー結果送信先のメールアドレス追加API<br>
ー処理中のファイルの残時間取得API<br>

# ③backend/folder_watch/watch_ts_req.py
バックエンド常時起動アプリ１<br>
ーDB登録されたファイルをDL・DB更新<br>

# ④backend/whisper_req.py
バックエンド常時起動アプリ２<br>
ーfaster-whisperにより文字起こし<br>
ー文字起こし結果と各タイムコードをrequest_operation_listテーブルのIDと紐づいた、
　request_transcriptionsテーブルに登録<br>
ー各文字起こし結果はMeCabで形態素解析し、文末表現まで文字起こし結果をつなげる<br>
ーja以外はChatGPTのAPIで翻訳結果を付与<br>

# ◯その他メモ<br>
ーモデルは↓から自動更新でDLしようとする。model_pathにこのモデルのパスを指定するとローカルで完結。<br>
 https://huggingface.co/guillaumekln<br>

ーlarge-v3使うには：↑はv2までしかない。パスを↓に変えるもしくはローカルにモデルDLでv3使用可能<br>
https://github.com/SYSTRAN/faster-whisper<br>

# ファイル版参考サイト<br>
https://github.com/PINTO0309/faster-whisper-env<br>
https://github.com/guillaumekln/faster-whisper<br>

# リアルタイム版参考サイト<br>
https://qiita.com/reriiasu/items/dccffb249a41959c839e
