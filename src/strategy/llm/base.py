# -*- coding: utf-8 -*-
"""
LLM策略基礎模組

此模組定義了所有LLM交易策略的基礎類別和共用功能。

主要功能：
- 定義LLM策略基類 LLMStrategy
- 提供LLM模型調用的通用方法
- 定義LLM策略異常類別
- 提供LLM策略參數驗證功能
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
import pandas as pd
from datetime import datetime

from ..base import Strategy, StrategyError

# 設定日誌
logger = logging.getLogger(__name__)


class LLMStrategyError(StrategyError):
    """LLM策略相關錯誤基類"""


class LLMConfigError(LLMStrategyError):
    """LLM配置錯誤"""


class LLMStrategy(Strategy):
    """LLM策略基類，所有LLM策略都應該繼承此類。

    此類定義了LLM策略的基本介面和通用功能，包括：
    - LLM模型調用
    - 新聞數據處理
    - 情緒分析
    - 決策置信度計算

    Attributes:
        name (str): 策略名稱
        parameters (Dict[str, Any]): 策略參數
        llm_config (Dict[str, Any]): LLM配置
        confidence_threshold (float): 決策置信度閾值
    """

    def __init__(
        self, 
        name: str = "BaseLLMStrategy", 
        llm_config: Optional[Dict[str, Any]] = None,
        confidence_threshold: float = 0.6,
        **parameters: Any
    ) -> None:
        """初始化LLM策略。

        Args:
            name: 策略名稱
            llm_config: LLM配置字典，包含模型名稱、API金鑰等
            confidence_threshold: 決策置信度閾值
            **parameters: 其他策略參數

        Raises:
            LLMConfigError: 當LLM配置不正確時
        """
        super().__init__(name, **parameters)
        
        self.llm_config = llm_config or {}
        self.confidence_threshold = confidence_threshold
        
        # 驗證LLM配置
        self._validate_llm_config()
        
        # 初始化LLM連接器
        self._llm_connector = None
        self._initialize_llm_connector()

    def _validate_llm_config(self) -> None:
        """驗證LLM配置。

        Raises:
            LLMConfigError: 當配置不正確時
        """
        required_keys = ['model_name', 'api_key']
        for key in required_keys:
            if key not in self.llm_config:
                raise LLMConfigError(f"缺少必要的LLM配置項: {key}")

    def _initialize_llm_connector(self) -> None:
        """初始化LLM連接器。"""
        try:
            # 這裡將在後續實現LLM連接器後進行整合
            logger.info(f"初始化LLM連接器: {self.llm_config.get('model_name', 'unknown')}")
        except Exception as e:
            logger.error(f"初始化LLM連接器失敗: {e}")
            raise LLMConfigError(f"無法初始化LLM連接器: {e}") from e

    @abstractmethod
    def _prepare_llm_input(self, data: pd.DataFrame) -> str:
        """準備LLM輸入數據。

        Args:
            data: 輸入資料，包含價格、新聞等資訊

        Returns:
            格式化的LLM輸入字符串

        Raises:
            NotImplementedError: 子類必須實現此方法
        """

    @abstractmethod
    def _parse_llm_output(self, llm_output: str) -> Dict[str, Any]:
        """解析LLM輸出。

        Args:
            llm_output: LLM的原始輸出

        Returns:
            解析後的結果字典，包含：
            - prediction: 預測結果 ('上漲', '下跌', '持平')
            - confidence: 置信度 (0-1)
            - reasoning: 推理過程
            - signals: 交易信號

        Raises:
            NotImplementedError: 子類必須實現此方法
        """

    def _call_llm(self, input_text: str) -> str:
        """調用LLM進行推理。

        Args:
            input_text: 輸入文本

        Returns:
            LLM輸出文本

        Raises:
            LLMStrategyError: 當LLM調用失敗時
        """
        try:
            # 這裡將在LLM連接器實現後進行整合
            logger.info(f"調用LLM進行推理，輸入長度: {len(input_text)}")
            
            # 暫時返回模擬輸出
            return "模擬LLM輸出：基於輸入數據分析，預測股價上漲，置信度0.75"
            
        except Exception as e:
            logger.error(f"LLM調用失敗: {e}")
            raise LLMStrategyError(f"LLM調用失敗: {e}") from e

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易訊號。

        Args:
            data: 輸入資料，包含價格、新聞等資訊

        Returns:
            包含交易訊號的資料框架，包含：
            - signal: 主要訊號 (1=買入, -1=賣出, 0=觀望)
            - buy_signal: 買入訊號 (1=買入, 0=無動作)
            - sell_signal: 賣出訊號 (1=賣出, 0=無動作)
            - confidence: 決策置信度
            - reasoning: LLM推理過程

        Raises:
            LLMStrategyError: 當策略執行失敗時
        """
        try:
            # 驗證輸入資料
            self._validate_price_data(data)
            
            # 準備LLM輸入
            llm_input = self._prepare_llm_input(data)
            
            # 調用LLM
            llm_output = self._call_llm(llm_input)
            
            # 解析LLM輸出
            parsed_result = self._parse_llm_output(llm_output)
            
            # 生成交易信號
            signals = self._generate_trading_signals(data, parsed_result)
            
            return signals
            
        except Exception as e:
            logger.error(f"生成交易訊號失敗: {e}")
            raise LLMStrategyError(f"生成交易訊號失敗: {e}") from e

    def _generate_trading_signals(
        self, 
        data: pd.DataFrame, 
        parsed_result: Dict[str, Any]
    ) -> pd.DataFrame:
        """根據LLM分析結果生成交易信號。

        Args:
            data: 原始數據
            parsed_result: LLM解析結果

        Returns:
            包含交易信號的DataFrame
        """
        signals = pd.DataFrame(index=data.index)
        
        # 提取預測結果和置信度
        prediction = parsed_result.get('prediction', '持平')
        confidence = parsed_result.get('confidence', 0.0)
        reasoning = parsed_result.get('reasoning', '')
        
        # 根據置信度和預測結果生成信號
        if confidence >= self.confidence_threshold:
            if prediction == '上漲':
                signal = 1
                buy_signal = 1
                sell_signal = 0
            elif prediction == '下跌':
                signal = -1
                buy_signal = 0
                sell_signal = 1
            else:
                signal = 0
                buy_signal = 0
                sell_signal = 0
        else:
            # 置信度不足，保持觀望
            signal = 0
            buy_signal = 0
            sell_signal = 0
        
        # 填充信號數據
        signals['signal'] = signal
        signals['buy_signal'] = buy_signal
        signals['sell_signal'] = sell_signal
        signals['confidence'] = confidence
        signals['reasoning'] = reasoning
        signals['prediction'] = prediction
        
        return signals

    def get_strategy_info(self) -> Dict[str, Any]:
        """獲取策略資訊。

        Returns:
            策略資訊字典
        """
        return {
            'name': self.name,
            'type': 'LLM策略',
            'model': self.llm_config.get('model_name', 'unknown'),
            'confidence_threshold': self.confidence_threshold,
            'parameters': self.parameters
        }
