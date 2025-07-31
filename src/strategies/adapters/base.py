# -*- coding: utf-8 -*-
"""策略適配器基類模組

此模組提供將外部策略庫整合到當前系統的基礎適配器框架。
遵循零修改原則，保持原始策略代碼完全不變。

主要類別：
- LegacyStrategyAdapter: 舊版策略適配器基類
- DataFormatConverter: 數據格式轉換器
- StrategyWrapper: 策略包裝器

設計原則：
- 零修改：原始策略代碼保持完全不變
- 統一接口：提供標準Strategy接口
- 向後相容：確保API向後相容性
- 錯誤處理：統一異常處理機制
- 性能優化：最小化適配器開銷
"""

import logging
import traceback
from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd

from ...strategy.base import Strategy, StrategyError

# 設定日誌
logger = logging.getLogger(__name__)


class AdapterError(StrategyError):
    """適配器基礎錯誤"""


class DataConversionError(AdapterError):
    """數據轉換錯誤"""


class StrategyExecutionError(AdapterError):
    """策略執行錯誤"""


class DataFormatConverter:
    """數據格式轉換器。

    負責在不同數據格式間進行轉換，確保原始策略能夠
    正確處理當前系統的數據格式。

    主要功能：
    - 數據格式標準化
    - 欄位名稱映射
    - 數據類型轉換
    - 缺失值處理
    """

    # 標準欄位映射
    COLUMN_MAPPING = {
        'close': ['close', '收盤價', 'Close', 'CLOSE'],
        'open': ['open', '開盤價', 'Open', 'OPEN'],
        'high': ['high', '最高價', 'High', 'HIGH'],
        'low': ['low', '最低價', 'Low', 'LOW'],
        'volume': ['volume', '成交量', 'Volume', 'VOLUME'],
        'date': ['date', 'trade_date', '交易日期', 'Date', 'DATE'],
    }

    @classmethod
    def standardize_columns(cls, data: pd.DataFrame) -> pd.DataFrame:
        """標準化數據欄位名稱。

        Args:
            data: 輸入數據框架

        Returns:
            標準化後的數據框架

        Raises:
            DataConversionError: 當必要欄位缺失時
        """
        try:
            standardized_data = data.copy()

            # 建立反向映射
            reverse_mapping = {}
            for standard_name, variants in cls.COLUMN_MAPPING.items():
                for variant in variants:
                    if variant in data.columns:
                        reverse_mapping[variant] = standard_name
                        break

            # 重命名欄位
            if reverse_mapping:
                standardized_data = standardized_data.rename(columns=reverse_mapping)

            # 驗證必要欄位
            required_columns = ['close', 'date']
            missing_columns = [col for col in required_columns
                               if col not in standardized_data.columns]

            if missing_columns:
                raise DataConversionError(f"缺少必要欄位: {missing_columns}")

            logger.debug("數據欄位標準化完成，原始欄位: %s, 標準化欄位: %s",
                         list(data.columns), list(standardized_data.columns))
            return standardized_data

        except Exception as e:
            logger.error("數據欄位標準化失敗: %s", e)
            raise DataConversionError(f"數據欄位標準化失敗: {e}") from e

    @classmethod
    def convert_to_legacy_format(cls, data: pd.DataFrame) -> pd.DataFrame:
        """將當前系統數據格式轉換為舊版策略期望的格式。

        Args:
            data: 當前系統數據格式

        Returns:
            舊版策略期望的數據格式
        """
        try:
            # 首先標準化欄位
            legacy_data = cls.standardize_columns(data)

            # 確保數據類型正確
            if 'close' in legacy_data.columns:
                legacy_data['close'] = pd.to_numeric(legacy_data['close'], errors='coerce')

            if 'date' in legacy_data.columns:
                legacy_data['date'] = pd.to_datetime(legacy_data['date'], errors='coerce')

            # 處理缺失值
            legacy_data = legacy_data.dropna()

            # 重置索引
            legacy_data = legacy_data.reset_index(drop=True)

            logger.debug("數據格式轉換完成，數據形狀: %s", legacy_data.shape)
            return legacy_data

        except Exception as e:
            logger.error("數據格式轉換失敗: %s", e)
            raise DataConversionError(f"數據格式轉換失敗: {e}") from e


