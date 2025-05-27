"""基礎訊號產生器

此模組定義了所有訊號產生器的基礎類別和共用功能。
"""

import logging
import warnings
from abc import ABC, abstractmethod
from typing import Dict, Optional

import pandas as pd

# 嘗試導入 indicators 模組
try:
    from src.core.indicators import (
        FundamentalIndicators,
        SentimentIndicators,
        TechnicalIndicators,
    )

    INDICATORS_AVAILABLE = True
except ImportError as e:
    warnings.warn(f"無法匯入 indicators 模組，部分功能將無法使用: {e}")
    INDICATORS_AVAILABLE = False

# 嘗試導入 model_integration 模組
try:
    from src.core.model_integration import ModelManager

    MODEL_INTEGRATION_AVAILABLE = True
except ImportError as e:
    warnings.warn(f"無法匯入 model_integration 模組，AI 模型整合功能將無法使用: {e}")
    MODEL_INTEGRATION_AVAILABLE = False

# 設定日誌
logger = logging.getLogger(__name__)

# 集中管理 log 訊息，方便多語系擴充
LOG_MSGS = {
    "no_financial": "缺少財務資料，無法生成基本面策略訊號",
    "no_price": "缺少價格資料，無法生成{strategy}策略訊號",
    "no_close": "價格資料缺少 'close' 列",
    "no_news": "缺少新聞資料，無法生成新聞情緒策略訊號",
    "no_sentiment": "新聞資料缺少 'sentiment' 列",
    "no_signal": "沒有可用的訊號，請先生成訊號",
    "unknown_strategy": "權重中包含未知的策略",
    "talib_missing": "未安裝 talib，將使用自定義 RSI 計算，建議安裝 talib 以提升效能與準確度。",
    "indicators_missing": "未安裝 indicators 模組，部分功能將無法使用",
    "no_indicators": "缺少指標資料，無法生成訊號",
    "export_error": "匯出訊號時發生錯誤: {error}",
    "model_integration_missing": "未安裝 model_integration 模組，AI 模型整合功能將無法使用",
    "no_model": "缺少模型，無法生成 AI 模型策略訊號",
    "model_error": "使用模型生成訊號時發生錯誤: {error}",
}


class BaseSignalGenerator(ABC):
    """基礎訊號產生器抽象類別

    定義了所有訊號產生器的共用介面和基礎功能。
    """

    def __init__(
        self,
        price_data: Optional[pd.DataFrame] = None,
        volume_data: Optional[pd.DataFrame] = None,
        financial_data: Optional[pd.DataFrame] = None,
        news_data: Optional[pd.DataFrame] = None,
        model_manager=None,
    ):
        """初始化基礎訊號產生器

        Args:
            price_data (pd.DataFrame, optional): 價格資料，索引為 (股票代號, 日期)
            volume_data (pd.DataFrame, optional): 成交量資料，索引為 (股票代號, 日期)
            financial_data (pd.DataFrame, optional): 財務資料，索引為 (股票代號, 日期)
            news_data (pd.DataFrame, optional): 新聞資料，索引為 (股票代號, 日期)
            model_manager (ModelManager, optional): 模型管理器，用於 AI 模型整合
        """
        # 避免不必要的資料複製，使用視圖
        self.price_data = price_data
        self.volume_data = volume_data
        self.financial_data = financial_data
        self.news_data = news_data
        self.model_manager = model_manager

        # 儲存生成的訊號
        self.signals: Dict[str, pd.DataFrame] = {}

        # 初始化指標計算器
        self._initialize_indicators()

    def _initialize_indicators(self):
        """初始化各種指標計算器"""
        self.tech_indicators = None
        self.fund_indicators = None
        self.sent_indicators = None

        if not INDICATORS_AVAILABLE:
            return

        self._initialize_technical_indicators()
        self._initialize_fundamental_indicators()
        self._initialize_sentiment_indicators()

    def _initialize_technical_indicators(self):
        """初始化技術指標計算器"""
        if self.price_data is not None:
            try:
                self.tech_indicators = TechnicalIndicators(self.price_data)
                logger.info("技術指標計算器初始化成功")
            except Exception as e:
                logger.warning("技術指標計算器初始化失敗: %s", e)

    def _initialize_fundamental_indicators(self):
        """初始化基本面指標計算器"""
        if self.financial_data is not None:
            try:
                if isinstance(self.financial_data, dict):
                    self.fund_indicators = FundamentalIndicators(self.financial_data)
                    logger.info("基本面指標計算器初始化成功")
                else:
                    logger.warning("財務資料格式不正確，應為字典格式")
            except Exception as e:
                logger.warning("基本面指標計算器初始化失敗: %s", e)

    def _initialize_sentiment_indicators(self):
        """初始化情緒指標計算器"""
        if self.news_data is not None:
            try:
                if isinstance(self.news_data, dict):
                    self.sent_indicators = SentimentIndicators(self.news_data)
                    logger.info("情緒指標計算器初始化成功")
                else:
                    # 如果是 DataFrame，轉換為字典格式
                    news_dict = {"news": self.news_data}
                    self.sent_indicators = SentimentIndicators(news_dict)
                    logger.info("情緒指標計算器初始化成功（DataFrame 轉換）")
            except Exception as e:
                logger.warning("情緒指標計算器初始化失敗: %s", e)

    @abstractmethod
    def generate_signals(self, **kwargs) -> pd.DataFrame:
        """生成訊號的抽象方法

        子類別必須實現此方法來生成特定類型的訊號。

        Args:
            **kwargs: 策略特定的參數

        Returns:
            pd.DataFrame: 訊號資料，包含 'signal' 列，1 表示買入，-1 表示賣出，0 表示持平
        """
        pass

    def validate_data(self, required_data: str) -> bool:
        """驗證所需資料是否可用

        Args:
            required_data (str): 所需資料類型 ('price', 'financial', 'news', 'volume')

        Returns:
            bool: 資料是否可用
        """
        data_map = {
            "price": self.price_data,
            "financial": self.financial_data,
            "news": self.news_data,
            "volume": self.volume_data,
        }

        data = data_map.get(required_data)
        return data is not None and not data.empty

    def get_signals(self, strategy_name: str) -> Optional[pd.DataFrame]:
        """獲取指定策略的訊號

        Args:
            strategy_name (str): 策略名稱

        Returns:
            pd.DataFrame: 訊號資料，如果不存在則返回 None
        """
        return self.signals.get(strategy_name)

    def clear_signals(self):
        """清除所有已生成的訊號"""
        self.signals.clear()

    def list_available_signals(self) -> list:
        """列出所有可用的訊號策略

        Returns:
            list: 策略名稱列表
        """
        return list(self.signals.keys())

    def export_signals(self, file_path: str, strategy_name: Optional[str] = None):
        """匯出訊號到檔案

        Args:
            file_path (str): 檔案路徑
            strategy_name (str, optional): 策略名稱，如果為 None 則匯出所有訊號
        """
        try:
            if strategy_name:
                if strategy_name in self.signals:
                    self.signals[strategy_name].to_csv(file_path)
                else:
                    logger.warning("策略 '%s' 不存在", strategy_name)
            else:
                # 匯出所有訊號
                all_signals = pd.concat(self.signals.values(), keys=self.signals.keys())
                all_signals.to_csv(file_path)
            logger.info("訊號已匯出到: %s", file_path)
        except Exception as e:
            logger.error(LOG_MSGS["export_error"].format(error=str(e)))
