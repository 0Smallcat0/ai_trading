"""策略管理服務核心模組

此模組提供策略管理的核心功能，包括：
- 策略CRUD操作
- 策略版本控制
- 策略參數管理
- 策略匯入匯出
- 策略執行狀態管理
- 策略效能追蹤
"""

import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# 導入專案配置
try:
    from src.config import DATA_DIR, LOGS_DIR, MODELS_DIR
except ImportError:
    # 如果配置不存在，使用預設值
    DATA_DIR = "data"
    LOGS_DIR = "logs"
    MODELS_DIR = "models"

# 導入子模組
from .strategy_management import (
    StrategyCRUD,
    StrategyVersion,
    StrategyTemplate,
    StrategyManagementError,
)

logger = logging.getLogger(__name__)


class StrategyManagementService:
    """策略管理服務類別"""

    def __init__(self):
        """初始化策略管理服務"""
        self.data_dir = Path(DATA_DIR)
        self.logs_dir = Path(LOGS_DIR)
        self.models_dir = Path(MODELS_DIR)
        self.strategies_dir = self.data_dir / "strategies"

        # 確保目錄存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.strategies_dir.mkdir(parents=True, exist_ok=True)

        # 初始化資料庫連接
        self.db_path = self.data_dir / "strategies.db"
        self._init_database()

        # 策略狀態管理
        self.strategy_lock = threading.Lock()

        # 初始化子模組
        self.crud = StrategyCRUD(self.db_path, self.strategies_dir)
        self.version = StrategyVersion(self.db_path, self.strategies_dir)
        self.template = StrategyTemplate()

        logger.info("策略管理服務初始化完成")

    def _init_database(self):
        """初始化策略資料庫"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 創建策略表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS strategies (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        type TEXT NOT NULL,
                        category TEXT,
                        description TEXT,
                        author TEXT,
                        version TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'draft',
                        code TEXT,
                        parameters TEXT,
                        risk_parameters TEXT,
                        performance_metrics TEXT,
                        tags TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(name, version)
                    )
                """
                )

                # 創建策略版本表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS strategy_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_id TEXT NOT NULL,
                        version TEXT NOT NULL,
                        code TEXT,
                        parameters TEXT,
                        risk_parameters TEXT,
                        change_log TEXT,
                        created_by TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (strategy_id) REFERENCES strategies (id)
                    )
                """
                )

                # 創建策略執行日誌表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS strategy_execution_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_id TEXT NOT NULL,
                        execution_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        signals_generated INTEGER DEFAULT 0,
                        trades_executed INTEGER DEFAULT 0,
                        profit_loss REAL DEFAULT 0,
                        error_message TEXT,
                        execution_details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (strategy_id) REFERENCES strategies (id)
                    )
                """
                )

                # 創建策略效能表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS strategy_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        strategy_id TEXT NOT NULL,
                        period_start DATE NOT NULL,
                        period_end DATE NOT NULL,
                        total_return REAL,
                        sharpe_ratio REAL,
                        max_drawdown REAL,
                        win_rate REAL,
                        profit_factor REAL,
                        total_trades INTEGER,
                        winning_trades INTEGER,
                        losing_trades INTEGER,
                        avg_trade_return REAL,
                        volatility REAL,
                        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (strategy_id) REFERENCES strategies (id)
                    )
                """
                )

                conn.commit()
                logger.info("策略資料庫初始化成功")

        except Exception as e:
            logger.error(f"初始化策略資料庫時發生錯誤: {e}")
            raise

    def get_strategy_types(self) -> Dict[str, List[str]]:
        """獲取策略類型定義

        Returns:
            Dict[str, List[str]]: 策略類型字典
        """
        return self.template.get_strategy_types()

    def get_strategy_templates(self) -> Dict[str, Dict]:
        """獲取策略模板

        Returns:
            Dict[str, Dict]: 策略模板字典
        """
        return self.template.get_strategy_templates()

    def create_strategy(
        self,
        name: str,
        strategy_type: str,
        category: str = None,
        description: str = "",
        author: str = "系統",
        code: str = "",
        parameters: Dict = None,
        risk_parameters: Dict = None,
        tags: List[str] = None,
    ) -> str:
        """創建新策略

        Args:
            name: 策略名稱
            strategy_type: 策略類型
            category: 策略分類
            description: 策略描述
            author: 作者
            code: 策略代碼
            parameters: 策略參數
            risk_parameters: 風險參數
            tags: 標籤列表

        Returns:
            str: 策略ID
        """
        return self.crud.create_strategy(
            name=name,
            strategy_type=strategy_type,
            category=category,
            description=description,
            author=author,
            code=code,
            parameters=parameters,
            risk_parameters=risk_parameters,
            tags=tags,
        )

    def get_strategy(self, strategy_id: str) -> Dict:
        """獲取策略詳細信息

        Args:
            strategy_id: 策略ID

        Returns:
            Dict: 策略信息
        """
        return self.crud.get_strategy(strategy_id)

    def list_strategies(
        self,
        strategy_type: str = None,
        status: str = None,
        author: str = None,
        search_query: str = None,
        limit: int = 100,
    ) -> List[Dict]:
        """列出策略

        Args:
            strategy_type: 策略類型過濾
            status: 狀態過濾
            author: 作者過濾
            search_query: 搜尋關鍵字
            limit: 返回數量限制

        Returns:
            List[Dict]: 策略列表
        """
        return self.crud.list_strategies(
            strategy_type=strategy_type,
            status=status,
            author=author,
            search_query=search_query,
            limit=limit,
        )

    def delete_strategy(self, strategy_id: str) -> bool:
        """刪除策略

        Args:
            strategy_id: 策略ID

        Returns:
            bool: 是否成功刪除
        """
        return self.crud.delete_strategy(strategy_id)

    def update_strategy_status(self, strategy_id: str, status: str) -> bool:
        """更新策略狀態

        Args:
            strategy_id: 策略ID
            status: 新狀態

        Returns:
            bool: 是否成功更新
        """
        return self.crud.update_strategy_status(strategy_id, status)

    # 版本控制方法
    def create_version(
        self,
        strategy_id: str,
        code: str = None,
        parameters: Dict = None,
        risk_parameters: Dict = None,
        change_log: str = "",
        author: str = "系統",
    ) -> str:
        """創建新版本

        Args:
            strategy_id: 策略ID
            code: 策略代碼
            parameters: 策略參數
            risk_parameters: 風險參數
            change_log: 變更日誌
            author: 作者

        Returns:
            str: 新版本號
        """
        return self.version.create_version(
            strategy_id=strategy_id,
            code=code,
            parameters=parameters,
            risk_parameters=risk_parameters,
            change_log=change_log,
            author=author,
        )

    def get_versions(self, strategy_id: str) -> List[Dict]:
        """獲取策略所有版本

        Args:
            strategy_id: 策略ID

        Returns:
            List[Dict]: 版本列表
        """
        return self.version.get_versions(strategy_id)

    def rollback_version(self, strategy_id: str, target_version: str) -> bool:
        """回滾到指定版本

        Args:
            strategy_id: 策略ID
            target_version: 目標版本號

        Returns:
            bool: 是否成功回滾
        """
        return self.version.rollback_version(strategy_id, target_version)

    # 模板相關方法
    def get_template(self, template_name: str) -> Dict:
        """獲取特定模板

        Args:
            template_name: 模板名稱

        Returns:
            Dict: 模板信息
        """
        return self.template.get_template(template_name)

    def validate_strategy_data(self, strategy_dict: Dict) -> bool:
        """驗證策略數據格式

        Args:
            strategy_dict: 策略數據字典

        Returns:
            bool: 是否有效
        """
        return self.template.validate_strategy_data(strategy_dict)

    def export_strategy_template(self, strategy_data: Dict) -> str:
        """匯出策略為模板格式

        Args:
            strategy_data: 策略數據

        Returns:
            str: JSON 格式的模板字符串
        """
        return self.template.export_strategy_template(strategy_data)
                "code": '''"""
