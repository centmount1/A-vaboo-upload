import psycopg2
import time
import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
import subprocess
from datetime import datetime, timedelta
from flask import Flask
from faster_whisper import WhisperModel
import gc
import torch
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import MeCab

# ログ設定
logging.basicConfig(
    filename="/workspaces/A-vaboo-upload/backend/log/whisper_req_ope.log",
    level=logging.INFO,
)

# envファイルの読み込み
load_dotenv()
OPEN_API_KEY = os.getenv("OPENAI_API_KEY")

# OpenAI APIクライアントの初期化
client = OpenAI()


# Database connection settings
db_params = {
    "dbname": os.environ["POSTGRES_DB"],
    "user": os.environ["POSTGRES_USER"],
    "password": os.environ["POSTGRES_PASSWORD"],
    "host": os.environ["POSTGRES_HOST"],
    "port": os.environ["POSTGRES_PORT"],
}


# DB接続設定
try:
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()
except Exception as e:
    logging.error(f"Database connection failed: {e}")
    exit()

# テーブルがなければ作成
try:
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS request_operation_list (
        id SERIAL PRIMARY KEY,
        status VARCHAR(10) NOT NULL,
        file_code VARCHAR(1024) NOT NULL,
        file_path VARCHAR(1024)[],
        added_time TIMESTAMP NOT NULL,
        watch_date CHAR(8) NOT NULL,
        translated_time TIMESTAMP,
        email VARCHAR(255)[]
    );
    """
    )
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS request_transcriptions (
        id SERIAL PRIMARY KEY,
        session_id INT NOT NULL,
        start_time VARCHAR(8) NOT NULL,
        end_time VARCHAR(8) NOT NULL,
        text TEXT NOT NULL,
        multi_id INT NOT NULL,
        initial_time VARCHAR(8) NOT NULL,
        video_duration VARCHAR(8)
    );
    """
    )
    conn.commit()
except Exception as e:
    logging.error(
        f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - Table creation failed: {e}"
    )
    exit()
finally:
    cur.close()
    conn.close()


def seconds_to_timecode(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"


def timecode_to_seconds(timecode):
    hours, minutes, seconds_frames = timecode.split(":")
    seconds = seconds_frames.split(";")[0]  # フレーム数を無視
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def extract_timecode():
    # 文字列を時間の形式に変換
    time_format = "%H:%M:%S.%f"
    time_obj = datetime.strptime("0:00:00.000", time_format)
    # 新しい時間を文字列に変換
    new_time_str = time_obj.strftime(time_format)
    return new_time_str[:8]


def get_video_duration(file_path):
    cmd = f'ffprobe -i {file_path} -show_entries format=duration -v quiet -of csv="p=0"'
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    print(f"video_duration {output}")
    return float(output.strip())


def insert_and_commit(record, segments, start_tc_seconds):
    logging.info(
        f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - insert_and_commit_start {record[0]} at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
    )

    local_conn = psycopg2.connect(**db_params)
    local_cur = local_conn.cursor()
    try:
        insert_data = [
            (
                record[0],
                seconds_to_timecode(segment.start + start_tc_seconds),
                seconds_to_timecode(segment.end + start_tc_seconds),
                segment.text,
            )
            for segment in segments
        ]
        local_cur.executemany(
            """
                        INSERT INTO request_transcriptions (session_id, start_time, end_time, text)
                        VALUES (%s, %s, %s, %s)
                        """,
            insert_data,
        )
        local_conn.commit()
        print(
            "DB_end: "
            + str(record[0])
            + "---"
            + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        )
    except Exception as e:
        logging.error(f"Error occurred while inserting and committing: {e}")
    finally:
        logging.info(
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - insert_and_commit_end {record[0]} at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
        )
        local_cur.close()
        local_conn.close()


def sendmail(subject, body, mail_to):
    gmail_account = "nakayamas@ex5ch.com"
    gmail_password = os.getenv("GMAIL_PASSWORD")  # 環境変数からパスワードを取得

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = gmail_account
    msg["To"] = mail_to
    msg.attach(MIMEText(body, "html"))

    try:
        s = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
        s.starttls()
        s.login(gmail_account, gmail_password)
        s.sendmail(gmail_account, mail_to, msg.as_string())
        s.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")


def translate_to_japanese(text):
    print(type(text))

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "あなたは優秀な通訳です"},
                {"role": "user", "content": f"日本語に翻訳してください:{text}"},
            ],
        )

        translated_text = response.choices[0].message.content
        return translated_text

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return ""


def is_sentence_end(text):
    tagger = MeCab.Tagger("")
    words = tagger.parse(text).split("\n")
    last_word_info = words[-3].split("\t")
    if "終止形-一般" in last_word_info or "補助記号-句点" in last_word_info:
        return True
    return False


last_execution_time = datetime.now() - timedelta(hours=2)

