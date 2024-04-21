import psycopg2
import os
import time
import logging
from datetime import datetime, timedelta
import shutil

# Setup logging
logging.basicConfig(
    filename="/workspaces/A-vaboo-upload/backend/log/ts_smb_watcher.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

db_params = {
    "dbname": os.environ["POSTGRES_DB"],
    "user": os.environ["POSTGRES_USER"],
    "password": os.environ["POSTGRES_PASSWORD"],
    "host": os.environ["POSTGRES_HOST"],
    "port": os.environ["POSTGRES_PORT"],
}


max_tries = 60  # 最大試行回数(60回 = 5分)
retry_interval = 5  # 再試行間隔(秒)

while True:
    try:
        for i in range(max_tries):
            try:
                conn = psycopg2.connect(**db_params)
                # 接続に成功した場合の処理
                break
            except psycopg2.OperationalError as e:
                print(f"接続試行 {i+1}/{max_tries}: {e}")
                time.sleep(retry_interval)
        else:
            # 最大試行回数を超えた場合の処理
            print("データベースへの接続に失敗しました。")
            continue

        cur = conn.cursor()

        # Fetch records with status "processing"
        cur.execute("SELECT * FROM request_operation_list WHERE status='processing'")
        records = cur.fetchall()
        print(records)

        for record in records:
            # watch_date = record[5]
            file_code = record[2]
            print(f"file_code: {file_code}")

            remote_dir = "/workspaces/A-vaboo-upload/backend/remote_dir/"
            remote_file_path = os.path.join(remote_dir, file_code)
            local_dir = "/workspaces/A-vaboo-upload/backend/tmp_req/"
            local_file_path = os.path.join(local_dir, file_code)
            print(
                f"remote_file_path: {remote_file_path}, local_file_path: {local_file_path}"
            )
            logging.info(
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - Processing file {file_code}."
            )
            logging.info(
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - Remote file path: {remote_file_path}."
            )
            logging.info(
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - Local file path: {local_file_path}."
            )
            try:
                files = os.listdir(remote_dir)
                file_paths = []
                for file in files:
                    if os.path.isfile(os.path.join(remote_dir, file)):
                        file_path = os.path.join(remote_dir, file)
                        file_paths.append(file_path)
                files = sorted(file_paths, key=lambda f: os.path.getmtime(f))
                print(f"files: {files}")
                logging.info(
                    f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - Files in remote directory: {files}."
                )

                # Get initial sizes for all files
                initial_sizes = {}
                for file in files:
                    initial_sizes[os.path.basename(file)] = os.path.getsize(file)

                # Wait for 10 seconds
                time.sleep(10)

                # Check for size changes
                all_files_same_size = True
                for file in files:
                    new_size = os.path.getsize(file)

                    if initial_sizes[os.path.basename(file)] != new_size:
                        all_files_same_size = False
                        cur.execute(
                            "UPDATE request_operation_list SET status='growing', translated_time=%s WHERE id=%s",
                            (datetime.now(), record[0]),
                        )
                        conn.commit()
                        break

                if all_files_same_size:
                    # Copy files and update database
                    copied_files = []
                    shutil.copyfile(remote_file_path, local_file_path)
                    copied_files.append(local_file_path)

                    # Update database
                    cur.execute(
                        "UPDATE request_operation_list SET status='translate', file_path=%s WHERE id=%s",
                        (copied_files, record[0]),
                    )
                    logging.info(
                        f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - Copied files: {copied_files}."
                    )

                    conn.commit()
                    logging.info(
                        f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - New file {file_code} added to PostgreSQL."
                    )

            except Exception as e:
                logging.error(f"An error occurred: {e}")

        # Check for 'growing' records and update them if needed
        cur.execute("SELECT * FROM request_operation_list WHERE status='growing'")
        growing_records = cur.fetchall()

        for record in growing_records:
            translated_time = record[6]
            if translated_time and (datetime.now() - translated_time) > timedelta(
                minutes=1
            ):
                cur.execute(
                    "UPDATE request_operation_list SET status='processing', translated_time=NULL WHERE id=%s",
                    (record[0],),
                )
                conn.commit()

        cur.close()
        conn.close()

    except IndexError as ie:
        cur.close()
        conn.close()
        if file_code:
            logging.error(
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - Index error at file {file_code}: {ie}"
            )
        else:
            logging.error(
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - Index error at file : {ie}"
            )

    except Exception as e:
        cur.close()
        conn.close()
        if file_code:
            logging.error(
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - Failed to process file : {e}"
            )
        else:
            logging.error(
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - Failed to process file {file_code}: {e}"
            )

    time.sleep(15)
