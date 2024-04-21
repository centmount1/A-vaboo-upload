<template>
  <div id="app">
    <header :class="['header', isCentered ? 'centered' : '']">
      <div class="header-content">
        <h1 style="margin-right: 20px">A-VAboo</h1>
        <span style="margin-top: 20px">by</span>
        <img src="logo.png" alt="NewsTechnology" class="header-image" />
      </div>
      <div class="input-group">
        <div class="file-upload-wrapper">
          <input
            type="file"
            id="file-upload"
            @change="handleFileUpload"
            accept="video/*"
            style="display: none"
          />
          <label for="file-upload" class="file-upload-button">
            動画を選択
          </label>
        </div>
        <input
          v-model="file_code"
          type="text"
          id="materialId"
          placeholder="選択したファイルが表示されます"
          class="input-materialId"
          readonly
        />
        <label for="email" class="label">メールアドレス</label>
        <input
          v-model="email"
          type="email"
          id="userEmail"
          placeholder="メールアドレスを入力"
          class="input-materialId"
          @input="updateEmail($event)"
          required
        />
        <span v-if="emailError" class="error-message">{{ emailError }}</span>
        <div style="display: none">
          <label for="date">登録日：</label>
          <input
            v-model="watch_date"
            type="date"
            id="date"
            class="input-date"
          />
        </div>
        <div>
          <button @click="fetchAndMove" :disabled="isFetching">確認</button>
        </div>
      </div>
    </header>

    <div v-if="isCentered && minutesDataFetched" class="minutes-data-section">
      <h2 v-if="minutesData.length > 0">終了時間の目安</h2>
      <h2 v-else>待ち時間：0分</h2>
      <ul class="minutes-list">
        <li
          v-for="(item, index) in minutesData"
          :key="index"
          class="minutes-item"
        >
          <span class="item-number">{{ item.result_number }}</span>
          <!-- <span class="file-code">{{ item.file_code }}</span> -->
          <span class="result-time">{{ item.result }}</span>
        </li>
      </ul>
    </div>

    <div v-if="isFetching" class="loading-indicator">ロード中...</div>

    <div v-if="result === 'done' && isCentered == false">
      <video
        ref="videoPlayer"
        :src="videoSrc"
        preload="auto"
        controls
        oncontextmenu="return false;"
        controlsList="nodownload"
        width="320"
        height="240"
        style="position: fixed; top: -16px; right: 10px"
      >
        お使いのブラウザは映像をサポートしていません。
      </video>
      <div class="transcriptions">
        <button @click="copyAllText">全てコピー</button>
        <div v-for="dataItem in data" :key="dataItem.session_id">
          <button
            class="time-button"
            @click="
              $nextTick(() =>
                jumpToTime(
                  dataItem.start_time,
                  dataItem.multi_id,
                  dataItem.initial_time,
                  dataItem.video_duration
                )
              )
            "
            :aria-label="'Jump to ' + dataItem.start_time"
          >
            【{{ dataItem.start_time }}】
          </button>
          <p v-html="dataItem.text.split('\n').join('<br>')"></p>
        </div>
      </div>
    </div>

    <div v-if="showModal" class="modal">
      <div class="modal-content">
        <p v-html="modalMessage"></p>
        <input
          v-if="showEmailInput"
          v-model="email"
          type="email"
          name="userEmail"
          id="userEmail"
          autocomplete="on"
          class="input-email"
        />
        <div style="display: none">
          <button
            v-if="showEmailInput"
            @click="submitEmail"
            class="email-submit"
          >
            送信
          </button>
          <button @click="closeModal" class="close-button">閉じる</button>
        </div>
      </div>
    </div>

    <div v-if="showShortModal" class="modal">
      <div class="modal-content">
        <h2 class="short-modal">{{ shortModalMessage }}</h2>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
// axios.defaults.baseURL = "http://app:5001";

