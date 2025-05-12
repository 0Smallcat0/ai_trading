import os
from dotenv import load_dotenv

# 取得目前環境（預設 dev）
env = os.getenv("ENV", "dev")
env_file = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), ".envs", f".env.{env}"
)

# 載入對應環境變數檔
load_dotenv(env_file)

# 取得常用設定
DB_URL = os.getenv("DB_URL")
API_KEY = os.getenv("API_KEY")
# 你可以依需求擴充更多設定
