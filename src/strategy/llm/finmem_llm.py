# -*- coding: utf-8 -*-
"""
FinMem-LLM策略模組

此模組實現基於FinMem-LLM的交易策略，結合新聞數據和歷史價格進行股票預測。

主要功能：
- 新聞數據處理和格式化
- 基於Qwen模型的股票預測
- 支持thinking模式的推理
- 置信度評估和信號生成
"""

import logging
import re
from typing import Dict, Any, Optional, List
import pandas as pd
from datetime import datetime, timedelta

from .base import LLMStrategy, LLMStrategyError

# 設定日誌
logger = logging.getLogger(__name__)


class FinMemLLMStrategy(LLMStrategy):
    """
    FinMem-LLM策略。

    基於FinMem-LLM模型進行股票預測，結合過去5個交易日的新聞數據
    和歷史價格資訊，生成買入/賣出信號。

    Attributes:
        news_days (int): 分析的新聞天數
        enable_thinking (bool): 是否啟用thinking模式
        max_news_per_day (int): 每日最大新聞數量

    Example:
        >>> strategy = FinMemLLMStrategy(
        ...     llm_config={'model_name': 'qwen', 'api_key': 'xxx'},
        ...     news_days=5,
        ...     enable_thinking=True
        ... )
        >>> signals = strategy.generate_signals(data)
    """

    def __init__(
        self,
        name: str = "FinMem-LLM策略",
        llm_config: Optional[Dict[str, Any]] = None,
        confidence_threshold: float = 0.6,
        news_days: int = 5,
        enable_thinking: bool = True,
        max_news_per_day: int = 30,
        **parameters: Any
    ) -> None:
        """初始化FinMem-LLM策略。

        Args:
            name: 策略名稱
            llm_config: LLM配置
            confidence_threshold: 決策置信度閾值
            news_days: 分析的新聞天數
            enable_thinking: 是否啟用thinking模式
            max_news_per_day: 每日最大新聞數量
            **parameters: 其他參數
        """
        super().__init__(name, llm_config, confidence_threshold, **parameters)
        
        self.news_days = news_days
        self.enable_thinking = enable_thinking
        self.max_news_per_day = max_news_per_day

    def _prepare_llm_input(self, data: pd.DataFrame) -> str:
        """準備FinMem-LLM的輸入數據。

        Args:
            data: 包含價格和新聞數據的DataFrame

        Returns:
            格式化的LLM輸入字符串

        Raises:
            LLMStrategyError: 當數據格式不正確時
        """
        try:
            # 獲取股票代碼和當前日期
            stock_code = data.get('stock_code', ['未知'])[0] if 'stock_code' in data.columns else '未知'
            current_date = data.index[-1].strftime('%Y-%m-%d') if len(data) > 0 else datetime.now().strftime('%Y-%m-%d')
            
            # 構建新聞部分
            news_section = self._format_news_data(data, stock_code, current_date)
            
            # 構建任務部分
            task_section = self._get_task_prompt()
            
            # 組合完整輸入
            full_input = f"###新聞###\n{news_section}\n\n###任務###\n{task_section}"
            
            logger.info(f"準備LLM輸入完成，股票: {stock_code}, 日期: {current_date}")
            return full_input
            
        except Exception as e:
            logger.error(f"準備LLM輸入失敗: {e}")
            raise LLMStrategyError(f"準備LLM輸入失敗: {e}") from e

    def _format_news_data(self, data: pd.DataFrame, stock_code: str, current_date: str) -> str:
        """格式化新聞數據。

        Args:
            data: 原始數據
            stock_code: 股票代碼
            current_date: 當前日期

        Returns:
            格式化的新聞字符串
        """
        news_lines = [f"Date:{current_date}, Stock:{stock_code},過去五日的新聞為:"]
        
        # 獲取過去5個交易日的新聞
        end_date = pd.to_datetime(current_date)
        
        for i in range(self.news_days):
            date = end_date - timedelta(days=i+1)
            date_str = date.strftime('%Y-%m-%d')
            
            # 獲取該日期的新聞
            day_news = self._get_news_for_date(data, date_str)
            
            if day_news:
                # 限制每日新聞數量
                if len(day_news) > self.max_news_per_day:
                    day_news = day_news[:self.max_news_per_day]
                
                news_text = ".".join([f"NEWS{j+1}: {news}" for j, news in enumerate(day_news)])
                news_lines.append(f"{date_str}: {news_text}.")
            else:
                news_lines.append(f"{date_str}: nan")
        
        return "\n".join(news_lines)

    def _get_news_for_date(self, data: pd.DataFrame, date_str: str) -> List[str]:
        """獲取指定日期的新聞。

        Args:
            data: 數據DataFrame
            date_str: 日期字符串

        Returns:
            該日期的新聞列表
        """
        # 如果數據中有新聞欄位，提取對應日期的新聞
        if 'news' in data.columns:
            date_mask = data.index.strftime('%Y-%m-%d') == date_str
            if date_mask.any():
                news_data = data.loc[date_mask, 'news'].iloc[0]
                if isinstance(news_data, str) and news_data.strip():
                    return [news_data]
                elif isinstance(news_data, list):
                    return news_data
        
        # 如果沒有新聞數據，返回空列表
        return []

    def _get_task_prompt(self) -> str:
        """獲取任務提示詞。

        Returns:
            任務提示字符串
        """
        return ("請根據過去五個交易日內關於該股票的新聞，預測下一個交易日該股票的漲跌，"
                "如果預測下一個交易日該股票會漲，請輸出[上漲]，"
                "如果預測下一個交易日該股票會跌，請輸出[下跌]")

    def _parse_llm_output(self, llm_output: str) -> Dict[str, Any]:
        """解析FinMem-LLM的輸出。

        Args:
            llm_output: LLM原始輸出

        Returns:
            解析結果字典

        Raises:
            LLMStrategyError: 當解析失敗時
        """
        try:
            result = {
                'prediction': '持平',
                'confidence': 0.0,
                'reasoning': '',
                'raw_output': llm_output
            }
            
            # 提取thinking內容（如果存在）
            thinking_content = ""
            if self.enable_thinking:
                thinking_match = re.search(r'<think>(.*?)</think>', llm_output, re.DOTALL)
                if thinking_match:
                    thinking_content = thinking_match.group(1).strip()
                    result['reasoning'] = thinking_content
            
            # 提取最終預測結果
            prediction = self._extract_prediction(llm_output)
            result['prediction'] = prediction
            
            # 計算置信度
            confidence = self._calculate_confidence(llm_output, thinking_content)
            result['confidence'] = confidence
            
            logger.info(f"LLM輸出解析完成: 預測={prediction}, 置信度={confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"解析LLM輸出失敗: {e}")
            raise LLMStrategyError(f"解析LLM輸出失敗: {e}") from e

    def _extract_prediction(self, output: str) -> str:
        """提取預測結果。

        Args:
            output: LLM輸出

        Returns:
            預測結果 ('上漲', '下跌', '持平')
        """
        # 查找[上漲]或[下跌]標籤
        if '[上漲]' in output or '上漲' in output:
            return '上漲'
        elif '[下跌]' in output or '下跌' in output:
            return '下跌'
        else:
            return '持平'

    def _calculate_confidence(self, output: str, thinking: str) -> float:
        """計算預測置信度。

        Args:
            output: LLM完整輸出
            thinking: thinking內容

        Returns:
            置信度分數 (0-1)
        """
        confidence = 0.5  # 基礎置信度
        
        # 基於thinking內容的長度和詳細程度調整置信度
        if thinking:
            thinking_length = len(thinking)
            if thinking_length > 500:
                confidence += 0.2
            elif thinking_length > 200:
                confidence += 0.1
        
        # 基於輸出中的確定性詞彙調整置信度
        certainty_words = ['明顯', '確定', '強烈', '顯著', '清楚']
        uncertainty_words = ['可能', '或許', '不確定', '難以判斷']
        
        for word in certainty_words:
            if word in output:
                confidence += 0.1
                
        for word in uncertainty_words:
            if word in output:
                confidence -= 0.1
        
        # 確保置信度在合理範圍內
        return max(0.0, min(1.0, confidence))

    def get_strategy_info(self) -> Dict[str, Any]:
        """獲取策略資訊。

        Returns:
            策略資訊字典
        """
        info = super().get_strategy_info()
        info.update({
            'strategy_type': 'FinMem-LLM',
            'news_days': self.news_days,
            'enable_thinking': self.enable_thinking,
            'max_news_per_day': self.max_news_per_day
        })
        return info