export default {
  data() {
    return {
      uploadedFile: null, // アップロードされたファイルを保持するためのデータプロパティ
      file_code: "",
      watch_date: new Date().toISOString().substring(0, 10), // 今日の日付をYYYY-MM-DD形式で設定
      email: "",
      emailError: "", // メールアドレスのバリデーションエラーを格納
      result: "",
      data: [],
      file_path: [], // 映像ファイルのパスを保持するための配列
      buffering: false,
      isCentered: true,
      showModal: false,
      modalMessage: "",
      showEmailInput: false,
      showShortModal: false, // 短時間モーダルの表示状態を制御
      shortModalMessage: "", // 短時間モーダルのメッセージ
      videoSrc: "", // 追加: MP4ファイルのURLを保持するためのデータプロパティ
      isFetching: false, // 追加: API呼び出し中かどうかを追跡するためのフラグ
      minutesData: [], // APIから取得したデータを格納
      minutesDataFetched: false, // APIからデータを取得したかどうかを示すフラグ
    };
  },
  mounted() {
    const urlParams = new URLSearchParams(window.location.search);
    const fileCode = urlParams.get("file_code");
    // watch_dateをemailに変更
    const email = urlParams.get("email");
    if (fileCode && email) {
      this.file_code = fileCode;
      this.email = email; // watch_dateの代わりにemailを設定
      this.fetchAndMove();
    } else {
      this.getMinutesData();
    }

    this.pollingInterval = setInterval(() => {
      this.getMinutesData();
    }, 10000); // 10秒ごとに更新
  },
  watch: {
    showModal(newVal) {
      if (newVal && this.email) {
        this.submitEmail();
      }
    },
    file_path: {
      immediate: true,
      handler(newVal) {
        if (newVal && newVal[0]) {
          console.log(newVal[0]);
          // ファイルをvideoSrcにセットします。
          this.videoSrc = newVal[0].replace(
            "/workspaces/A-vaboo-upload/backend/tmp_req",
            "http://localhost:6001"
          );
          console.log(this.videoSrc);
        }
      },
    },
    result(newVal) {
      if (newVal === "growing" || newVal === "translating") {
        this.openModal(
          '<h2 style="color: #fc9d32;">文字起こし中<br>少々お待ちください</h2>終わり次第、メールを送信します',
          true
        );
      } else if (newVal === "added") {
        this.openModal(
          '<h2 style="color: #008fdf;">文字起こしを開始しました<br>少々お待ちください</h2>終わり次第、メールを送信します',
          true
        );
      } else if (newVal === "done") {
        this.isCentered = false;
      }
    },
    videoSrc(newSrc) {
      if (newSrc) {
        this.$nextTick(() => {
          const video = this.$refs.videoPlayer;
          console.log("videoPlayer ref:", video);
          if (video) {
            video.addEventListener("loadedmetadata", () => {
              console.log("loadedmetadata event");
            });

            video.addEventListener("loadeddata", () => {
              console.log("loadeddata event");
            });

            video.addEventListener("canplay", () => {
              console.log("canplay event");
            });

            video.addEventListener("canplaythrough", () => {
              console.log("canplaythrough event");
            });
          }
        });
      }
    },
  },
  methods: {
    async handleFileUpload(event) {
      const files = event.target.files;
      if (files.length > 0) {
        this.uploadedFile = files[0];
        const fileCode = this.uploadedFile.name; // 一時変数に保持
        console.log("ファイルが選択されました:", fileCode);

        // ファイルアップロードの処理
        const formData = new FormData();
        formData.append("file", this.uploadedFile);
        try {
          const response = await axios.post("api/upload", formData, {
            headers: {
              "Content-Type": "multipart/form-data",
            },
          });
          console.log("サーバーへのアップロード成功:", response.data);

          // アップロード成功後にfile_codeを更新
          this.file_code = fileCode;
        } catch (error) {
          console.error("ファイルアップロード失敗:", error);
        }
      }
    },
    updateEmail(event) {
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      this.email = event.target.value;
      if (this.email && !emailPattern.test(this.email)) {
        this.emailError = "無効なメールアドレス形式です。";
      } else {
        this.emailError = ""; // エラーがなければエラーメッセージをクリア
      }
    },

    jumpToTime(timeString, multi_id, initial_time, video_duration) {
      const video = this.$refs.videoPlayer;

      const timeParts = timeString.split(":").map(Number);
      const seconds = timeParts[0] * 3600 + timeParts[1] * 60 + timeParts[2];

      const initialTimeParts = initial_time.split(":").map(Number);
      const initialSeconds =
        initialTimeParts[0] * 3600 +
        initialTimeParts[1] * 60 +
        initialTimeParts[2];

      let offsetTime;
      if (multi_id === 0) {
        offsetTime = seconds - initialSeconds;
      } else if (multi_id >= 1) {
        offsetTime = seconds - initialSeconds + video_duration;
      }

      const setVideoTime = () => {
        if (video.readyState >= 2 && video.seekable.length > 0) {
          const startTime = video.seekable.start(0);
          const endTime = video.seekable.end(0);
          if (offsetTime >= startTime && offsetTime <= endTime) {
            video.currentTime = offsetTime;
            console.log("Video time set to", video.currentTime);
            if (video.paused) {
              video.play();
            }
          } else {
            console.log("Video is not seekable to the specified time.");
          }
        } else {
          console.log("Video is not ready or not seekable yet.");
          setTimeout(setVideoTime, 100); // 再試行
        }
      };
      setVideoTime();
    },
    async checkFileExists() {
      const url = "/api/check_file";
      const payload = {
        file_code: this.file_code,
        email: this.email,
      };
      try {
        const response = await axios.post(url, payload);
        if (response.data.exists) {
          await this.fetchData();
        } else {
          this.openModal(
            '<h2 style="color: #e63c60;">ファイル名とメールアドレスの組み合わせが存在しません<br>再度入力してください</h2>'
          );
        }
      } catch (error) {
        console.error("API call failed", error);
        this.openModal(
          '<h2 style="color: #e63c60;">システムが混み合っています<br>時間を空けて再度お試しください</h2>'
        );
      }
    },
    async fetchData() {
      const url = "/api/post_data";
      const payload = {
        file_code: this.file_code,
        watch_date: this.watch_date.replace(/-/g, ""),
      };
      try {
        const response = await axios.post(url, payload);
        this.result = "temp-value";
        this.$nextTick(() => {
          this.result = response.data.result;
        });
        this.data = response.data.data || [];
        this.file_path = response.data.file_path || []; // 映像ファイルのパスをセット
        console.log(this.result);
        console.log(this.data);
        console.log(this.file_path);
      } catch (error) {
        console.error("API call failed", error);
      }
    },

    async fetchAndMove() {
      if (this.isFetching) return; // 既にフェッチ中の場合は何もしない

      // メールアドレスの入力チェック
      if (!this.email) {
        this.emailError = "メールアドレスを入力してください。";
        return;
      }
      // メールアドレスの形式チェック
      const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailPattern.test(this.email)) {
        this.emailError = "無効なメールアドレス形式です。";
        return;
      }
      this.isFetching = true; // フェッチ開始前にフラグを設定
      this.isCentered = true; // フェッチ開始時に中央揃えにする

      try {
        await this.checkFileExists();
      } catch (error) {
        console.error("API call failed", error);
      } finally {
        this.isFetching = false; // 処理が完了したらフラグをリセット
      }
    },

    copyAllText() {
      const textToCopy = this.data
        .map((dataItem) => `【${dataItem.start_time}】 ${dataItem.text}`)
        .join("\n");

      // 一時的なテキストエリアを生成
      const textArea = document.createElement("textarea");
      textArea.value = textToCopy;
      document.body.appendChild(textArea);

      // テキストエリアを選択
      textArea.select();

      // テキストをクリップボードにコピー
      document.execCommand("copy");

      // 一時的なテキストエリアを削除
      document.body.removeChild(textArea);
      this.showShortModalMessage("コピーしました");
    },
    showShortModalMessage(message) {
      this.shortModalMessage = message;
      this.showShortModal = true;
      setTimeout(() => {
        this.showShortModal = false;
        this.shortModalMessage = "";
      }, 1500); // 2秒後にモーダルを非表示にする
    },
    async submitEmail() {
      console.log("Email:", this.email);
      if (!this.email) {
        alert("メールアドレスを入力してください");
        return;
      }
      const url = "/api/update_email";
      const payload = {
        email: this.email,
        file_code: this.file_code,
        watch_date: this.watch_date.replace(/-/g, ""),
      };
      try {
        const response = await axios.post(url, payload);
        console.log("Email updated successfully", response.data);
        this.modalMessage =
          '<h3 style="color: #008fdf;">メールアドレスを登録しました</h3>文字起こしが終了次第メールでお知らせします';

        // 送信後にモーダルを自動で閉じるなどの処理をここに追加
        setTimeout(() => {
          this.showModal = false;
        }, 2000); // 2秒後にモーダルを閉じる
      } catch (error) {
        console.error("Failed to update email", error);
      }
    },
    getMinutesData() {
      const url = "/api/get_minutes"; // Updated URL
      axios
        .get(url)
        .then((response) => {
          this.minutesData = response.data;
          this.minutesDataFetched = true; // データ取得後にフラグを設定
        })
        .catch((error) => {
          console.error("There was an error fetching the minutes data:", error);
        });
    },
    openModal(message, showEmail = false) {
      this.modalMessage = message;
      this.showModal = true;
      this.showEmailInput = showEmail;
    },
    closeModal() {
      this.modalMessage = "";
      this.showModal = false;
      this.showEmailInput = false;
      this.isCentered = true;
      this.getMinutesData();
    },
  },
};
</script>

