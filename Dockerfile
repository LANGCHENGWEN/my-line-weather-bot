# Dockerfile
# --- 第一階段：建置環境 (builder) ---
# 用一個功能更完整的 Python 映像檔安裝所有依賴套件
# 確保在編譯時不會缺少任何必要的系統函式庫，同時可以利用 Docker 快取
FROM python:3.10 as builder

# 設定容器內的工作目錄為 /app
# 之後的所有指令 (COPY, RUN) 都會在這個目錄下執行
WORKDIR /app

# 將本地的 requirements.txt 檔案複製到容器的 /app 目錄
# 複製這個檔案是為了利用 Docker 的快取
# 如果 requirements.txt 沒有變動，接下來的 pip install 指令在下次建置時會直接使用快取結果，大幅加快建置速度
COPY requirements.txt .

# 安裝所有 Python 依賴套件
# --no-cache-dir 參數可以防止 pip 儲存快取檔案，進一步減少最終映像檔的體積
RUN pip install --no-cache-dir -r requirements.txt

# --- 第二階段：最終執行環境 ---
# 建立一個最小化的、只包含應用程式和必要依賴的映像檔
# 使用 python:3.10-slim 映像檔，比完整版更小，可以讓容器更輕量、啟動更快
FROM python:3.10-slim

# 設定最終容器的工作目錄
WORKDIR /app

# 從第一階段 (builder) 將安裝好的 Python 依賴複製過來
# 這麼做的好處是不需要在 final stage 重新安裝套件，並只複製「最終需要的檔案」，而非整個建置環境
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# 複製 pip 安裝的執行檔 (如 gunicorn)，確保這些指令在最終映像檔中可用
COPY --from=builder /usr/local/bin /usr/local/bin

# 複製專案程式碼（整個當前目錄）到容器中
COPY . .

# 設定 PYTHONPATH 環境變數，讓 Python 能夠在 /app 目錄中找到模組
# 確保 `import` 語句能正確運作
ENV PYTHONPATH=/app

# --- 啟動腳本與執行指令 ---
# 將 Rich Menu 的部署邏輯整合到容器啟動流程中
# 確保在應用程式啟動前，Rich Menu 已經正確部署完成

# 複製 entrypoint.sh 腳本到容器中
COPY entrypoint.sh /app/entrypoint.sh
# 賦予腳本執行權限
RUN chmod +x /app/entrypoint.sh
# 使用 sed 將換行字元從 CRLF 轉換為 LF，可能因為換行格式不正確而導致部署失敗
RUN sed -i 's/\r$//' /app/entrypoint.sh

# 定義容器啟動時執行的指令
# 這裡不直接啟動 gunicorn，而是呼叫 entrypoint.sh 腳本
# 這樣就可以在腳本中先執行 Rich Menu 的部署，再啟動主應用程式
CMD ["/app/entrypoint.sh"]