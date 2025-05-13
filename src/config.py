import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# 專案根目錄
ROOT_DIR = Path(os.path.dirname(os.path.dirname(__file__)))

# 取得目前環境（預設 dev）
ENV = os.getenv("ENV", "dev")
env_file = os.path.join(ROOT_DIR, ".envs", f".env.{ENV}")

# 載入對應環境變數檔
load_dotenv(env_file)

# 目錄設定
DATA_DIR = os.path.join(ROOT_DIR, "data")
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
CACHE_DIR = os.path.join(DATA_DIR, "cache")

# 確保目錄存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

# 資料庫設定
DB_URL = os.getenv("DB_URL", f"sqlite:///{os.path.join(DATA_DIR, 'market_data.db')}")
MARKET_INFO_DB = os.path.join(DATA_DIR, "market_info.db")

# API 設定
API_KEY = os.getenv("API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "")

# 日誌設定
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 交易設定
TRADING_HOURS_START = os.getenv("TRADING_HOURS_START", "09:00:00")
TRADING_HOURS_END = os.getenv("TRADING_HOURS_END", "13:30:00")
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "0.2"))  # 最大持倉比例
STOP_LOSS_THRESHOLD = float(os.getenv("STOP_LOSS_THRESHOLD", "0.05"))  # 停損閾值

# 爬蟲設定
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))  # 請求超時時間（秒）
RETRY_COUNT = int(os.getenv("RETRY_COUNT", "3"))  # 重試次數

# 監控設定
PRICE_ANOMALY_THRESHOLD = float(
    os.getenv("PRICE_ANOMALY_THRESHOLD", "0.05")
)  # 價格異常閾值
VOLUME_ANOMALY_THRESHOLD = float(
    os.getenv("VOLUME_ANOMALY_THRESHOLD", "3.0")
)  # 成交量異常閾值
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))  # 檢查間隔（秒）

# 其他設定
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