<style scoped>
#app {
  text-align: center;
  padding: 0;
  margin: 20px;
  font-family: Arial, sans-serif;
  color: #333;
  background-color: #eef2ff;
  position: relative;
  min-height: 95vh; /* Ensure the background color covers the whole viewport */
}

.header {
  background: rgba(255, 255, 255, 0.95);
  padding: 0 20px;
  border-radius: 10px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  transition: transform 0.7s cubic-bezier(0.68, -0.55, 0.27, 1.55), top 0.5s;
}

.header h1 {
  color: #5a6eb2;
  font-size: 2.5em;
  margin-bottom: 20px;
}

.header.centered {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  max-width: 500px;
}

.header:not(.centered) {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  max-width: 600px;
  font-size: 10px;
}

.header:not(.centered) button {
  font-size: 10px;
}

.header:not(.centered) .file-upload-button {
  font-size: 10px;
  padding: 1px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
  background: #dce6f8;
  padding: 15px;
  border-radius: 10px;
}

.file-upload-button {
  padding: 10px 20px;
  font-size: 26px;
  color: #fff;
  background-color: #99b0fd;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.file-upload-button:hover {
  background-color: #7a8fd8;
}

.header:not(.centered) .input-group {
  flex-direction: row;
  align-items: center;
  justify-content: space-around;
  font-size: 8px;
}