class StrategyWrapper:
    """策略包裝器。

    提供對原始策略函數的安全包裝，包括：
    - 參數驗證
    - 異常處理
    - 執行監控
    - 結果驗證
    """

    def __init__(self, strategy_func, strategy_name: str):
        """初始化策略包裝器。

        Args:
            strategy_func: 原始策略函數
            strategy_name: 策略名稱
        """
        self.strategy_func = strategy_func
        self.strategy_name = strategy_name
        self.execution_count = 0
        self.error_count = 0

    def execute(self, *args, **kwargs) -> Any:
        """安全執行策略函數。

        Args:
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            策略執行結果

        Raises:
            StrategyExecutionError: 當策略執行失敗時
        """
        try:
            self.execution_count += 1
            logger.debug("執行策略 %s，第 %d 次", self.strategy_name, self.execution_count)

            # 執行原始策略
            result = self.strategy_func(*args, **kwargs)

            logger.debug("策略 %s 執行成功", self.strategy_name)
            return result

        except Exception as e:
            self.error_count += 1
            error_msg = f"策略 {self.strategy_name} 執行失敗 (第 {self.error_count} 次錯誤): {e}"
            logger.error(error_msg)
            logger.debug("錯誤詳情: %s", traceback.format_exc())
            raise StrategyExecutionError(error_msg) from e

    @property
    def success_rate(self) -> float:
        """計算策略執行成功率"""
        if not self.execution_count:
            return 0.0
        return (self.execution_count - self.error_count) / self.execution_count


class LegacyStrategyAdapter(Strategy, ABC):
    """舊版策略適配器基類。

    提供將外部策略庫整合到當前系統的統一框架。
    遵循零修改原則，保持原始策略代碼完全不變。

    子類需要實現：
    - _load_legacy_strategy: 載入原始策略
    - _convert_parameters: 轉換策略參數
    - _execute_legacy_strategy: 執行原始策略
    - _convert_results: 轉換策略結果

    Attributes:
        legacy_strategy: 原始策略實例或函數
        data_converter: 數據格式轉換器
        strategy_wrapper: 策略包裝器
    """

    def __init__(self, name: str = "LegacyStrategy", **parameters: Any) -> None:
        """初始化舊版策略適配器。

        Args:
            name: 策略名稱
            **parameters: 策略參數
        """
        super().__init__(name, **parameters)

        self.legacy_strategy = None
        self.data_converter = DataFormatConverter()
        self.strategy_wrapper = None

        # 載入原始策略
        self._load_legacy_strategy()

        logger.info("舊版策略適配器 %s 初始化完成", name)

    @abstractmethod
    def _load_legacy_strategy(self) -> None:
        """載入原始策略。

        子類必須實現此方法來載入具體的原始策略。
        """

    @abstractmethod
    def _convert_parameters(self, **parameters: Any) -> Dict[str, Any]:
        """轉換策略參數格式。

        Args:
            **parameters: 當前系統參數格式

        Returns:
            原始策略期望的參數格式
        """

    @abstractmethod
    def _execute_legacy_strategy(self, data: pd.DataFrame, **parameters: Any) -> Any:
        """執行原始策略。

        Args:
            data: 輸入數據
            **parameters: 策略參數

        Returns:
            原始策略執行結果
        """

    @abstractmethod
    def _convert_results(self, legacy_results: Any, data: pd.DataFrame) -> pd.DataFrame:
        """轉換策略結果格式。

        Args:
            legacy_results: 原始策略結果
            data: 輸入數據

        Returns:
            當前系統期望的結果格式
        """

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易訊號。

        Args:
            data: 輸入數據

        Returns:
            包含交易訊號的數據框架
        """
        try:
            # 驗證輸入數據
            self._validate_price_data(data)

            # 轉換數據格式
            legacy_data = self.data_converter.convert_to_legacy_format(data)

            # 轉換參數格式
            legacy_parameters = self._convert_parameters(**self.parameters)

            # 執行原始策略
            legacy_results = self._execute_legacy_strategy(legacy_data, **legacy_parameters)

            # 轉換結果格式
            signals = self._convert_results(legacy_results, data)

            # 驗證結果
            self._validate_signals_data(signals)

            logger.debug("策略 %s 成功生成 %d 個訊號", self.name, len(signals))
            return signals

        except Exception as e:
            logger.error("策略 %s 訊號生成失敗: %s", self.name, e)
            raise StrategyExecutionError(
                f"策略 {self.name} 訊號生成失敗: {e}") from e
