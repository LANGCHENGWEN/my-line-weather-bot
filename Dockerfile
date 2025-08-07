# 選擇一個官方的 Python 基礎映像檔，這裡我們用 3.10 版本
FROM python:3.10-slim

# 設定容器內的工作目錄
WORKDIR /app

# 將 requirements.txt 複製到工作目錄
# 這樣做可以利用 Docker 的快取機制，當檔案沒變動時，下次建置會更快
COPY requirements.txt .

# 安裝所有 Python 依賴套件
RUN pip install --no-cache-dir -r requirements.txt

# 將你的應用程式程式碼（main.py）複製到容器中
COPY . .

# 定義容器啟動時執行的指令
# 這會啟動你的 Flask 應用程式
CMD ["python", "main.py"]