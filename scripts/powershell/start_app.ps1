# 啟動 AI 交易系統應用
# 使用 Poetry 虛擬環境運行 Streamlit 應用

# 切換到專案目錄
cd $PSScriptRoot

# 檢查是否有 Streamlit 進程正在運行
$streamlitProcess = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -ErrorAction SilentlyContinue
if ($streamlitProcess) {
    Write-Host "發現 Streamlit 進程正在運行 (PID: $streamlitProcess)，正在終止..." -ForegroundColor Yellow
    Stop-Process -Id $streamlitProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# 使用 Poetry 運行 Streamlit 應用
Write-Host "正在啟動 AI 交易系統..." -ForegroundColor Green
poetry run python -m streamlit run src\ui\web_ui.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true

# 如果應用意外退出，等待用戶按鍵後關閉窗口
Write-Host "應用已退出。按任意鍵關閉此窗口..." -ForegroundColor Red
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
