# 🌦️ 天氣預報 LINE Bot 🤖

一個貼心的 LINE Bot，陪你一起關心每一天的天氣。

結合氣象資料與自動化推播系統，讓用戶即時掌握天氣變化，輕鬆規劃每日生活。

整合即時天氣、未來預報、颱風現況、路徑追蹤與地區影響預警，讓你隨時掌握最新氣象資訊；同時提供穿搭建議、週末天氣與節氣小知識，讓天氣不只是數據，更貼近你的日常。

支援城市切換與自動推播設定，可依需求接收每日天氣、週末預報、颱風提醒與節氣知識，打造智慧又貼心的氣象體驗，讓生活更安心、出行更從容。

---

## 🎯 功能特色

- 查詢 **即時天氣**（顯示氣溫、體感溫度、濕度、風速、降雨機率等資訊）
- 查詢 **天氣預報**（提供 3 天、5 天、7 天的天氣趨勢與詳細預報）
- 查詢 **週末天氣**（快速掌握假期出遊天氣狀況）
- 查詢 **颱風資訊**（包含颱風現況、最新路徑圖與地區影響預警）
- 查詢 **節氣小知識**（介紹節氣由來、氣候變化與生活建議）
- 提供 **穿搭建議**（依氣溫與天氣條件自動生成穿搭提示）
- 自動 **排程推播**（天天／定時傳送天氣）  （每日 / 週末 / 颱風 / 節氣提醒，自動傳送最新天氣資訊）
- 支援 **城市與推播設定**（可切換預設城市、開啟或關閉各項推播通知）
- 支援 **LINE Rich Menu** 操作  （直覺化選單，快速使用各項功能）
- 可 **部署於 Docker 或雲端環境**  （方便開發、維護與擴展）

---

## 專案結構（主要目錄）  

以下是專案的大致檔案結構：



- `handlers/`：負責接收 LINE 事件、指令解析與回覆路由  
- `menu_handlers/`：Rich Menu 相關操作  
- `push_modules/`：排程推播邏輯  
- `weather_*`：各類型天氣資料查詢模組  
- `solar_terms/`：節氣資料計算或查詢  
- `typhoon/`：颱風資料查詢模組  
- `utils/`：共用輔助函式  
- `config.py`：配置（API 金鑰、路徑、常數等）  
- `Dockerfile` / `entrypoint.sh`：容器化部署腳本  
- `scheduler.py`：排程任務管理  
- `main.py` / `main_initializer.py`：程式入口、初始化流程  

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


4. 執行專案
   ```bash
   python main.py


或透過 Docker 編排：
   ```bash
   docker build -t my-line-weather-bot .
   docker run --env-file .env -p 80:80 my-line-weather-bot


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


### 授權 / 作者

作者：LANGCHENGWEN
授權：請在此填上使用的授權方式（如 MIT / Apache 2.0 / …）


### 待辦 / 改進方向

支援更多天氣資料源以提升可靠度

加入錯誤處理與異常回復機制

用戶管理：訂閱 / 取消訂閱

多語系支援

增加圖表、圖片輸出（如天氣圖、降雨機率圖）
