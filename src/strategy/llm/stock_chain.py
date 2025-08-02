# -*- coding: utf-8 -*-
"""
Stock-chain策略模組

此模組實現基於Stock-chain的交易策略，結合網路搜索、新聞分析和技術指標。

主要功能：
- 網路搜索和熱點話題分析
- 新聞情緒分析
- 技術指標整合
- 多維度決策融合
"""

import logging
from typing import Dict, Any, Optional, List
import pandas as pd
from datetime import datetime

from .base import LLMStrategy, LLMStrategyError

# 設定日誌
logger = logging.getLogger(__name__)


class StockChainStrategy(LLMStrategy):
    """
    Stock-chain策略。

    基於Stock-chain框架進行多維度分析，包括：
    - 網路熱點話題搜索
    - 新聞情緒分析
    - 技術指標分析
    - 多源信息融合決策

    Attributes:
        enable_web_search (bool): 是否啟用網路搜索
        search_topics (List[str]): 搜索主題列表
        sentiment_weight (float): 情緒分析權重
        technical_weight (float): 技術指標權重

    Example:
        >>> strategy = StockChainStrategy(
        ...     llm_config={'model_name': 'qwen', 'api_key': 'xxx'},
        ...     enable_web_search=True,
        ...     search_topics=['人工智能', '新能源']
        ... )
        >>> signals = strategy.generate_signals(data)
    """

    def __init__(
        self,
        name: str = "Stock-chain策略",
        llm_config: Optional[Dict[str, Any]] = None,
        confidence_threshold: float = 0.65,
        enable_web_search: bool = True,
        search_topics: Optional[List[str]] = None,
        sentiment_weight: float = 0.4,
        technical_weight: float = 0.3,
        news_weight: float = 0.3,
        **parameters: Any
    ) -> None:
        """初始化Stock-chain策略。

        Args:
            name: 策略名稱
            llm_config: LLM配置
            confidence_threshold: 決策置信度閾值
            enable_web_search: 是否啟用網路搜索
            search_topics: 搜索主題列表
            sentiment_weight: 情緒分析權重
            technical_weight: 技術指標權重
            news_weight: 新聞分析權重
            **parameters: 其他參數
        """
        super().__init__(name, llm_config, confidence_threshold, **parameters)
        
        self.enable_web_search = enable_web_search
        self.search_topics = search_topics or ['股市行情', '經濟政策', '行業動態']
        self.sentiment_weight = sentiment_weight
        self.technical_weight = technical_weight
        self.news_weight = news_weight
        
        # 驗證權重總和
        total_weight = sentiment_weight + technical_weight + news_weight
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"權重總和不為1.0: {total_weight}, 將自動標準化")
            self.sentiment_weight /= total_weight
            self.technical_weight /= total_weight
            self.news_weight /= total_weight

    def _prepare_llm_input(self, data: pd.DataFrame) -> str:
        """準備Stock-chain的輸入數據。

        Args:
            data: 包含價格、新聞和技術指標的DataFrame

        Returns:
            格式化的LLM輸入字符串

        Raises:
            LLMStrategyError: 當數據格式不正確時
        """
        try:
            # 獲取基本信息
            stock_code = data.get('stock_code', ['未知'])[0] if 'stock_code' in data.columns else '未知'
            current_date = data.index[-1].strftime('%Y-%m-%d') if len(data) > 0 else datetime.now().strftime('%Y-%m-%d')
            
            # 構建各個分析部分
            sections = []
            
            # 1. 熱點話題分析
            if self.enable_web_search:
                hot_topics_section = self._format_hot_topics(stock_code)
                sections.append(f"###熱點話題###\n{hot_topics_section}")
            
            # 2. 新聞分析
            news_section = self._format_news_analysis(data, stock_code)
            sections.append(f"###新聞分析###\n{news_section}")
            
            # 3. 技術指標分析
            technical_section = self._format_technical_analysis(data)
            sections.append(f"###技術指標###\n{technical_section}")
            
            # 4. 任務說明
            task_section = self._get_stock_chain_task_prompt(stock_code)
            sections.append(f"###分析任務###\n{task_section}")
            
            full_input = "\n\n".join(sections)
            
            logger.info(f"準備Stock-chain輸入完成，股票: {stock_code}")
            return full_input
            
        except Exception as e:
            logger.error(f"準備Stock-chain輸入失敗: {e}")
            raise LLMStrategyError(f"準備Stock-chain輸入失敗: {e}") from e

    def _format_hot_topics(self, stock_code: str) -> str:
        """格式化熱點話題數據。

        Args:
            stock_code: 股票代碼

        Returns:
            格式化的熱點話題字符串
        """
        # 模擬熱點話題數據（實際實現中會調用搜索API）
        topics_data = []
        
        for topic in self.search_topics:
            # 這裡將在實際實現中調用網路搜索API
            topic_info = f"關於{topic}的最新動態：相關政策利好，市場關注度較高"
            topics_data.append(f"- {topic}: {topic_info}")
        
        return "\n".join(topics_data)

    def _format_news_analysis(self, data: pd.DataFrame, stock_code: str) -> str:
        """格式化新聞分析數據。

        Args:
            data: 原始數據
            stock_code: 股票代碼

        Returns:
            格式化的新聞分析字符串
        """
        news_lines = [f"股票 {stock_code} 近期新聞分析："]
        
        # 獲取新聞數據
        if 'news' in data.columns:
            recent_news = data['news'].dropna().tail(5)  # 最近5條新聞
            
            for i, news in enumerate(recent_news, 1):
                # 簡單的情緒分析（實際實現中會使用更複雜的NLP模型）
                sentiment = self._analyze_sentiment(str(news))
                news_lines.append(f"{i}. {news[:100]}... (情緒: {sentiment})")
        else:
            news_lines.append("暫無新聞數據")
        
        return "\n".join(news_lines)

    def _analyze_sentiment(self, text: str) -> str:
        """簡單的情緒分析。

        Args:
            text: 文本內容

        Returns:
            情緒標籤 ('正面', '負面', '中性')
        """
        # 簡單的關鍵詞情緒分析
        positive_words = ['上漲', '利好', '增長', '突破', '創新', '合作', '收購']
        negative_words = ['下跌', '利空', '下降', '虧損', '風險', '調查', '處罰']
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return '正面'
        elif negative_count > positive_count:
            return '負面'
        else:
            return '中性'

    def _format_technical_analysis(self, data: pd.DataFrame) -> str:
        """格式化技術指標分析。

        Args:
            data: 包含技術指標的數據

        Returns:
            格式化的技術分析字符串
        """
        tech_lines = ["技術指標分析："]
        
        if len(data) > 0:
            latest_data = data.iloc[-1]
            
            # 價格趨勢
            if '收盤價' in data.columns and len(data) >= 5:
                recent_prices = data['收盤價'].tail(5)
                price_trend = "上升" if recent_prices.iloc[-1] > recent_prices.iloc[0] else "下降"
                tech_lines.append(f"- 價格趨勢: {price_trend}")
            
            # 移動平均線
            if 'MA5' in latest_data and 'MA20' in latest_data:
                ma_signal = "多頭排列" if latest_data['MA5'] > latest_data['MA20'] else "空頭排列"
                tech_lines.append(f"- 移動平均線: {ma_signal}")
            
            # RSI指標
            if 'RSI' in latest_data:
                rsi_value = latest_data['RSI']
                if rsi_value > 70:
                    rsi_signal = "超買"
                elif rsi_value < 30:
                    rsi_signal = "超賣"
                else:
                    rsi_signal = "正常"
                tech_lines.append(f"- RSI指標: {rsi_value:.2f} ({rsi_signal})")
            
            # 成交量
            if '成交量' in data.columns and len(data) >= 2:
                volume_change = (data['成交量'].iloc[-1] / data['成交量'].iloc[-2] - 1) * 100
                volume_trend = "放量" if volume_change > 20 else "縮量" if volume_change < -20 else "平量"
                tech_lines.append(f"- 成交量: {volume_trend} ({volume_change:+.1f}%)")
        else:
            tech_lines.append("暫無技術指標數據")
        
        return "\n".join(tech_lines)

    def _get_stock_chain_task_prompt(self, stock_code: str) -> str:
        """獲取Stock-chain任務提示詞。

        Args:
            stock_code: 股票代碼

        Returns:
            任務提示字符串
        """
        return f"""請基於以上多維度分析信息，對股票 {stock_code} 進行綜合評估：

1. 分析各個維度的影響因素
2. 評估整體市場情緒和技術面
3. 給出明確的投資建議：[買入]、[賣出]或[持有]
4. 提供決策的置信度評分（0-100分）
5. 說明主要的風險因素

請以結構化的方式回答，包含推理過程和最終結論。"""

    def _parse_llm_output(self, llm_output: str) -> Dict[str, Any]:
        """解析Stock-chain的輸出。

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
                'reasoning': llm_output,
                'raw_output': llm_output,
                'risk_factors': []
            }
            
            # 提取投資建議
            prediction = self._extract_stock_chain_prediction(llm_output)
            result['prediction'] = prediction
            
            # 提取置信度
            confidence = self._extract_confidence_score(llm_output)
            result['confidence'] = confidence
            
            # 提取風險因素
            risk_factors = self._extract_risk_factors(llm_output)
            result['risk_factors'] = risk_factors
            
            logger.info(f"Stock-chain輸出解析完成: 建議={prediction}, 置信度={confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"解析Stock-chain輸出失敗: {e}")
            raise LLMStrategyError(f"解析Stock-chain輸出失敗: {e}") from e

    def _extract_stock_chain_prediction(self, output: str) -> str:
        """提取Stock-chain預測結果。

        Args:
            output: LLM輸出

        Returns:
            預測結果 ('上漲', '下跌', '持平')
        """
        if '[買入]' in output or '買入' in output:
            return '上漲'
        elif '[賣出]' in output or '賣出' in output:
            return '下跌'
        elif '[持有]' in output or '持有' in output:
            return '持平'
        else:
            # 嘗試其他關鍵詞
            if '看好' in output or '推薦' in output:
                return '上漲'
            elif '看空' in output or '避免' in output:
                return '下跌'
            else:
                return '持平'

    def _extract_confidence_score(self, output: str) -> float:
        """提取置信度分數。

        Args:
            output: LLM輸出

        Returns:
            置信度分數 (0-1)
        """
        import re
        
        # 查找置信度相關的數字
        confidence_patterns = [
            r'置信度[：:]?\s*(\d+)分',
            r'置信度[：:]?\s*(\d+)%',
            r'信心指數[：:]?\s*(\d+)',
            r'確定性[：:]?\s*(\d+)%'
        ]
        
        for pattern in confidence_patterns:
            match = re.search(pattern, output)
            if match:
                score = float(match.group(1))
                return min(score / 100.0, 1.0)  # 轉換為0-1範圍
        
        # 如果沒有找到明確的置信度，基於文本內容估算
        return self._estimate_confidence_from_text(output)

    def _estimate_confidence_from_text(self, text: str) -> float:
        """基於文本內容估算置信度。

        Args:
            text: 文本內容

        Returns:
            估算的置信度
        """
        high_confidence_words = ['強烈', '明確', '確定', '顯著', '明顯']
        low_confidence_words = ['可能', '或許', '不確定', '謹慎', '風險']
        
        high_count = sum(1 for word in high_confidence_words if word in text)
        low_count = sum(1 for word in low_confidence_words if word in text)
        
        base_confidence = 0.6
        confidence_adjustment = (high_count - low_count) * 0.1
        
        return max(0.0, min(1.0, base_confidence + confidence_adjustment))

    def _extract_risk_factors(self, output: str) -> List[str]:
        """提取風險因素。

        Args:
            output: LLM輸出

        Returns:
            風險因素列表
        """
        risk_factors = []
        
        # 查找風險相關的段落
        risk_keywords = ['風險', '注意', '警告', '不確定性', '挑戰']
        
        lines = output.split('\n')
        for line in lines:
            if any(keyword in line for keyword in risk_keywords):
                risk_factors.append(line.strip())
        
        return risk_factors

    def get_strategy_info(self) -> Dict[str, Any]:
        """獲取策略資訊。

        Returns:
            策略資訊字典
        """
        info = super().get_strategy_info()
        info.update({
            'strategy_type': 'Stock-chain',
            'enable_web_search': self.enable_web_search,
            'search_topics': self.search_topics,
            'sentiment_weight': self.sentiment_weight,
            'technical_weight': self.technical_weight,
            'news_weight': self.news_weight
        })
        return info
