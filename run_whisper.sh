#!/bin/bash

# 仮想環境のアクティベーション
echo "Activating virtual environment"
source ./.venv/bin/activate

# 仮想環境のパスを表示
echo "Virtual environment path: $VIRTUAL_ENV"

# インストール済みのパッケージを表示
echo "Installed packages:"
pip list

# 8000、5001、8080ポートのプロセスをkill
echo "Killing processes on ports 8000, 5001, 8080"
sudo killall -9 node  # Nodeプロセスをkill
lsof -i :8000 | awk 'NR!=1 {print $2}' | xargs kill  # 8000ポートのプロセスをkill
lsof -i :5001 | awk 'NR!=1 {print $2}' | xargs kill  # 5001ポートのプロセスをkill
lsof -i :8080 | awk 'NR!=1 {print $2}' | xargs kill  # 8080ポートのプロセスをkill

# PostgreSQLサーバーが起動しているか確認し、whisperデータベースに接続
psql -d whisper <<EOF
SELECT 'Connected to whisper database' AS "Connection Status";
\q
EOF

# pythonファイルを順次実行（バックグラウンドで実行）
echo "Executing backend/whisper_req.py"
python ./backend/whisper_req.py &

echo "Executing backend/flask/whisper_api_request.py"
python ./backend/flask/whisper_api_request.py &

echo "Executing backend/folder_watch/watch_ts_req.py"
python ./backend/folder_watch/watch_ts_req.py &

echo "Executing backend/localserver.py"
python ./localserver.py 8000 &

# ディレクトリ移動
echo "Changing directory to frontend"
cd ./frontend

# 処理実行
echo "Running npm serve"
npm run serve &

# ブラウザを開く
echo "Opening browser"
if command -v xdg-open > /dev/null; then
  xdg-open http://localhost:8080
elif command -v open > /dev/null; then
  open http://localhost:8080
elif command -v start > /dev/null; then
  start http://localhost:8080
else
  echo "No suitable command found to open the browser"
fi