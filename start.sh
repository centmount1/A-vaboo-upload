#!/bin/bash

# ディレクトリを作成
mkdir -p ./backend/log
mkdir -p ./backend/remote_dir
mkdir -p ./backend/tmp_req

# ログファイルを作成
touch ./backend/log/request_api.log
touch ./backend/log/ts_smb_watcher.log
touch ./backend/log/whisper_req_ope.log
