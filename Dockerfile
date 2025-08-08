# Dockerfile
# 第一階段：建置環境
# 使用一個更完整的 Python 映像檔來安裝依賴，確保所有套件都能正確編譯
FROM python:3.10 as builder

# 設定容器內的工作目錄
WORKDIR /app

# 將 requirements.txt 複製到工作目錄
# 這樣做可以利用 Docker 的快取機制，當檔案沒變動時，下次建置會更快
COPY requirements.txt .

# 安裝所有 Python 依賴套件
RUN pip install --no-cache-dir -r requirements.txt

# 第二階段：最終執行環境
# 使用一個更小的映像檔來運行你的應用程式，這可以讓容器更輕量、啟動更快
FROM python:3.10-slim

# 設定最終容器的工作目錄
WORKDIR /app

# 從建置環境中，將安裝好的依賴複製過來
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# 將你的應用程式程式碼（main.py）複製到容器中
COPY . .

# 這行環境變數是正確的，但我們改用更可靠的模組執行方式來確保它能正常運作
ENV PYTHONPATH=/app

# --- 新增的步驟：在建置時執行 Rich Menu 部署腳本 ---
# ARG 指令定義一個可以在建置時傳入的參數，我們稱之為 LINE_ACCESS_TOKEN
ARG LINE_ACCESS_TOKEN
# ENV 指令將 ARG 的值設定為環境變數，這樣 Python 腳本就能透過 os.environ 讀取
ENV LINE_CHANNEL_ACCESS_TOKEN=${LINE_ACCESS_TOKEN}

# 執行 Rich Menu 部署腳本，這會生成 rich_menu_ids.json
# 注意：這裡會呼叫 LINE API，所以建置時間會稍微延長
RUN python -m rich_menu_manager.rich_menu_deployer

# 定義容器啟動時執行的指令
# 這會使用 gunicorn 來啟動你的 Flask 應用程式
# 0.0.0.0:8080 是 Cloud Run 服務必須監聽的埠號
# main:app 代表在 main.py 檔案中找到一個名為 app 的 Flask 應用程式實例
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]