移動平均線交叉策略

當短期移動平均線向上穿越長期移動平均線時產生買入信號，
當短期移動平均線向下穿越長期移動平均線時產生賣出信號。
"""

import pandas as pd
import numpy as np

class MovingAverageCrossStrategy:
    def __init__(self, short_window=5, long_window=20):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signals(self, data):
        """生成交易信號"""
        signals = pd.DataFrame(index=data.index)
        signals['price'] = data['close']

        # 計算移動平均線
        signals['short_ma'] = data['close'].rolling(window=self.short_window).mean()
        signals['long_ma'] = data['close'].rolling(window=self.long_window).mean()

        # 生成信號
        signals['signal'] = 0
        signals['signal'][self.short_window:] = np.where(
            signals['short_ma'][self.short_window:] > signals['long_ma'][self.short_window:], 1, 0
        )

        # 計算信號變化
        signals['positions'] = signals['signal'].diff()

        return signals
''',
                "parameters": {
                    "short_window": {
                        "type": "int",
                        "default": 5,
                        "min": 1,
                        "max": 50,
                        "description": "短期移動平均線窗口大小",
                    },
                    "long_window": {
                        "type": "int",
                        "default": 20,
                        "min": 5,
                        "max": 200,
                        "description": "長期移動平均線窗口大小",
                    },
                },
                "risk_parameters": {
                    "stop_loss": {
                        "type": "float",
                        "default": 0.05,
                        "min": 0.01,
                        "max": 0.2,
                        "description": "停損百分比",
                    },
                    "take_profit": {
                        "type": "float",
                        "default": 0.1,
                        "min": 0.02,
                        "max": 0.5,
                        "description": "停利百分比",
                    },
                    "max_position_size": {
                        "type": "float",
                        "default": 0.2,
                        "min": 0.01,
                        "max": 1.0,
                        "description": "最大倉位大小（佔總資金比例）",
                    },
                },
                "description": "移動平均線交叉策略是一種經典的技術分析策略，通過比較短期和長期移動平均線的交叉來產生交易訊號。",
            },
            "RSI策略": {
                "code": '''"""
