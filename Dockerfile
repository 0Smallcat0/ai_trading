# AI 股票自動交易系統 Docker 配置
# 多階段建置，優化映像檔大小和安全性

# =============================================================================
# 建置階段 - 安裝相依套件和建置應用
# =============================================================================
FROM python:3.11-slim as builder

# 設定環境變數
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安裝系統相依套件
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Poetry
RUN pip install poetry==1.7.1

# 設定 Poetry 配置
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# 設定工作目錄
WORKDIR /app

# 複製 Poetry 配置檔案
COPY pyproject.toml poetry.lock ./

# 安裝 Python 相依套件
RUN poetry install --only=main --no-root && rm -rf $POETRY_CACHE_DIR

# =============================================================================
# 生產階段 - 建立最終映像檔
# =============================================================================
FROM python:3.11-slim as production

# 設定環境變數
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    ENVIRONMENT=production

# 安裝運行時相依套件
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 創建非 root 使用者
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 設定工作目錄
WORKDIR /app

# 從建置階段複製虛擬環境
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

# 複製應用程式碼
COPY --chown=appuser:appuser . .

# 創建必要的目錄
RUN mkdir -p /app/data /app/logs /app/uploads /app/backups && \
    chown -R appuser:appuser /app

# 切換到非 root 使用者
USER appuser

# 健康檢查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/health || exit 1

# 暴露埠號
EXPOSE 8501 8000

# 設定啟動命令
CMD ["python", "-m", "streamlit", "run", "src/ui/web_ui.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]

# =============================================================================
# 開發階段 - 包含開發工具
# =============================================================================
FROM builder as development

# 安裝開發相依套件
RUN poetry install --no-root

# 安裝額外的開發工具
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# 設定開發環境變數
ENV ENVIRONMENT=development \
    DEBUG=true

# 複製應用程式碼
COPY . .

# 暴露開發用埠號
EXPOSE 8501 8000 8888

# 開發模式啟動命令
CMD ["python", "-m", "streamlit", "run", "src/ui/web_ui.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=false"]

# =============================================================================
# 測試階段 - 用於 CI/CD
# =============================================================================
FROM development as testing

# 安裝測試相依套件
RUN poetry install --with=test

# 設定測試環境變數
ENV ENVIRONMENT=testing \
    TEST_MODE=true

# 執行測試
RUN poetry run pytest tests/ --cov=src --cov-report=xml

# =============================================================================
# 標籤和元資料
# =============================================================================
LABEL maintainer="AI Trading Team" \
      version="1.0.0" \
      description="AI 股票自動交易系統" \
      org.opencontainers.image.source="https://github.com/your-org/ai-trading" \
      org.opencontainers.image.documentation="https://github.com/your-org/ai-trading/blob/main/README.md" \
      org.opencontainers.image.licenses="MIT"
