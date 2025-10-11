# 🌦️ 天氣預報 LINE Bot 🤖

一個貼心的 LINE Bot，陪你一起關心每一天的天氣。

結合氣象資料與自動化推播系統，讓用戶即時掌握天氣變化，輕鬆規劃每日生活。

整合即時天氣、未來預報、颱風現況、路徑追蹤與地區影響預警，讓你隨時掌握最新氣象資訊；同時提供穿搭建議、週末天氣與節氣小知識，讓天氣不只是數據，更貼近你的日常。

支援城市切換與自動推播設定，可依需求接收每日天氣、週末預報、颱風提醒與節氣知識，打造智慧又貼心的氣象體驗，讓生活更安心、出行更從容。

---

## 🎯 功能特色

### 🌤 天氣查詢
- 查詢 **即時天氣**（溫度、體感、濕度、降雨量、風速、紫外線指數等資訊）
- 查詢 **天氣預報**（提供 3 天、5 天、7 天的天氣趨勢與詳細預報）
- 查詢 **今日天氣**（體感、最低 ~ 最高溫、濕度、降雨機率、風速、舒適度、紫外線指數等資訊）
- 查詢 **週末天氣**（快速掌握假期出遊天氣狀況）

### 🌀 颱風專區
- 查看 **颱風現況**（即時現況與未來 72 小時趨勢預報）
- 顯示 **颱風路徑圖**（連結外部網站 (NCDR) 國家災害防救科技中心）
- 提供 **地區影響預警**（警戒風雨狀況與注意事項）

### 👕 生活氣象
- 提供 **穿搭建議**（依氣溫、體感與天氣條件生成穿搭提示）
- 查詢 **節氣小知識**（介紹傳統習俗、養生建議與相關詩詞）

### 🔔 智慧推播
- 自動 **排程推播**（每日天氣 / 週末預報 / 颱風速報 / 節氣提醒，自動傳送最新天氣資訊）
- 支援 **推播設定**（可選擇開啟或關閉各項推播通知）

### ⚙️ 個人化設定
- 自由 **切換預設城市**（讓用戶自由選擇要查詢與推播的預設城市）
- 支援 **Rich Menu** 操作（直覺化選單，快速使用各項功能）

### ☁️ 系統與部署
- **部署於雲端環境**（方便開發、維護與擴展）
- 整合 **自動排程與 Google Cloud Build**（穩定更新與持續運行）

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


### 部署 / 雲端整合

可在 Heroku / Google Cloud / AWS / GCP 等平台部署

使用 Docker 容器化，可簡化跨環境部署

cloudbuild.yaml 為 Google Cloud Build 的部署配置範例


### 技術棧 / 依賴

Docker

排程模組（如 schedule / APScheduler）

---

## 🔧 技術架構

- 💻 後端框架 | Python + Flask
- ☁️ 雲端部署 | Google Cloud Build
- 💬 LINE SDK | LINE Messaging API (v3)
- 🎨 訊息格式 | Flex Message（支援滑動選單與卡片）
- 📡 氣象資料來源 | 交通部中央氣象署 Open Data 平台
  - 即時天氣觀測（O-A0003-001）  
  - 今明 36 小時預報（F-C0032-001）  
  - 未來 3 日 / 7 日預報（F-D0047-089 / F-D0047-091）  
  - 紫外線指數（O-A0005-001）  
  - 熱帶氣旋與警特報（W-C0034-005 / W-C0033-002）  
- 🌐 外部參考來源 | 國家災害防救科技中心（NCDR）颱風路徑圖

---

## 🔑 使用技術細節

- **模組化架構設計**：依功能分為天氣查詢、颱風資訊、節氣、推播、設定等模組，方便維護與擴充
- **氣象資料整合**：解析中央氣象署自訂格式的資料，並聚合多時段資料，確保預報完整一致
- **智慧推播系統**：利用排程自動推播每日天氣、週末天氣、颱風速報與節氣提醒
- **Flex Message 視覺化**：以圖文卡片呈現未來天氣、颱風動態與建議內容，提升使用者體驗
- **使用者狀態管理**：記錄用戶查詢流程與設定（預設城市、推播開關），提供個人化互動
- **Rich Menu 整合**：以圖像化選單操作查詢與設定功能，強化互動性與操作便利性
- **自動化部署**：支援 Google Cloud Build 與 Docker 容器化，實現穩定持續整合與更新

---

## ⚙️ 開發與部署

### 安裝環境

```bash
# 建立虛擬環境
python -m venv my_env

#（Windows）啟動虛擬環境 (Linux 或 macOS 用 source venv/bin/activate)
my_env\Scripts\activate

# 安裝所有依賴套件
pip install -r requirements.txt
```

### 在專案根目錄建立環境變數 `.env` 檔案

```env
LINE_CHANNEL_SECRET=YOUR_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN=YOUR_CHANNEL_ACCESS_TOKEN
CWA_API_KEY=YOUR_CWA_API_KEY
YOUR_LINE_USER_ID=YOUR_LINE_USER_ID
LOG_LEVEL=DEBUG                  # 控制 log 顯示的詳細程度
LOG_FILE=main.log                # 指定 log 儲存的檔名
ENABLE_FILE_LOG=True             # 是否啟用檔案 log 輸出
IS_DEBUG_MODE=True               # 是否啟用 debug 模式，部署到雲端，通常預設是 False
ENABLE_DAILY_NOTIFICATIONS=False # 是否啟用每日推播
FIREBASE_ADMIN_SDK=YOUR_FIREBASE_ADMIN_SDK # 私密金鑰，授權完整的管理權限，於 Firebase 專案後台取得
```

### 本地啟動

```bash
python main.py
```

---

## 📄 授權說明
本專案僅供學術研究與作品展示用途。
LINE 與中央氣象署為其商標所有者，與本專案無商業合作。

---

## 🙋‍♂️ 作者
郎承文｜2025
如果你對專案有興趣，歡迎交流或點 star 🌟 支持！
