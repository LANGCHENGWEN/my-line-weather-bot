#!/bin/bash
# 這一行稱為 Shebang，它告訴作業系統這個腳本應該使用 /bin/bash 來執行，***而且一定要在這個檔案的第一行

# 確保腳本在任何指令失敗時立即退出，防止腳本在部分失敗後繼續執行，導致後續的錯誤
set -e

# --- 部署 LINE Rich Menu ---
# 在應用程式啟動前，先執行 Rich Menu 的部署腳本
echo "Deploying LINE Rich Menu..."
# 先執行 rich_menu_deployer.py 的部署腳本
# || echo "..." 是一個條件執行語法：如果前一個指令 (python ...) 失敗，則執行後面的 echo 指令
# 這樣即使 Rich Menu 部署失敗，也會輸出錯誤訊息，但腳本會因為 set -e 而終止
python -m rich_menu_manager.rich_menu_deployer || echo "Rich menu deployment failed, continuing startup..."
# python -m 是以模組形式執行腳本，確保 Python 能正確找到路徑

# --- 啟動應用程式 ---
# 使用 gunicorn 啟動 Python Web 應用程式
echo "Starting application..."
# gunicorn 是 Python Web 伺服器，負責處理 HTTP 請求
# entrypoint.sh 是一個臨時的啟動器，主要用來部署 Rich Menu，但部署到雲端時，是要啟動 gunicorn 伺服器來運行應用程式，所以才需要在前面加上 exec
# exec 會替換掉當前的 entrypoint.sh 進程，用 gunicorn 來運行應用程式，讓應用程式成為進程 1
# --bind 0.0.0.0:${PORT:-8080} 告訴 gunicorn 監聽所有網路接口 (0.0.0.0)，並使用環境變數 PORT 指定的埠號
# 如果 PORT 環境變數未設定，則使用預設的 8080 埠號，這是 Cloud Run 的標準設定
# main:app 代表在 main.py 檔案中，找到一個名為 app 的 Flask 應用程式實例來運行
exec gunicorn --bind 0.0.0.0:${PORT:-8080} main:app