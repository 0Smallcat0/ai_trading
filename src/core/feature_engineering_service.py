"""
特徵工程服務核心模組

此模組提供特徵工程的核心功能，包括：
- 特徵計算與更新
- 特徵查詢與分析
- 特徵處理操作（標準化、降維、選擇等）
- 特徵品質監控
- 操作日誌記錄
"""

import os
import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.feature_selection import (
    SelectKBest,
    f_regression,
    mutual_info_regression,
    RFE,
)
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Lasso

# 導入專案配置
try:
    from src.config import DATA_DIR, LOGS_DIR, MODELS_DIR
except ImportError:
    # 如果配置不存在，使用預設值
    DATA_DIR = "data"
    LOGS_DIR = "logs"
    MODELS_DIR = "models"

# 設置日誌
logger = logging.getLogger(__name__)


class FeatureEngineeringService:
    """特徵工程服務類別"""

    def __init__(self):
        """初始化特徵工程服務"""
        self.data_dir = Path(DATA_DIR)
        self.logs_dir = Path(LOGS_DIR)
        self.models_dir = Path(MODELS_DIR)

        # 確保目錄存在
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # 初始化資料庫連接
        self.db_path = self.data_dir / "features.db"
        self._init_database()

        # 任務狀態管理
        self.current_tasks = {}
        self.task_lock = threading.Lock()

        logger.info("特徵工程服務初始化完成")

    def _init_database(self):
        """初始化特徵資料庫"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 創建特徵表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS features (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        stock_id TEXT NOT NULL,
                        feature_name TEXT NOT NULL,
                        feature_type TEXT NOT NULL,
                        feature_value REAL,
                        calculation_date DATE NOT NULL,
                        data_date DATE NOT NULL,
                        parameters TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(stock_id, feature_name, data_date)
                    )
                """
                )

                # 創建特徵計算日誌表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS feature_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id TEXT NOT NULL,
                        operation_type TEXT NOT NULL,
                        feature_type TEXT,
                        stock_ids TEXT,
                        start_date DATE,
                        end_date DATE,
                        status TEXT NOT NULL,
                        progress INTEGER DEFAULT 0,
                        total_records INTEGER DEFAULT 0,
                        processed_records INTEGER DEFAULT 0,
                        error_records INTEGER DEFAULT 0,
                        message TEXT,
                        parameters TEXT,
                        start_time TIMESTAMP,
                        end_time TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # 創建特徵品質表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS feature_quality (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        feature_name TEXT NOT NULL,
                        feature_type TEXT NOT NULL,
                        completeness REAL,
                        accuracy REAL,
                        consistency REAL,
                        timeliness REAL,
                        overall_score REAL,
                        check_date DATE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                conn.commit()
                logger.info("特徵資料庫初始化成功")

        except Exception as e:
            logger.error(f"初始化特徵資料庫時發生錯誤: {e}")
            raise

    def get_available_features(self) -> Dict[str, List[Dict]]:
        """獲取可用的特徵列表"""
        return {
            "technical": self._get_technical_indicators(),
            "fundamental": self._get_fundamental_indicators(),
            "sentiment": self._get_sentiment_indicators(),
        }

    def _get_technical_indicators(self) -> List[Dict]:
        """獲取技術指標列表"""
        return [
            {
                "name": "RSI",
                "full_name": "相對強弱指標",
                "category": "動量指標",
                "description": "測量價格變動的速度和幅度",
                "parameters": {"window": 14},
                "data_requirements": ["close"],
                "calculation_cost": "低",
            },
            {
                "name": "MACD",
                "full_name": "移動平均收斂散度",
                "category": "趨勢指標",
                "description": "比較兩條不同週期的指數移動平均線",
                "parameters": {"fast": 12, "slow": 26, "signal": 9},
                "data_requirements": ["close"],
                "calculation_cost": "中",
            },
            {
                "name": "BBANDS",
                "full_name": "布林帶",
                "category": "波動指標",
                "description": "移動平均線加減標準差構成的通道",
                "parameters": {"window": 20, "std": 2},
                "data_requirements": ["close"],
                "calculation_cost": "中",
            },
            {
                "name": "ATR",
                "full_name": "平均真實範圍",
                "category": "波動指標",
                "description": "測量市場波動性",
                "parameters": {"window": 14},
                "data_requirements": ["high", "low", "close"],
                "calculation_cost": "低",
            },
        ]

    def _get_fundamental_indicators(self) -> List[Dict]:
        """獲取基本面指標列表"""
        return [
            {
                "name": "PE",
                "full_name": "本益比",
                "category": "估值指標",
                "description": "股價與每股盈餘的比率",
                "data_source": "財務報表",
                "update_frequency": "季度",
            },
            {
                "name": "PB",
                "full_name": "股價淨值比",
                "category": "估值指標",
                "description": "股價與每股淨資產的比率",
                "data_source": "財務報表",
                "update_frequency": "季度",
            },
            {
                "name": "ROE",
                "full_name": "股東權益報酬率",
                "category": "獲利能力指標",
                "description": "淨利潤與股東權益的比率",
                "data_source": "財務報表",
                "update_frequency": "季度",
            },
        ]

    def _get_sentiment_indicators(self) -> List[Dict]:
        """獲取情緒指標列表"""
        return [
            {
                "name": "NEWS_SENT",
                "full_name": "新聞情緒指標",
                "category": "媒體情緒",
                "description": "基於新聞報導的情緒分析",
                "data_source": "新聞API",
                "update_frequency": "每日",
            },
            {
                "name": "SOCIAL_SENT",
                "full_name": "社交媒體情緒指標",
                "category": "社交媒體情緒",
                "description": "基於社交媒體的情緒分析",
                "data_source": "社交媒體API",
                "update_frequency": "每小時",
            },
        ]

    def start_feature_calculation(
        self,
        feature_type: str,
        stock_ids: List[str],
        start_date: date,
        end_date: date,
        indicators: List[str] = None,
        parameters: Dict = None,
    ) -> str:
        """啟動特徵計算任務"""
        task_id = f"calc_{int(time.time())}"

        # 記錄任務開始
        self._log_task_start(
            task_id=task_id,
            operation_type="feature_calculation",
            feature_type=feature_type,
            stock_ids=stock_ids,
            start_date=start_date,
            end_date=end_date,
            parameters=parameters,
        )

        # 啟動背景任務
        thread = threading.Thread(
            target=self._calculate_features_background,
            args=(
                task_id,
                feature_type,
                stock_ids,
                start_date,
                end_date,
                indicators,
                parameters,
            ),
        )
        thread.daemon = True
        thread.start()

        return task_id

    def _calculate_features_background(
        self,
        task_id: str,
        feature_type: str,
        stock_ids: List[str],
        start_date: date,
        end_date: date,
        indicators: List[str] = None,
        parameters: Dict = None,
    ):
        """背景執行特徵計算"""
        try:
            with self.task_lock:
                self.current_tasks[task_id] = {
                    "status": "running",
                    "progress": 0,
                    "message": "開始計算特徵...",
                    "start_time": datetime.now(),
                }

            total_stocks = len(stock_ids)
            processed_count = 0
            error_count = 0

            for i, stock_id in enumerate(stock_ids):
                try:
                    # 模擬特徵計算
                    if feature_type == "technical":
                        self._calculate_technical_features(
                            stock_id, start_date, end_date, indicators, parameters
                        )
                    elif feature_type == "fundamental":
                        self._calculate_fundamental_features(
                            stock_id, start_date, end_date, indicators, parameters
                        )
                    elif feature_type == "sentiment":
                        self._calculate_sentiment_features(
                            stock_id, start_date, end_date, indicators, parameters
                        )

                    processed_count += 1

                except Exception as e:
                    logger.error(f"計算 {stock_id} 特徵時發生錯誤: {e}")
                    error_count += 1

                # 更新進度
                progress = int((i + 1) / total_stocks * 100)
                with self.task_lock:
                    self.current_tasks[task_id].update(
                        {
                            "progress": progress,
                            "message": f"正在處理 {stock_id}... ({i+1}/{total_stocks})",
                        }
                    )

                # 模擬處理時間
                time.sleep(0.1)

            # 任務完成
            with self.task_lock:
                self.current_tasks[task_id].update(
                    {
                        "status": "completed",
                        "progress": 100,
                        "message": f"計算完成！處理 {processed_count} 檔股票，{error_count} 檔發生錯誤",
                        "end_time": datetime.now(),
                        "processed_records": processed_count,
                        "error_records": error_count,
                    }
                )

            # 記錄任務完成
            self._log_task_completion(
                task_id, "completed", processed_count, error_count
            )

        except Exception as e:
            logger.error(f"特徵計算任務 {task_id} 發生錯誤: {e}")

            with self.task_lock:
                self.current_tasks[task_id].update(
                    {
                        "status": "failed",
                        "message": f"計算失敗: {str(e)}",
                        "end_time": datetime.now(),
                    }
                )

            self._log_task_completion(task_id, "failed", 0, 0, str(e))

    def _calculate_technical_features(
        self,
        stock_id: str,
        start_date: date,
        end_date: date,
        indicators: List[str] = None,
        parameters: Dict = None,
    ):
        """計算技術指標特徵"""
        # 模擬技術指標計算
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")

        # 模擬價格數據
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(len(date_range)) * 0.02)

        features_data = []

        for i, calc_date in enumerate(date_range):
            if indicators is None or "RSI" in indicators:
                # 模擬 RSI 計算
                rsi_value = 30 + np.random.rand() * 40  # 30-70 範圍
                features_data.append(
                    {
                        "stock_id": stock_id,
                        "feature_name": "RSI_14",
                        "feature_type": "technical",
                        "feature_value": rsi_value,
                        "data_date": calc_date.date(),
                        "parameters": json.dumps({"window": 14}),
                    }
                )

            if indicators is None or "MACD" in indicators:
                # 模擬 MACD 計算
                macd_value = np.random.randn() * 2
                features_data.append(
                    {
                        "stock_id": stock_id,
                        "feature_name": "MACD",
                        "feature_type": "technical",
                        "feature_value": macd_value,
                        "data_date": calc_date.date(),
                        "parameters": json.dumps({"fast": 12, "slow": 26, "signal": 9}),
                    }
                )

        # 儲存到資料庫
        self._save_features(features_data)

    def _calculate_fundamental_features(
        self,
        stock_id: str,
        start_date: date,
        end_date: date,
        indicators: List[str] = None,
        parameters: Dict = None,
    ):
        """計算基本面指標特徵"""
        # 模擬基本面指標計算（通常是季度數據）
        features_data = []

        # 生成季度日期
        current_date = start_date
        while current_date <= end_date:
            if indicators is None or "PE" in indicators:
                # 模擬 PE 比率
                pe_value = 10 + np.random.rand() * 20  # 10-30 範圍
                features_data.append(
                    {
                        "stock_id": stock_id,
                        "feature_name": "PE",
                        "feature_type": "fundamental",
                        "feature_value": pe_value,
                        "data_date": current_date,
                        "parameters": json.dumps({}),
                    }
                )

            if indicators is None or "ROE" in indicators:
                # 模擬 ROE
                roe_value = 0.05 + np.random.rand() * 0.15  # 5%-20% 範圍
                features_data.append(
                    {
                        "stock_id": stock_id,
                        "feature_name": "ROE",
                        "feature_type": "fundamental",
                        "feature_value": roe_value,
                        "data_date": current_date,
                        "parameters": json.dumps({}),
                    }
                )

            # 移動到下一季
            if current_date.month <= 3:
                current_date = current_date.replace(month=6)
            elif current_date.month <= 6:
                current_date = current_date.replace(month=9)
            elif current_date.month <= 9:
                current_date = current_date.replace(month=12)
            else:
                current_date = current_date.replace(year=current_date.year + 1, month=3)

        # 儲存到資料庫
        self._save_features(features_data)

    def _calculate_sentiment_features(
        self,
        stock_id: str,
        start_date: date,
        end_date: date,
        indicators: List[str] = None,
        parameters: Dict = None,
    ):
        """計算情緒指標特徵"""
        # 模擬情緒指標計算
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")

        features_data = []

        for calc_date in date_range:
            if indicators is None or "NEWS_SENT" in indicators:
                # 模擬新聞情緒分數
                news_sentiment = np.random.randn() * 0.3  # -1 到 1 範圍
                features_data.append(
                    {
                        "stock_id": stock_id,
                        "feature_name": "NEWS_SENT",
                        "feature_type": "sentiment",
                        "feature_value": news_sentiment,
                        "data_date": calc_date.date(),
                        "parameters": json.dumps({}),
                    }
                )

            if indicators is None or "SOCIAL_SENT" in indicators:
                # 模擬社交媒體情緒分數
                social_sentiment = np.random.randn() * 0.4  # -1 到 1 範圍
                features_data.append(
                    {
                        "stock_id": stock_id,
                        "feature_name": "SOCIAL_SENT",
                        "feature_type": "sentiment",
                        "feature_value": social_sentiment,
                        "data_date": calc_date.date(),
                        "parameters": json.dumps({}),
                    }
                )

        # 儲存到資料庫
        self._save_features(features_data)

    def _save_features(self, features_data: List[Dict]):
        """儲存特徵數據到資料庫"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                for feature in features_data:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO features
                        (stock_id, feature_name, feature_type, feature_value,
                         calculation_date, data_date, parameters)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            feature["stock_id"],
                            feature["feature_name"],
                            feature["feature_type"],
                            feature["feature_value"],
                            datetime.now().date(),
                            feature["data_date"],
                            feature["parameters"],
                        ),
                    )

                conn.commit()

        except Exception as e:
            logger.error(f"儲存特徵數據時發生錯誤: {e}")
            raise

    def get_task_status(self, task_id: str) -> Dict:
        """獲取任務狀態"""
        with self.task_lock:
            return self.current_tasks.get(task_id, {"status": "not_found"})

    def query_features(
        self,
        feature_type: str = None,
        stock_ids: List[str] = None,
        feature_names: List[str] = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """查詢特徵數據"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 構建查詢條件
                conditions = []
                params = []

                if feature_type:
                    conditions.append("feature_type = ?")
                    params.append(feature_type)

                if stock_ids:
                    placeholders = ",".join(["?" for _ in stock_ids])
                    conditions.append(f"stock_id IN ({placeholders})")
                    params.extend(stock_ids)

                if feature_names:
                    placeholders = ",".join(["?" for _ in feature_names])
                    conditions.append(f"feature_name IN ({placeholders})")
                    params.extend(feature_names)

                if start_date:
                    conditions.append("data_date >= ?")
                    params.append(start_date)

                if end_date:
                    conditions.append("data_date <= ?")
                    params.append(end_date)

                # 構建完整查詢
                query = "SELECT * FROM features"
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                query += " ORDER BY data_date DESC, stock_id, feature_name"
                query += f" LIMIT {limit}"

                # 執行查詢
                df = pd.read_sql_query(query, conn, params=params)

                # 轉換日期欄位
                if not df.empty:
                    df["data_date"] = pd.to_datetime(df["data_date"])
                    df["calculation_date"] = pd.to_datetime(df["calculation_date"])
                    df["created_at"] = pd.to_datetime(df["created_at"])

                return df

        except Exception as e:
            logger.error(f"查詢特徵數據時發生錯誤: {e}")
            return pd.DataFrame()

    def get_feature_statistics(self, feature_name: str, stock_id: str = None) -> Dict:
        """獲取特徵統計資訊"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 構建查詢條件
                conditions = ["feature_name = ?"]
                params = [feature_name]

                if stock_id:
                    conditions.append("stock_id = ?")
                    params.append(stock_id)

                query = f"""
                    SELECT
                        COUNT(*) as count,
                        AVG(feature_value) as mean,
                        MIN(feature_value) as min_value,
                        MAX(feature_value) as max_value,
                        (SELECT feature_value FROM features
                         WHERE {' AND '.join(conditions)}
                         ORDER BY feature_value
                         LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM features WHERE {' AND '.join(conditions)})) as median
                    FROM features
                    WHERE {' AND '.join(conditions)}
                """

                cursor = conn.cursor()
                cursor.execute(query, params + params)  # params 重複是因為子查詢也需要
                result = cursor.fetchone()

                if result and result[0] > 0:
                    # 計算標準差
                    std_query = f"""
                        SELECT SQRT(AVG((feature_value - ?)*(feature_value - ?))) as std_dev
                        FROM features
                        WHERE {' AND '.join(conditions)}
                    """
                    cursor.execute(std_query, [result[1], result[1]] + params)
                    std_result = cursor.fetchone()

                    return {
                        "count": result[0],
                        "mean": result[1],
                        "std": std_result[0] if std_result else 0,
                        "min": result[2],
                        "max": result[3],
                        "median": result[4],
                    }
                else:
                    return {
                        "count": 0,
                        "mean": 0,
                        "std": 0,
                        "min": 0,
                        "max": 0,
                        "median": 0,
                    }

        except Exception as e:
            logger.error(f"獲取特徵統計資訊時發生錯誤: {e}")
            return {}

    def standardize_features(
        self,
        data: pd.DataFrame,
        method: str = "standard",
        feature_columns: List[str] = None,
    ) -> Tuple[pd.DataFrame, Dict]:
        """標準化特徵"""
        try:
            if data.empty:
                return data, {}

            # 選擇要標準化的欄位
            if feature_columns is None:
                numeric_columns = data.select_dtypes(
                    include=[np.number]
                ).columns.tolist()
                feature_columns = [
                    col for col in numeric_columns if col not in ["id", "stock_id"]
                ]

            if not feature_columns:
                return data, {}

            # 選擇標準化方法
            if method == "standard":
                scaler = StandardScaler()
            elif method == "minmax":
                scaler = MinMaxScaler()
            elif method == "robust":
                scaler = RobustScaler()
            else:
                raise ValueError(f"不支援的標準化方法: {method}")

            # 執行標準化
            result_data = data.copy()
            scaled_values = scaler.fit_transform(data[feature_columns])
            result_data[feature_columns] = scaled_values

            # 返回標準化參數
            scaler_params = {
                "method": method,
                "feature_columns": feature_columns,
                "scaler_params": {},
            }

            if method == "standard":
                scaler_params["scaler_params"] = {
                    "mean": scaler.mean_.tolist(),
                    "scale": scaler.scale_.tolist(),
                }
            elif method == "minmax":
                scaler_params["scaler_params"] = {
                    "min": scaler.min_.tolist(),
                    "scale": scaler.scale_.tolist(),
                }
            elif method == "robust":
                scaler_params["scaler_params"] = {
                    "center": scaler.center_.tolist(),
                    "scale": scaler.scale_.tolist(),
                }

            return result_data, scaler_params

        except Exception as e:
            logger.error(f"標準化特徵時發生錯誤: {e}")
            return data, {}

    def select_features(
        self,
        data: pd.DataFrame,
        target_column: str,
        method: str = "f_regression",
        k: int = 10,
    ) -> Tuple[pd.DataFrame, List[str]]:
        """特徵選擇"""
        try:
            if data.empty or target_column not in data.columns:
                return data, []

            # 準備特徵和目標變數
            feature_columns = [
                col
                for col in data.columns
                if col != target_column and data[col].dtype in [np.number]
            ]

            if len(feature_columns) == 0:
                return data, []

            X = data[feature_columns].fillna(0)
            y = data[target_column].fillna(0)

            # 選擇特徵選擇方法
            if method == "f_regression":
                selector = SelectKBest(
                    score_func=f_regression, k=min(k, len(feature_columns))
                )
            elif method == "mutual_info":
                selector = SelectKBest(
                    score_func=mutual_info_regression, k=min(k, len(feature_columns))
                )
            elif method == "rfe":
                estimator = RandomForestRegressor(n_estimators=10, random_state=42)
                selector = RFE(
                    estimator=estimator,
                    n_features_to_select=min(k, len(feature_columns)),
                )
            elif method == "lasso":
                # 使用 Lasso 進行特徵選擇
                lasso = Lasso(alpha=0.01, random_state=42)
                lasso.fit(X, y)
                selected_features = [
                    col
                    for col, coef in zip(feature_columns, lasso.coef_)
                    if abs(coef) > 1e-5
                ]
                selected_features = selected_features[:k]  # 限制數量

                result_data = data[[target_column] + selected_features].copy()
                return result_data, selected_features
            else:
                raise ValueError(f"不支援的特徵選擇方法: {method}")

            # 執行特徵選擇
            X_selected = selector.fit_transform(X, y)
            selected_mask = selector.get_support()
            selected_features = [
                feature_columns[i]
                for i, selected in enumerate(selected_mask)
                if selected
            ]

            # 構建結果數據
            result_data = data[[target_column] + selected_features].copy()

            return result_data, selected_features

        except Exception as e:
            logger.error(f"特徵選擇時發生錯誤: {e}")
            return data, []

    def reduce_dimensions(
        self,
        data: pd.DataFrame,
        method: str = "pca",
        n_components: int = 2,
        feature_columns: List[str] = None,
    ) -> Tuple[pd.DataFrame, Dict]:
        """降維處理"""
        try:
            if data.empty:
                return data, {}

            # 選擇要降維的欄位
            if feature_columns is None:
                numeric_columns = data.select_dtypes(
                    include=[np.number]
                ).columns.tolist()
                feature_columns = [
                    col for col in numeric_columns if col not in ["id", "stock_id"]
                ]

            if len(feature_columns) < n_components:
                return data, {}

            X = data[feature_columns].fillna(0)

            # 選擇降維方法
            if method == "pca":
                reducer = PCA(n_components=n_components, random_state=42)
                X_reduced = reducer.fit_transform(X)

                # 創建新的欄位名稱
                component_names = [f"PC{i+1}" for i in range(n_components)]

                # 降維參數
                reduction_params = {
                    "method": method,
                    "n_components": n_components,
                    "explained_variance_ratio": reducer.explained_variance_ratio_.tolist(),
                    "total_explained_variance": float(
                        reducer.explained_variance_ratio_.sum()
                    ),
                }

            elif method == "tsne":
                reducer = TSNE(
                    n_components=n_components,
                    random_state=42,
                    perplexity=min(30, len(X) - 1),
                )
                X_reduced = reducer.fit_transform(X)

                # 創建新的欄位名稱
                component_names = [f"TSNE{i+1}" for i in range(n_components)]

                # 降維參數
                reduction_params = {
                    "method": method,
                    "n_components": n_components,
                    "kl_divergence": (
                        float(reducer.kl_divergence_)
                        if hasattr(reducer, "kl_divergence_")
                        else None
                    ),
                }

            else:
                raise ValueError(f"不支援的降維方法: {method}")

            # 構建結果數據
            result_data = data.copy()

            # 移除原始特徵欄位
            result_data = result_data.drop(columns=feature_columns)

            # 添加降維後的欄位
            for i, component_name in enumerate(component_names):
                result_data[component_name] = X_reduced[:, i]

            return result_data, reduction_params

        except Exception as e:
            logger.error(f"降維處理時發生錯誤: {e}")
            return data, {}

    def detect_outliers(
        self,
        data: pd.DataFrame,
        feature_column: str,
        method: str = "iqr",
        threshold: float = 1.5,
    ) -> Tuple[pd.DataFrame, List[int]]:
        """異常值檢測"""
        try:
            if data.empty or feature_column not in data.columns:
                return data, []

            values = data[feature_column].dropna()

            if method == "iqr":
                # 使用四分位距方法
                Q1 = values.quantile(0.25)
                Q3 = values.quantile(0.75)
                IQR = Q3 - Q1

                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR

                outlier_mask = (data[feature_column] < lower_bound) | (
                    data[feature_column] > upper_bound
                )

            elif method == "zscore":
                # 使用 Z-score 方法
                mean_val = values.mean()
                std_val = values.std()

                z_scores = np.abs((data[feature_column] - mean_val) / std_val)
                outlier_mask = z_scores > threshold

            else:
                raise ValueError(f"不支援的異常值檢測方法: {method}")

            # 獲取異常值索引
            outlier_indices = data[outlier_mask].index.tolist()

            # 標記異常值
            result_data = data.copy()
            result_data[f"{feature_column}_is_outlier"] = outlier_mask

            return result_data, outlier_indices

        except Exception as e:
            logger.error(f"異常值檢測時發生錯誤: {e}")
            return data, []

    def _log_task_start(
        self,
        task_id: str,
        operation_type: str,
        feature_type: str = None,
        stock_ids: List[str] = None,
        start_date: date = None,
        end_date: date = None,
        parameters: Dict = None,
    ):
        """記錄任務開始"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO feature_logs
                    (task_id, operation_type, feature_type, stock_ids, start_date, end_date,
                     status, parameters, start_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        task_id,
                        operation_type,
                        feature_type,
                        json.dumps(stock_ids) if stock_ids else None,
                        start_date,
                        end_date,
                        "running",
                        json.dumps(parameters) if parameters else None,
                        datetime.now(),
                    ),
                )
                conn.commit()

        except Exception as e:
            logger.error(f"記錄任務開始時發生錯誤: {e}")

    def _log_task_completion(
        self,
        task_id: str,
        status: str,
        processed_records: int = 0,
        error_records: int = 0,
        message: str = None,
    ):
        """記錄任務完成"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE feature_logs
                    SET status = ?, processed_records = ?, error_records = ?,
                        message = ?, end_time = ?, progress = 100
                    WHERE task_id = ?
                """,
                    (
                        status,
                        processed_records,
                        error_records,
                        message,
                        datetime.now(),
                        task_id,
                    ),
                )
                conn.commit()

        except Exception as e:
            logger.error(f"記錄任務完成時發生錯誤: {e}")

    def get_operation_logs(
        self,
        operation_type: str = None,
        start_date: date = None,
        end_date: date = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """獲取操作日誌"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 構建查詢條件
                conditions = []
                params = []

                if operation_type:
                    conditions.append("operation_type = ?")
                    params.append(operation_type)

                if start_date:
                    conditions.append("DATE(start_time) >= ?")
                    params.append(start_date)

                if end_date:
                    conditions.append("DATE(start_time) <= ?")
                    params.append(end_date)

                # 構建完整查詢
                query = "SELECT * FROM feature_logs"
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                query += " ORDER BY start_time DESC"
                query += f" LIMIT {limit}"

                # 執行查詢
                df = pd.read_sql_query(query, conn, params=params)

                # 轉換日期欄位
                if not df.empty:
                    df["start_time"] = pd.to_datetime(df["start_time"])
                    df["end_time"] = pd.to_datetime(df["end_time"])
                    df["created_at"] = pd.to_datetime(df["created_at"])

                return df

        except Exception as e:
            logger.error(f"獲取操作日誌時發生錯誤: {e}")
            return pd.DataFrame()