RSI策略

使用相對強弱指數(RSI)判斷超買超賣狀態，
當RSI低於超賣閾值時產生買入信號，
當RSI高於超買閾值時產生賣出信號。
"""

import pandas as pd
import numpy as np

class RSIStrategy:
    def __init__(self, window=14, overbought=70, oversold=30):
        self.window = window
        self.overbought = overbought
        self.oversold = oversold

    def calculate_rsi(self, prices):
        """計算RSI指標"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def generate_signals(self, data):
        """生成交易信號"""
        signals = pd.DataFrame(index=data.index)
        signals['price'] = data['close']

        # 計算RSI
        signals['rsi'] = self.calculate_rsi(data['close'])

        # 生成信號
        signals['signal'] = 0
        signals['signal'] = np.where(signals['rsi'] < self.oversold, 1, 0)
        signals['signal'] = np.where(signals['rsi'] > self.overbought, -1, signals['signal'])

        # 計算信號變化
        signals['positions'] = signals['signal'].diff()

        return signals
''',
                "parameters": {
                    "window": {
                        "type": "int",
                        "default": 14,
                        "min": 2,
                        "max": 50,
                        "description": "RSI計算窗口大小",
                    },
                    "overbought": {
                        "type": "float",
                        "default": 70,
                        "min": 50,
                        "max": 90,
                        "description": "超買閾值",
                    },
                    "oversold": {
                        "type": "float",
                        "default": 30,
                        "min": 10,
                        "max": 50,
                        "description": "超賣閾值",
                    },
                },
                "risk_parameters": {
                    "stop_loss": {
                        "type": "float",
                        "default": 0.05,
                        "min": 0.01,
                        "max": 0.2,
                        "description": "停損百分比",
                    },
                    "take_profit": {
                        "type": "float",
                        "default": 0.1,
                        "min": 0.02,
                        "max": 0.5,
                        "description": "停利百分比",
                    },
                    "max_position_size": {
                        "type": "float",
                        "default": 0.2,
                        "min": 0.01,
                        "max": 1.0,
                        "description": "最大倉位大小（佔總資金比例）",
                    },
                },
                "description": "RSI策略是一種基於動量指標的交易策略，通過計算相對強弱指數來判斷市場是否處於超買或超賣狀態。",
            },
        }

    def create_strategy(
        self,
        name: str,
        strategy_type: str,
        category: str = None,
        description: str = "",
        author: str = "系統",
        code: str = "",
        parameters: Dict = None,
        risk_parameters: Dict = None,
        tags: List[str] = None,
    ) -> str:
        """創建新策略"""
        try:
            strategy_id = str(uuid.uuid4())
            version = "1.0.0"

            # 準備數據
            parameters_json = json.dumps(parameters) if parameters else "{}"
            risk_parameters_json = (
                json.dumps(risk_parameters) if risk_parameters else "{}"
            )
            tags_json = json.dumps(tags) if tags else "[]"

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 檢查策略名稱是否已存在
                cursor.execute("SELECT id FROM strategies WHERE name = ?", (name,))
                if cursor.fetchone():
                    raise ValueError(f"策略名稱 '{name}' 已存在")

                # 插入策略
                cursor.execute(
                    """
                    INSERT INTO strategies
                    (id, name, type, category, description, author, version, status,
                     code, parameters, risk_parameters, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        strategy_id,
                        name,
                        strategy_type,
                        category,
                        description,
                        author,
                        version,
                        "draft",
                        code,
                        parameters_json,
                        risk_parameters_json,
                        tags_json,
                    ),
                )

                # 創建初始版本記錄
                cursor.execute(
                    """
                    INSERT INTO strategy_versions
                    (strategy_id, version, code, parameters, risk_parameters,
                     change_log, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        strategy_id,
                        version,
                        code,
                        parameters_json,
                        risk_parameters_json,
                        "初始版本",
                        author,
                    ),
                )

                conn.commit()

                # 保存策略代碼文件
                self._save_strategy_file(strategy_id, version, code)

                logger.info(f"策略創建成功: {name} (ID: {strategy_id})")
                return strategy_id

        except Exception as e:
            logger.error(f"創建策略時發生錯誤: {e}")
            raise

    def update_strategy(
        self,
        strategy_id: str,
        name: str = None,
        strategy_type: str = None,
        category: str = None,
        description: str = None,
        code: str = None,
        parameters: Dict = None,
        risk_parameters: Dict = None,
        tags: List[str] = None,
        change_log: str = "",
        author: str = "系統",
    ) -> str:
        """更新策略並創建新版本"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 獲取當前策略信息
                cursor.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
                current_strategy = cursor.fetchone()

                if not current_strategy:
                    raise ValueError(f"策略不存在: {strategy_id}")

                # 解析當前版本號並生成新版本號
                current_version = current_strategy[6]  # version column
                new_version = self._increment_version(current_version)

                # 準備更新數據
                update_fields = []
                update_values = []

                if name is not None:
                    update_fields.append("name = ?")
                    update_values.append(name)

                if strategy_type is not None:
                    update_fields.append("type = ?")
                    update_values.append(strategy_type)

                if category is not None:
                    update_fields.append("category = ?")
                    update_values.append(category)

                if description is not None:
                    update_fields.append("description = ?")
                    update_values.append(description)

                if code is not None:
                    update_fields.append("code = ?")
                    update_values.append(code)

                if parameters is not None:
                    update_fields.append("parameters = ?")
                    update_values.append(json.dumps(parameters))

                if risk_parameters is not None:
                    update_fields.append("risk_parameters = ?")
                    update_values.append(json.dumps(risk_parameters))

                if tags is not None:
                    update_fields.append("tags = ?")
                    update_values.append(json.dumps(tags))

                # 更新版本和時間
                update_fields.extend(["version = ?", "updated_at = ?"])
                update_values.extend([new_version, datetime.now()])
                update_values.append(strategy_id)

                # 執行更新
                if update_fields:
                    query = (
                        f"UPDATE strategies SET {', '.join(update_fields)} WHERE id = ?"
                    )
                    cursor.execute(query, update_values)

                # 創建版本記錄
                cursor.execute(
                    """
                    INSERT INTO strategy_versions
                    (strategy_id, version, code, parameters, risk_parameters,
                     change_log, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        strategy_id,
                        new_version,
                        (
                            code if code is not None else current_strategy[8]
                        ),  # code column
                        (
                            json.dumps(parameters)
                            if parameters is not None
                            else current_strategy[9]
                        ),  # parameters column
                        (
                            json.dumps(risk_parameters)
                            if risk_parameters is not None
                            else current_strategy[10]
                        ),  # risk_parameters column
                        change_log,
                        author,
                    ),
                )

                conn.commit()

                # 保存策略代碼文件
                if code is not None:
                    self._save_strategy_file(strategy_id, new_version, code)

                logger.info(f"策略更新成功: {strategy_id} -> 版本 {new_version}")
                return new_version

        except Exception as e:
            logger.error(f"更新策略時發生錯誤: {e}")
            raise

    def get_strategy(self, strategy_id: str) -> Dict:
        """獲取策略詳細信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
                row = cursor.fetchone()

                if not row:
                    raise ValueError(f"策略不存在: {strategy_id}")

                # 解析策略數據
                strategy = {
                    "id": row[0],
                    "name": row[1],
                    "type": row[2],
                    "category": row[3],
                    "description": row[4],
                    "author": row[5],
                    "version": row[6],
                    "status": row[7],
                    "code": row[8],
                    "parameters": json.loads(row[9]) if row[9] else {},
                    "risk_parameters": json.loads(row[10]) if row[10] else {},
                    "performance_metrics": json.loads(row[11]) if row[11] else {},
                    "tags": json.loads(row[12]) if row[12] else [],
                    "created_at": row[13],
                    "updated_at": row[14],
                }

                return strategy

        except Exception as e:
            logger.error(f"獲取策略時發生錯誤: {e}")
            raise

    def list_strategies(
        self,
        strategy_type: str = None,
        status: str = None,
        author: str = None,
        search_query: str = None,
        limit: int = 100,
    ) -> List[Dict]:
        """列出策略"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 構建查詢條件
                conditions = []
                params = []

                if strategy_type:
                    conditions.append("type = ?")
                    params.append(strategy_type)

                if status:
                    conditions.append("status = ?")
                    params.append(status)

                if author:
                    conditions.append("author = ?")
                    params.append(author)

                if search_query:
                    conditions.append("(name LIKE ? OR description LIKE ?)")
                    params.extend([f"%{search_query}%", f"%{search_query}%"])

                # 構建完整查詢
                query = "SELECT * FROM strategies"
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                query += " ORDER BY updated_at DESC"
                query += f" LIMIT {limit}"

                # 執行查詢
                cursor = conn.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()

                # 解析結果
                strategies = []
                for row in rows:
                    strategy = {
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "category": row[3],
                        "description": row[4],
                        "author": row[5],
                        "version": row[6],
                        "status": row[7],
                        "parameters": json.loads(row[9]) if row[9] else {},
                        "risk_parameters": json.loads(row[10]) if row[10] else {},
                        "performance_metrics": json.loads(row[11]) if row[11] else {},
                        "tags": json.loads(row[12]) if row[12] else [],
                        "created_at": row[13],
                        "updated_at": row[14],
                    }
                    strategies.append(strategy)

                return strategies

        except Exception as e:
            logger.error(f"列出策略時發生錯誤: {e}")
            return []

    def delete_strategy(self, strategy_id: str) -> bool:
        """刪除策略"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 檢查策略是否存在
                cursor.execute(
                    "SELECT name FROM strategies WHERE id = ?", (strategy_id,)
                )
                strategy = cursor.fetchone()

                if not strategy:
                    raise ValueError(f"策略不存在: {strategy_id}")

                # 刪除相關記錄
                cursor.execute(
                    "DELETE FROM strategy_performance WHERE strategy_id = ?",
                    (strategy_id,),
                )
                cursor.execute(
                    "DELETE FROM strategy_execution_logs WHERE strategy_id = ?",
                    (strategy_id,),
                )
                cursor.execute(
                    "DELETE FROM strategy_versions WHERE strategy_id = ?",
                    (strategy_id,),
                )
                cursor.execute("DELETE FROM strategies WHERE id = ?", (strategy_id,))

                conn.commit()

                # 刪除策略文件
                self._delete_strategy_files(strategy_id)

                logger.info(f"策略刪除成功: {strategy[0]} (ID: {strategy_id})")
                return True

        except Exception as e:
            logger.error(f"刪除策略時發生錯誤: {e}")
            return False

    def update_strategy_status(self, strategy_id: str, status: str) -> bool:
        """更新策略狀態"""
        try:
            valid_statuses = ["draft", "active", "testing", "disabled", "archived"]
            if status not in valid_statuses:
                raise ValueError(f"無效的狀態: {status}")

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE strategies SET status = ?, updated_at = ? WHERE id = ?",
                    (status, datetime.now(), strategy_id),
                )

                if cursor.rowcount == 0:
                    raise ValueError(f"策略不存在: {strategy_id}")

                conn.commit()

                logger.info(f"策略狀態更新成功: {strategy_id} -> {status}")
                return True

        except Exception as e:
            logger.error(f"更新策略狀態時發生錯誤: {e}")
            return False

    def get_strategy_versions(self, strategy_id: str) -> List[Dict]:
        """獲取策略版本歷史"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT * FROM strategy_versions
                    WHERE strategy_id = ?
                    ORDER BY created_at DESC
                """,
                    (strategy_id,),
                )
                rows = cursor.fetchall()

                versions = []
                for row in rows:
                    version = {
                        "id": row[0],
                        "strategy_id": row[1],
                        "version": row[2],
                        "code": row[3],
                        "parameters": json.loads(row[4]) if row[4] else {},
                        "risk_parameters": json.loads(row[5]) if row[5] else {},
                        "change_log": row[6],
                        "created_by": row[7],
                        "created_at": row[8],
                    }
                    versions.append(version)

                return versions

        except Exception as e:
            logger.error(f"獲取策略版本時發生錯誤: {e}")
            return []

    def rollback_strategy(
        self, strategy_id: str, target_version: str, author: str = "系統"
    ) -> bool:
        """回滾策略到指定版本"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 獲取目標版本信息
                cursor.execute(
                    """
                    SELECT code, parameters, risk_parameters FROM strategy_versions
                    WHERE strategy_id = ? AND version = ?
                """,
                    (strategy_id, target_version),
                )
                version_data = cursor.fetchone()

                if not version_data:
                    raise ValueError(f"版本不存在: {target_version}")

                # 獲取當前版本號並生成新版本號
                cursor.execute(
                    "SELECT version FROM strategies WHERE id = ?", (strategy_id,)
                )
                current_version = cursor.fetchone()[0]
                new_version = self._increment_version(current_version)

                # 更新策略
                cursor.execute(
                    """
                    UPDATE strategies
                    SET code = ?, parameters = ?, risk_parameters = ?,
                        version = ?, updated_at = ?
                    WHERE id = ?
                """,
                    (
                        version_data[0],
                        version_data[1],
                        version_data[2],
                        new_version,
                        datetime.now(),
                        strategy_id,
                    ),
                )

                # 創建回滾版本記錄
                cursor.execute(
                    """
                    INSERT INTO strategy_versions
                    (strategy_id, version, code, parameters, risk_parameters,
                     change_log, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        strategy_id,
                        new_version,
                        version_data[0],
                        version_data[1],
                        version_data[2],
                        f"回滾到版本 {target_version}",
                        author,
                    ),
                )

                conn.commit()

                # 保存策略代碼文件
                self._save_strategy_file(strategy_id, new_version, version_data[0])

                logger.info(f"策略回滾成功: {strategy_id} 回滾到版本 {target_version}")
                return True

        except Exception as e:
            logger.error(f"回滾策略時發生錯誤: {e}")
            return False

    def export_strategy(self, strategy_id: str, export_format: str = "json") -> str:
        """匯出策略"""
        try:
            strategy = self.get_strategy(strategy_id)

            if export_format == "json":
                return json.dumps(strategy, indent=2, ensure_ascii=False, default=str)
            elif export_format == "python":
                return self._export_as_python(strategy)
            else:
                raise ValueError(f"不支援的匯出格式: {export_format}")

        except Exception as e:
            logger.error(f"匯出策略時發生錯誤: {e}")
            raise

    def import_strategy(
        self, strategy_data: str, import_format: str = "json", author: str = "系統"
    ) -> str:
        """匯入策略"""
        try:
            if import_format == "json":
                strategy_dict = json.loads(strategy_data)
            else:
                raise ValueError(f"不支援的匯入格式: {import_format}")

            # 驗證策略數據
            required_fields = ["name", "type", "description"]
            for field in required_fields:
                if field not in strategy_dict:
                    raise ValueError(f"缺少必要欄位: {field}")

            # 創建策略
            strategy_id = self.create_strategy(
                name=strategy_dict["name"],
                strategy_type=strategy_dict["type"],
                category=strategy_dict.get("category"),
                description=strategy_dict["description"],
                author=author,
                code=strategy_dict.get("code", ""),
                parameters=strategy_dict.get("parameters"),
                risk_parameters=strategy_dict.get("risk_parameters"),
                tags=strategy_dict.get("tags"),
            )

            logger.info(f"策略匯入成功: {strategy_dict['name']} (ID: {strategy_id})")
            return strategy_id

        except Exception as e:
            logger.error(f"匯入策略時發生錯誤: {e}")
            raise

    def validate_strategy_code(self, code: str) -> Dict[str, Any]:
        """驗證策略代碼"""
        try:
            import ast

            validation_result = {
                "is_valid": True,
                "syntax_errors": [],
                "warnings": [],
                "suggestions": [],
            }

            # 語法檢查
            try:
                ast.parse(code)
            except SyntaxError as e:
                validation_result["is_valid"] = False
                validation_result["syntax_errors"].append(
                    {"line": e.lineno, "message": str(e), "text": e.text}
                )

            # 基本結構檢查
            if "class" not in code:
                validation_result["warnings"].append("建議使用類別結構定義策略")

            if "generate_signals" not in code:
                validation_result["warnings"].append("建議實作 generate_signals 方法")

            return validation_result

        except Exception as e:
            logger.error(f"驗證策略代碼時發生錯誤: {e}")
            return {
                "is_valid": False,
                "syntax_errors": [{"message": str(e)}],
                "warnings": [],
                "suggestions": [],
            }

    def _increment_version(self, current_version: str) -> str:
        """遞增版本號"""
        try:
            parts = current_version.split(".")
            if len(parts) != 3:
                return "1.0.1"

            major, minor, patch = map(int, parts)
            patch += 1

            return f"{major}.{minor}.{patch}"

        except Exception:
            return "1.0.1"

    def _save_strategy_file(self, strategy_id: str, version: str, code: str):
        """保存策略代碼文件"""
        try:
            strategy_dir = self.strategies_dir / strategy_id
            strategy_dir.mkdir(exist_ok=True)

            file_path = strategy_dir / f"strategy_{version}.py"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

        except Exception as e:
            logger.error(f"保存策略文件時發生錯誤: {e}")

    def _delete_strategy_files(self, strategy_id: str):
        """刪除策略文件"""
        try:
            strategy_dir = self.strategies_dir / strategy_id
            if strategy_dir.exists():
                shutil.rmtree(strategy_dir)

        except Exception as e:
            logger.error(f"刪除策略文件時發生錯誤: {e}")

    def _export_as_python(self, strategy: Dict) -> str:
        """將策略匯出為Python文件格式"""
        template = f'''"""
策略名稱: {strategy["name"]}
策略類型: {strategy["type"]}
描述: {strategy["description"]}
作者: {strategy["author"]}
版本: {strategy["version"]}
創建時間: {strategy["created_at"]}
更新時間: {strategy["updated_at"]}
"""

