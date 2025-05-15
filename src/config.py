"""
配置模組

此模組提供系統配置的載入和訪問功能。
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 導入配置驗證模組
try:
    from src.utils.config_validator import validate_and_exit_on_error
except ImportError:
    # 如果直接運行此文件，則使用相對導入
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.utils.config_validator import validate_and_exit_on_error

# 專案根目錄
ROOT_DIR = Path(os.path.dirname(os.path.dirname(__file__)))

# 取得目前環境（預設 dev）
ENV = os.getenv("ENV", "dev")

# 載入環境變數檔案，優先順序：
# 1. 根目錄 .env 檔案（如果存在）
# 2. 環境特定 .envs/.env.{ENV} 檔案（如果存在）
root_env_file = os.path.join(ROOT_DIR, ".env")
env_specific_file = os.path.join(ROOT_DIR, ".envs", f".env.{ENV}")

# 先載入環境特定檔案（如果存在）
if os.path.exists(env_specific_file):
    load_dotenv(env_specific_file)
    print(f"已載入環境特定配置: {env_specific_file}")

# 再載入根目錄 .env 檔案（如果存在），這樣可以覆蓋環境特定設定
if os.path.exists(root_env_file):
    load_dotenv(root_env_file, override=True)
    print(f"已載入根目錄配置: {root_env_file}")

# 目錄設定
DATA_DIR = os.path.join(ROOT_DIR, "data")
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
MODELS_DIR = os.path.join(ROOT_DIR, "models")

# 確保目錄存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# 資料庫設定
DB_URL = os.getenv("DB_URL", f"sqlite:///{os.path.join(DATA_DIR, 'market_data.db')}")
MARKET_INFO_DB = os.getenv("MARKET_INFO_DB", os.path.join(DATA_DIR, "market_info.db"))

# API 設定
API_KEY = os.getenv("API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "")

# 日誌設定
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv(
    "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

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


def load_config_file(file_path, default=None):
    """
    載入配置文件

    Args:
        file_path (str): 配置文件路徑
        default (dict, optional): 默認配置，如果文件不存在則返回此配置

    Returns:
        dict: 配置字典
    """
    import json
    import yaml

    if default is None:
        default = {}

    file_path = Path(file_path)

    if not file_path.exists():
        print(f"配置文件不存在: {file_path}")
        return default

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix.lower() in [".yaml", ".yml"]:
                return yaml.safe_load(f)
            if file_path.suffix.lower() == ".json":
                return json.load(f)

            print(f"不支援的配置文件格式: {file_path.suffix}")
            return default
    except Exception as e:
        print(f"載入配置文件時發生錯誤: {e}")
        return default


def validate_config():
    """
    驗證配置

    如果配置無效，則輸出錯誤信息並退出程序。
    """
    validate_and_exit_on_error()


# 如果直接運行此文件，則驗證配置
if __name__ == "__main__":
    validate_config()
    print("配置驗證通過，當前配置:")
    print(f"環境: {ENV}")
    print(f"資料庫 URL: {DB_URL}")
    print(f"API 金鑰: {'已設置' if API_KEY else '未設置'}")
    print(f"日誌級別: {LOG_LEVEL}")
    print(f"調試模式: {DEBUG_MODE}")
