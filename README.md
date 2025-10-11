# 🌦️ 天氣預報 LINE Bot 🤖

一個貼心的 LINE Bot，陪你一起關心每一天的天氣。

結合氣象資料與自動化推播系統，讓用戶即時掌握天氣變化，輕鬆規劃每日生活。

整合即時天氣、未來預報、颱風現況、路徑追蹤與地區影響預警，讓你隨時掌握最新氣象資訊；同時提供穿搭建議、週末天氣與節氣小知識，讓天氣不只是數據，更貼近你的日常。

支援城市切換與自動推播設定，可依需求接收每日天氣、週末預報、颱風提醒與節氣知識，打造智慧又貼心的氣象體驗，讓生活更安心、出行更從容。

---

## 🎯 功能特色

### 🌤 天氣查詢
- 查詢 **即時天氣**（顯示天氣狀況、氣溫、體感溫度、濕度、降雨量、風速、紫外線指數等資訊）
- 查詢 **天氣預報**（提供 3 天、5 天、7 天的天氣趨勢與詳細預報）
- 查詢 **週末天氣**（快速掌握假期出遊天氣狀況）

### 🌀 颱風專區
- 查詢 **颱風資訊**（包含颱風現況、最新路徑圖與地區影響預警）

### 👕 生活氣象
- 查詢 **節氣小知識**（介紹傳統習俗、養生建議與相關詩詞）
- 提供 **穿搭建議**（依氣溫與天氣條件自動生成穿搭提示）

### 🔔 智慧推播
- 自動 **排程推播**（每日 / 週末 / 颱風 / 節氣提醒，自動傳送最新天氣資訊）
- 支援 **城市與推播設定**（可切換預設城市、開啟或關閉各項推播通知）

### ⚙️ 個人化設定
- 支援 **LINE Rich Menu** 操作（直覺化選單，快速使用各項功能）

### ☁️ 系統與部署
- **部署於雲端環境**（方便開發、維護與擴展）

---

## 專案結構

- `handlers/`：接收與分派 LINE 事件，負責文字、按鈕、postback 等互動邏輯
- `menu_handlers/`：Rich Menu 點擊事件的主控中樞
- `rich_menu_manager/`：Rich Menu 建立、綁定、更新的自動化管理工具

- `weather_current/`：即時天氣查詢（溫度、濕度、天氣描述等）
- `weather_forecast/`：未來天氣預報（3天 / 5天 / 7天）與 Flex Message 呈現
- `weather_today/`：當日重點天氣摘要（溫度範圍、降雨機率、一日概況）
- `weekend_weather/`：週末天氣總覽與出遊小建議

- `typhoon/`：颱風資訊查詢（即時路徑、警戒地區、強度等）
- `solar_terms/`：節氣計算或查詢與生活化說明（配合時節的小提醒）
- `outfit_suggestion/`：根據氣溫與體感提供穿搭建議

- `settings/`：使用者個人化設定（預設城市、推播開關等）
- `push_modules/`：每日或定時自動推播模組（早安天氣、颱風速報等）
- `utils/`：共用工具集（API 請求、資料格式轉換、時間處理）

- `config.py`：全域設定檔（API 金鑰、環境變數、常數等）
- `scheduler.py`：排程任務管理與自動化執行
- `main.py` / `main_initializer.py`：主程式入口與初始化流程

- `Dockerfile` / `entrypoint.sh`：容器化部署腳本，讓 Bot 可快速上線
- `cloudbuild.yaml`：雲端自動部署設定（整合 Google Cloud Build 流程）

---

## 快速上手 / 安裝與執行  

以下是建議的部署流程（可視你的環境做修改）：

### 先決條件  

- Python 版本（建議 3.9+）  
- LINE Messaging API 金鑰  
- 天氣資料 API（如中央氣象局、氣象局開放資料、颱風資料等）  
- 若要使用 Docker / 容器部署，需有 Docker 環境  

### 安裝步驟  

1. 複製專案  
   ```bash
   git clone https://github.com/LANGCHENGWEN/my-line-weather-bot.git
   cd my-line-weather-bot

2. 建立虛擬環境並安裝依賴
   ```bash
  python -m venv venv
  source venv/bin/activate  # Linux / macOS  
  # 或 Windows: venv\Scripts\activate  
  pip install -r requirements.txt


3. 配置環境變數 / 秘密檔案

專案內有 .env.example，你可以複製為 .env，並填上以下必要項：
  ```bash
  LINE_CHANNEL_SECRET=your_line_channel_secret
  LINE_CHANNEL_ACCESS_TOKEN=your_line_access_token
  WEATHER_API_KEY=your_weather_api_key
  # .. 其餘根據 config.py 所需的變數
  ```


4. 執行專案
   ```bash
   python main.py
   ```


或透過 Docker 編排：
   ```bash
   docker build -t my-line-weather-bot .
   docker run --env-file .env -p 80:80 my-line-weather-bot
   ```


5. 在 LINE 開發者後台設定 Webhook URL，連動 bot


### 使用說明 / 範例

用戶對話範例：

使用者：/weather Taipei  
Bot：臺北市目前天氣：晴，溫度 25°C，濕度 60%，風速 3.5 m/s  


選單操作：用戶可透過永久選單（Rich Menu）點選「當日天氣」、「未來預報」、「颱風資訊」等快速查詢

排程推播：你可設定每天早上 07:00 推播當日天氣至用戶


### 部署 / 雲端整合

可在 Heroku / Google Cloud / AWS / GCP 等平台部署

使用 Docker 容器化，可簡化跨環境部署

cloudbuild.yaml 為 Google Cloud Build 的部署配置範例


### 技術棧 / 依賴

Python

LINE Messaging API / SDK

各類天氣資料 API

Docker

排程模組（如 schedule / APScheduler）

其他輔助套件（詳見 requirements.txt）

---

## 📄 授權說明
本專案僅供學術研究與作品展示用途。
LINE 與中央氣象署為其商標所有者，與本專案無商業合作。

---

## 🙋‍♂️ 作者
郎承文｜2025
如果你對專案有興趣，歡迎交流或點 star 🌟 支持！