while True:
    try:
        app = Flask(__name__)

        current_time = datetime.now()
        time_diff = current_time - last_execution_time

        print(time_diff.total_seconds())
        if time_diff.total_seconds() > 3600:  # Check if more than 1 hour has passed
            # if "model" in locals():
            #     del model
            #     gc.collect()
            #     torch.cuda.empty_cache()

            # モデルを初期化
            # model_size = "large-v1"
            # model_size = "large-v2"
            model_size = "large-v3"
            # model_size = "medium"
            # model_size = "tiny"

            # model = WhisperModel(
            #     model_size, device="cuda", compute_type="float32"
            # )

            # CPUで実行
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            print(model)
            logging.info(
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - Model initialized"
            )

            last_execution_time = current_time  # Update the last execution time

        conn = psycopg2.connect(**db_params)
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM request_operation_list WHERE status = 'translate' ORDER BY added_time ASC;"
        )
        records = cur.fetchall()

        cur.close()
        conn.close()

        # with ThreadPoolExecutor(max_workers=2) as executor:
        #     futures = []
        for record in records:
            try:
                file_paths = record[3]  # 変更点: 順番に合わせてインデックスを修正
                print(file_paths)

                if not file_paths:
                    conn = psycopg2.connect(**db_params)
                    cur = conn.cursor()
                    cur.execute(
                        "UPDATE request_operation_list SET status = 'failed' WHERE id = %s",
                        (record[0],),
                    )
                    conn.commit()
                    cur.close()
                    conn.close()

                    if record[7]:
                        error_mail_to_list = "; ".join(
                            record[7]
                        )  # Convert list of emails to comma-separated string
                        print("mail_send")
                        error_body = (
                            """
                            <html>
                            <head> """
                            + "</head>"
                            + f"""
                            <body style="font-family: 'Yu Gothic', sans-serif; font-size: 11pt;">
                                <p>文字起こしに失敗しました。<br><br>送信した素材ID<"""
                            + record[2]
                            + """>は指定の日にち"""
                            + record[5]
                            + """に存在しませんでした。再度ご確認ください。</p>
                            </body>
                            </html>
                            """
                        )
                        sendmail(
                            "【A-Vaboo】文字起こし失敗",
                            error_body,
                            error_mail_to_list,
                        )

                    break

                # ファイルサイズが5秒間変わらないか確認
                initial_sizes = {
                    file_path: os.path.getsize(file_path) for file_path in file_paths
                }
                time.sleep(5)
                for file_path in file_paths:
                    final_size = os.path.getsize(file_path)

                    if initial_sizes[file_path] != final_size:
                        break

                else:
                    conn = psycopg2.connect(**db_params)
                    cur = conn.cursor()

                    total_video_duration = 0  # 初期値を0に設定

                    for index, file_path in enumerate(file_paths):
                        print(index, file_path)

                        video_duration = get_video_duration(file_path)
                        print(
                            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                            + "start: "
                            + str(video_duration)
                            + "---"
                            + file_path
                        )
                        logging.info(
                            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                            + "start: "
                            + str(video_duration)
                            + "---"
                            + file_path
                        )

                        # Set the status based on video duration
                        new_status = "completed"
                        # if video_duration <= 15:
                        #     new_status = 'done_short'
                        start_tc = extract_timecode()
                        start_tc_seconds = timecode_to_seconds(start_tc)
                        logging.info(
                            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                            + " - start_tc_seconds: "
                            + str(start_tc_seconds)
                        )

                        # モデルで推論
                        segments, info = model.transcribe(file_path, beam_size=5)
                        print(
                            f"Detected language {info.language} with probability {info.language_probability:.2f}"
                        )
                        logging.info(
                            f"Detected language {info.language} with probability {info.language_probability:.2f}"
                        )

                        print(
                            "DB_start: "
                            + str(record[0])
                            + "---"
                            + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        )

                        insert_data = []
                        if info.language != "ja" and info.language_probability > 0.80:

                            if info.language == "zh":
                                segments = list(segments)
                                for segment in segments:
                                    print(segment.text)
                                    translated_text = translate_to_japanese(
                                        segment.text
                                    )
                                    insert_data.append(
                                        (
                                            record[0],
                                            seconds_to_timecode(
                                                segment.start + start_tc_seconds
                                            ),
                                            seconds_to_timecode(
                                                segment.end + start_tc_seconds
                                            ),
                                            segment.text + "\n" + translated_text,
                                            index,
                                            seconds_to_timecode(start_tc_seconds),
                                            seconds_to_timecode(total_video_duration),
                                        )
                                    )

                            else:
                                segments = list(segments)
                                combined_text = ""
                                segment_start_tc_seconds = (
                                    None  # 結合したテキストの最初のsegment.start
                                )
                                for seg_num, segment in enumerate(segments):
                                    if segment_start_tc_seconds == None:
                                        segment_start_tc_seconds = segments[
                                            seg_num
                                        ].start

                                    print(segment.text)
                                    if segment.text.endswith("."):
                                        combined_text += segment.text
                                        translated_text = translate_to_japanese(
                                            combined_text
                                        )
                                        print(f"翻訳文:{translated_text}")
                                        insert_data.append(
                                            (
                                                record[0],
                                                seconds_to_timecode(
                                                    segment_start_tc_seconds
                                                    + start_tc_seconds
                                                ),
                                                seconds_to_timecode(
                                                    segment.end + start_tc_seconds
                                                ),
                                                combined_text + "\n" + translated_text,
                                                index,
                                                seconds_to_timecode(start_tc_seconds),
                                                seconds_to_timecode(
                                                    total_video_duration
                                                ),
                                            )
                                        )
                                        combined_text = ""
                                        segment_start_tc_seconds = None
                                    else:
                                        combined_text += segment.text
                        else:
                            # info.languageが"JA"であるか、info.language_probabilityが0.85以下の場合
                            if info.language == "ja":
                                segments = list(segments)
                                combined_text = ""
                                segment_start_tc_seconds = (
                                    None  # 結合したテキストの最初のsegment.start
                                )
                                for seg_num, segment in enumerate(segments):
                                    if segment_start_tc_seconds == None:
                                        segment_start_tc_seconds = segments[
                                            seg_num
                                        ].start

                                    combined_text += (
                                        segment.text + " "
                                    )  # 末尾に半角スペースを追加

                                    # 次のsegmentの開始時刻と現在のsegmentの終了時刻の差を計算
                                    time_difference = (
                                        segments[seg_num + 1].start
                                        if seg_num + 1 < len(segments)
                                        else segment.end
                                    ) - segment.end

                                    # 文末の判定または時間の差の判定
                                    if (
                                        is_sentence_end(combined_text)
                                        or time_difference >= 3
                                        or seg_num + 1 == len(segments)
                                    ):
                                        insert_data.append(
                                            (
                                                record[0],
                                                seconds_to_timecode(
                                                    segment_start_tc_seconds
                                                    + start_tc_seconds
                                                ),
                                                seconds_to_timecode(
                                                    segment.end + start_tc_seconds
                                                ),
                                                combined_text,
                                                index,
                                                seconds_to_timecode(start_tc_seconds),
                                                seconds_to_timecode(
                                                    total_video_duration
                                                ),
                                            )
                                        )
                                        combined_text = ""
                                        segment_start_tc_seconds = None
                            else:
                                insert_data = [
                                    (
                                        record[0],
                                        seconds_to_timecode(
                                            segment.start + start_tc_seconds
                                        ),
                                        seconds_to_timecode(
                                            segment.end + start_tc_seconds
                                        ),
                                        segment.text,
                                        index,
                                        seconds_to_timecode(start_tc_seconds),
                                        seconds_to_timecode(total_video_duration),
                                    )
                                    for segment in segments
                                ]

                        print(insert_data)
                        logging.info(
                            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - insert_data: {insert_data}"
                        )

                        cur.executemany(
                            """
                        INSERT INTO request_transcriptions (session_id, start_time, end_time, text, multi_id, initial_time, video_duration)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                            insert_data,
                        )
                        print(
                            "DB_end: "
                            + str(record[0])
                            + "---"
                            + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                        )

                        # Update request_operation_list
                        cur.execute(
                            """
                        UPDATE request_operation_list
                        SET status = %s, translated_time = %s
                        WHERE id = %s
                        """,
                            (
                                new_status,
                                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                record[0],
                            ),
                        )

                        conn.commit()

                        if record[7]:
                            mail_to_list = "; ".join(
                                record[7]
                            )  # Convert list of emails to comma-separated string
                            print("mail_send")
                            body = (
                                """
                                <html>
                                <head> """
                                + "</head>"
                                + f"""
                                <body style="font-family: 'Yu Gothic', sans-serif; font-size: 11pt;">
                                    <p>文字起こしが完了しました。<br><br>文字起こし結果↓<br>
                                    <a href="http://localhost:8080/?file_code="""
                                + str(record[2])
                                + "&email="
                                + str(record[7][0])
                                + """">http://localhost:8080/?file_code="""
                                + str(record[2])
                                + "&email="
                                + str(record[7][0])
                                + """</a><br><br>
                                    ご質問やご要望等あれば****までご連絡ください。</p>
                                </body>
                                </html>
                                """
                            )
                            sendmail("【A-Vaboo】文字起こし完了", body, mail_to_list)

                        logging.info(
                            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} - translated file {file_path} at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
                        )

                        total_video_duration += video_duration  # 合計に追加
                        # os.remove(file_path)

                    cur.close()
                    conn.close()

            except Exception as e:
                logging.error(
                    f"Error occurred while processing record {record[0]} at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}: {e}"
                )

    except Exception as e:
        logging.error(f"Error occurred: {e}")

    time.sleep(5)  # 5second interval
