# my-line-weather-bot  

**天氣預報 LINE Bot**  

一個可部署於雲端／本地的 LINE 聊天機器人，能回覆天氣資訊（如即時天氣、預報、颱風、節氣等）。  

---

## 功能特色 🎯

- 查詢 **即時天氣**  
- 查詢 **天氣預報**（未來數日）  
- 查詢 **颱風資訊**  
- 查詢 **節氣**  
- 自動 **排程推播**（天天／定時傳送天氣）  
- 支援 **LINE Rich Menu** 選單操作  
- 可部署於 Docker / 雲端環境  

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