# 策略參數
PARAMETERS = {json.dumps(strategy["parameters"], indent=4, ensure_ascii=False)}

# 風險管理參數
RISK_PARAMETERS = {json.dumps(strategy["risk_parameters"], indent=4, ensure_ascii=False)}

# 策略代碼
{strategy["code"]}
'''
        return template

    def get_strategy_statistics(self) -> Dict[str, Any]:
        """獲取策略統計信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 總策略數
                cursor.execute("SELECT COUNT(*) FROM strategies")
                total_strategies = cursor.fetchone()[0]

                # 按類型統計
                cursor.execute(
                    """
                    SELECT type, COUNT(*) FROM strategies
                    GROUP BY type ORDER BY COUNT(*) DESC
                """
                )
                type_stats = dict(cursor.fetchall())

                # 按狀態統計
                cursor.execute(
                    """
                    SELECT status, COUNT(*) FROM strategies
                    GROUP BY status ORDER BY COUNT(*) DESC
                """
                )
                status_stats = dict(cursor.fetchall())

                # 按作者統計
                cursor.execute(
                    """
                    SELECT author, COUNT(*) FROM strategies
                    GROUP BY author ORDER BY COUNT(*) DESC LIMIT 10
                """
                )
                author_stats = dict(cursor.fetchall())

                return {
                    "total_strategies": total_strategies,
                    "by_type": type_stats,
                    "by_status": status_stats,
                    "by_author": author_stats,
                }

        except Exception as e:
            logger.error(f"獲取策略統計信息時發生錯誤: {e}")
            return {}

    def search_strategies(self, query: str, filters: Dict = None) -> List[Dict]:
        """搜尋策略"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 構建搜尋條件
                conditions = ["(name LIKE ? OR description LIKE ? OR tags LIKE ?)"]
                params = [f"%{query}%", f"%{query}%", f"%{query}%"]

                # 添加過濾條件
                if filters:
                    if filters.get("type"):
                        conditions.append("type = ?")
                        params.append(filters["type"])

                    if filters.get("status"):
                        conditions.append("status = ?")
                        params.append(filters["status"])

                    if filters.get("author"):
                        conditions.append("author = ?")
                        params.append(filters["author"])

                # 構建查詢
                query_sql = f"""
                    SELECT * FROM strategies
                    WHERE {' AND '.join(conditions)}
                    ORDER BY updated_at DESC
                    LIMIT 50
                """

                cursor = conn.cursor()
                cursor.execute(query_sql, params)
                rows = cursor.fetchall()

                # 解析結果
                strategies = []
                for row in rows:
                    strategy = {
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "category": row[3],
                        "description": row[4],
                        "author": row[5],
                        "version": row[6],
                        "status": row[7],
                        "parameters": json.loads(row[9]) if row[9] else {},
                        "risk_parameters": json.loads(row[10]) if row[10] else {},
                        "performance_metrics": json.loads(row[11]) if row[11] else {},
                        "tags": json.loads(row[12]) if row[12] else [],
                        "created_at": row[13],
                        "updated_at": row[14],
                    }
                    strategies.append(strategy)

                return strategies

        except Exception as e:
            logger.error(f"搜尋策略時發生錯誤: {e}")
            return []
