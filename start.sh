#!/bin/bash

# ディレクトリを作成
mkdir -p /workspaces/A-vaboo-upload/backend/log
mkdir -p /workspaces/A-vaboo-upload/backend/remote_dir
mkdir -p /workspaces/A-vaboo-upload/backend/tmp_req

# ログファイルを作成
touch /workspaces/A-vaboo-upload/backend/log/request_api.log
touch /workspaces/A-vaboo-upload/backend/log/ts_smb_watcher.log
touch /workspaces/A-vaboo-upload/backend/log/whisper_req_ope.log