.header:not(.centered) .input-group .label {
  font-size: 8px;
}

.input-date,
.input-materialId {
  padding: 10px;
  border: none;
  border-radius: 5px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  color: #333;
  flex: 1;
  font-size: 12px;
}

.label {
  font-size: 16px;
  color: #333;
  margin-bottom: 0px;
}

.file-upload-label {
  margin-top: 10px;
  margin-bottom: 5px;
  display: block;
}

button {
  padding: 10px 20px;
  font-size: 26px;
  color: #fff;
  background-color: #99b0fd;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

button:hover {
  background-color: #7a8fd8;
}

.transcriptions {
  margin-top: 234px;
  text-align: left;
  padding: 20px;
  border-radius: 5px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

h2 {
  margin-bottom: 10px;
}

p {
  margin-bottom: 20px;
}

.info-box {
  margin-top: 220px; /* Adjust this value as needed to position .info-box below the header */
}

.info-box input.input-email {
  padding: 10px;
  border: 2px solid #5a6eb2;
  border-radius: 5px;
  margin-top: 10px;
}

.info-box button.email-submit {
  padding: 10px 20px;
  font-size: 16px;
  color: #5a6eb2;
  background-color: #eef2ff;
  border: 2px solid #5a6eb2;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
  margin-top: 10px;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  color: #fff;
  font-size: 24px;
  transition: opacity 0.3s ease;
}

.modal-content {
  background-color: #fff;
  padding: 20px;
  border-radius: 10px;
  width: 80%;
  max-width: 600px;
  text-align: center;
  transform: scale(0.7);
  transition: transform 0.3s cubic-bezier(0.68, -0.55, 0.27, 1.55);
  color: #333;
}

.modal.show {
  opacity: 1;
}
.modal.show .modal-content {
  transform: scale(1);
}
.input-email {
  margin-top: 10px;
  padding: 10px;
  border-radius: 5px;
  border: 1px solid #ccc;
  width: 90%;
  font-size: 24px;
}
.email-submit {
  margin-top: 10px;
  /* padding: 10px; */
  color: #fff;
  background-color: #99b0fd;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  transition: background-color 0.3s ease;
  margin-right: 20px;
}
.email-submit:hover {
  background-color: #7a8fd8;
}
.close-button {
  margin-top: 20px;
  display: inline-block;
}

.short-modal {
  font-size: 2.5em;
  margin-bottom: 45px;
}

.time-button {
  background: none;
  border: none;
  color: blue;
  text-decoration: underline;
  cursor: pointer;
  font-size: 1.2em; /* 必要に応じてサイズを調整 */
  padding: 0;
}

.time-button:hover,
.time-button:focus {
  color: darkblue;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-image {
  max-height: 65px; /* 画像のサイズを調整 */
  margin-top: 15px;
  padding-left: 5px;
}

.minutes-data-section {
  padding: 0 20px;
  background-color: #f0f0f0;
  border-radius: 10px;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  position: absolute; /* 絶対位置指定 */
  top: calc(50% + 200px); /* ヘッダーの高さを考慮して位置を調整 */
  left: 50%;
  transform: translateX(-50%);
  width: 100%; /* 必要に応じて幅を調整 */
  max-width: 500px; /* ヘッダーと同じ最大幅を設定 */
}

.minutes-data-section h2 {
  margin-bottom: 15px;
}

.minutes-data-section ul {
  list-style-type: none;
  background-color: #ffffff; /* 要素の背景色は適宜調整 */
  border-radius: 5px;
  padding: 0;
}

.minutes-data-section li {
  padding: 10px;
}

.minutes-item {
  display: flex;
  align-items: center;
}

.minutes-list {
  list-style-type: none;
  padding: 0;
}

.list-item {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.item-number {
  font-weight: bold;
  color: #5a6eb2;
  margin-right: 25px;
  margin-left: 25%;
  width: 30px; /* 項番の幅を固定 */
}

.file-code {
  margin-right: 10px;
  width: 80px; /* file_codeの幅を固定 */
}

.loading-indicator {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 20px;
  border-radius: 10px;
  font-size: 1.5em;
}

.error-message {
  color: #e74c3c; /* エラーメッセージの色 */
  font-size: 14px; /* テキストのサイズ */
  margin-top: 5px; /* 入力フィールドの上部からのマージン */
}
</style>
