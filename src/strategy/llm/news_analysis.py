# -*- coding: utf-8 -*-
"""
新聞分析策略模組

此模組實現基於新聞分析的交易策略，專注於新聞情緒分析和事件驅動交易。

主要功能：
- 新聞情緒分析
- 事件影響評估
- 新聞重要性評分
- 時間衰減模型
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
from datetime import datetime, timedelta

from .base import LLMStrategy, LLMStrategyError

# 設定日誌
logger = logging.getLogger(__name__)


class NewsAnalysisStrategy(LLMStrategy):
    """
    新聞分析策略。

    專注於新聞數據的深度分析，包括：
    - 新聞情緒分析
    - 事件重要性評估
    - 時間衰減效應
    - 多新聞源整合

    Attributes:
        sentiment_threshold (float): 情緒閾值
        importance_threshold (float): 重要性閾值
        time_decay_factor (float): 時間衰減因子
        max_news_count (int): 最大新聞數量

    Example:
        >>> strategy = NewsAnalysisStrategy(
        ...     llm_config={'model_name': 'qwen', 'api_key': 'xxx'},
        ...     sentiment_threshold=0.6,
        ...     importance_threshold=0.7
        ... )
        >>> signals = strategy.generate_signals(data)
    """

    def __init__(
        self,
        name: str = "新聞分析策略",
        llm_config: Optional[Dict[str, Any]] = None,
        confidence_threshold: float = 0.65,
        sentiment_threshold: float = 0.6,
        importance_threshold: float = 0.7,
        time_decay_factor: float = 0.1,
        max_news_count: int = 20,
        **parameters: Any
    ) -> None:
        """初始化新聞分析策略。

        Args:
            name: 策略名稱
            llm_config: LLM配置
            confidence_threshold: 決策置信度閾值
            sentiment_threshold: 情緒閾值
            importance_threshold: 重要性閾值
            time_decay_factor: 時間衰減因子
            max_news_count: 最大新聞數量
            **parameters: 其他參數
        """
        super().__init__(name, llm_config, confidence_threshold, **parameters)
        
        self.sentiment_threshold = sentiment_threshold
        self.importance_threshold = importance_threshold
        self.time_decay_factor = time_decay_factor
        self.max_news_count = max_news_count

    def _prepare_llm_input(self, data: pd.DataFrame) -> str:
        """準備新聞分析的輸入數據。

        Args:
            data: 包含新聞數據的DataFrame

        Returns:
            格式化的LLM輸入字符串

        Raises:
            LLMStrategyError: 當數據格式不正確時
        """
        try:
            # 獲取基本信息
            stock_code = data.get('stock_code', ['未知'])[0] if 'stock_code' in data.columns else '未知'
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            # 處理新聞數據
            news_analysis = self._analyze_news_data(data, stock_code)
            
            # 構建輸入
            sections = [
                f"###股票信息###",
                f"股票代碼: {stock_code}",
                f"分析日期: {current_date}",
                "",
                f"###新聞分析###",
                news_analysis,
                "",
                f"###分析任務###",
                self._get_news_analysis_task_prompt()
            ]
            
            full_input = "\n".join(sections)
            
            logger.info(f"準備新聞分析輸入完成，股票: {stock_code}")
            return full_input
            
        except Exception as e:
            logger.error(f"準備新聞分析輸入失敗: {e}")
            raise LLMStrategyError(f"準備新聞分析輸入失敗: {e}") from e

    def _analyze_news_data(self, data: pd.DataFrame, stock_code: str) -> str:
        """分析新聞數據。

        Args:
            data: 原始數據
            stock_code: 股票代碼

        Returns:
            新聞分析結果字符串
        """
        analysis_lines = []
        
        if 'news' not in data.columns:
            return "暫無新聞數據可供分析"
        
        # 獲取新聞數據
        news_data = self._extract_news_with_timestamps(data)
        
        if not news_data:
            return "暫無有效新聞數據"
        
        # 限制新聞數量
        if len(news_data) > self.max_news_count:
            news_data = news_data[:self.max_news_count]
        
        analysis_lines.append(f"共分析 {len(news_data)} 條新聞：")
        analysis_lines.append("")
        
        # 分析每條新聞
        total_sentiment_score = 0
        total_importance_score = 0
        
        for i, (timestamp, news_text) in enumerate(news_data, 1):
            # 計算時間權重
            time_weight = self._calculate_time_weight(timestamp)
            
            # 分析新聞情緒和重要性
            sentiment_score = self._analyze_news_sentiment(news_text)
            importance_score = self._analyze_news_importance(news_text, stock_code)
            
            # 應用時間權重
            weighted_sentiment = sentiment_score * time_weight
            weighted_importance = importance_score * time_weight
            
            total_sentiment_score += weighted_sentiment
            total_importance_score += weighted_importance
            
            # 格式化新聞分析結果
            analysis_lines.append(f"新聞 {i}:")
            analysis_lines.append(f"時間: {timestamp}")
            analysis_lines.append(f"內容: {news_text[:150]}...")
            analysis_lines.append(f"情緒分數: {sentiment_score:.2f} (權重後: {weighted_sentiment:.2f})")
            analysis_lines.append(f"重要性: {importance_score:.2f} (權重後: {weighted_importance:.2f})")
            analysis_lines.append("")
        
        # 計算總體分數
        avg_sentiment = total_sentiment_score / len(news_data)
        avg_importance = total_importance_score / len(news_data)
        
        analysis_lines.append("###總體分析###")
        analysis_lines.append(f"平均情緒分數: {avg_sentiment:.2f}")
        analysis_lines.append(f"平均重要性分數: {avg_importance:.2f}")
        analysis_lines.append(f"情緒趨勢: {self._get_sentiment_trend(avg_sentiment)}")
        analysis_lines.append(f"重要性評級: {self._get_importance_level(avg_importance)}")
        
        return "\n".join(analysis_lines)

    def _extract_news_with_timestamps(self, data: pd.DataFrame) -> List[Tuple[str, str]]:
        """提取帶時間戳的新聞數據。

        Args:
            data: 原始數據

        Returns:
            (時間戳, 新聞內容) 的列表
        """
        news_list = []
        
        for idx, row in data.iterrows():
            if pd.notna(row.get('news')):
                timestamp = idx.strftime('%Y-%m-%d %H:%M:%S') if hasattr(idx, 'strftime') else str(idx)
                news_text = str(row['news'])
                if news_text.strip():
                    news_list.append((timestamp, news_text))
        
        # 按時間排序（最新的在前）
        news_list.sort(key=lambda x: x[0], reverse=True)
        
        return news_list

    def _calculate_time_weight(self, timestamp: str) -> float:
        """計算時間權重。

        Args:
            timestamp: 時間戳字符串

        Returns:
            時間權重 (0-1)
        """
        try:
            # 解析時間戳
            if len(timestamp) > 10:
                news_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            else:
                news_time = datetime.strptime(timestamp, '%Y-%m-%d')
            
            # 計算時間差（天數）
            current_time = datetime.now()
            time_diff = (current_time - news_time).days
            
            # 應用指數衰減
            weight = max(0.1, 1.0 * (1 - self.time_decay_factor) ** time_diff)
            
            return weight
            
        except Exception:
            # 如果時間解析失敗，返回默認權重
            return 0.5

    def _analyze_news_sentiment(self, news_text: str) -> float:
        """分析新聞情緒。

        Args:
            news_text: 新聞文本

        Returns:
            情緒分數 (-1到1，負數表示負面，正數表示正面)
        """
        # 定義情緒關鍵詞
        positive_keywords = [
            '上漲', '增長', '利好', '突破', '創新', '合作', '收購', '擴張',
            '盈利', '成功', '優秀', '領先', '強勁', '看好', '推薦', '買入'
        ]
        
        negative_keywords = [
            '下跌', '下降', '利空', '虧損', '風險', '警告', '調查', '處罰',
            '困難', '挑戰', '減少', '衰退', '看空', '賣出', '避免', '謹慎'
        ]
        
        # 計算正負面詞彙出現次數
        positive_count = sum(1 for keyword in positive_keywords if keyword in news_text)
        negative_count = sum(1 for keyword in negative_keywords if keyword in news_text)
        
        # 計算情緒分數
        total_count = positive_count + negative_count
        if total_count == 0:
            return 0.0  # 中性
        
        sentiment_score = (positive_count - negative_count) / total_count
        
        # 標準化到-1到1範圍
        return max(-1.0, min(1.0, sentiment_score))

    def _analyze_news_importance(self, news_text: str, stock_code: str) -> float:
        """分析新聞重要性。

        Args:
            news_text: 新聞文本
            stock_code: 股票代碼

        Returns:
            重要性分數 (0-1)
        """
        importance_score = 0.0
        
        # 基礎重要性
        importance_score += 0.3
        
        # 如果新聞直接提到股票代碼或公司名稱
        if stock_code in news_text:
            importance_score += 0.3
        
        # 重要事件關鍵詞
        important_keywords = [
            '財報', '業績', '收購', '合併', '重組', 'IPO', '分紅', '配股',
            '監管', '政策', '法規', '批准', '許可', '合作', '協議', '投資'
        ]
        
        for keyword in important_keywords:
            if keyword in news_text:
                importance_score += 0.1
        
        # 數字和百分比增加重要性
        import re
        if re.search(r'\d+%', news_text) or re.search(r'\d+億', news_text):
            importance_score += 0.1
        
        # 標準化到0-1範圍
        return min(1.0, importance_score)

    def _get_sentiment_trend(self, sentiment_score: float) -> str:
        """獲取情緒趨勢描述。

        Args:
            sentiment_score: 情緒分數

        Returns:
            情緒趨勢描述
        """
        if sentiment_score > 0.3:
            return "積極正面"
        elif sentiment_score > 0.1:
            return "偏向正面"
        elif sentiment_score > -0.1:
            return "中性"
        elif sentiment_score > -0.3:
            return "偏向負面"
        else:
            return "明顯負面"

    def _get_importance_level(self, importance_score: float) -> str:
        """獲取重要性等級描述。

        Args:
            importance_score: 重要性分數

        Returns:
            重要性等級描述
        """
        if importance_score > 0.8:
            return "極高"
        elif importance_score > 0.6:
            return "高"
        elif importance_score > 0.4:
            return "中等"
        elif importance_score > 0.2:
            return "低"
        else:
            return "極低"

    def _get_news_analysis_task_prompt(self) -> str:
        """獲取新聞分析任務提示詞。

        Returns:
            任務提示字符串
        """
        return """請基於以上新聞分析結果，進行綜合評估：

1. 分析新聞對股價的潛在影響
2. 評估市場情緒的變化趨勢
3. 識別關鍵的風險和機會因素
4. 給出明確的交易建議：[買入]、[賣出]或[持有]
5. 提供決策置信度（0-100分）

請重點關注：
- 新聞的時效性和可信度
- 事件對公司基本面的影響
- 市場情緒的持續性
- 潛在的風險因素

請以結構化的方式回答，包含詳細的分析過程。"""

    def _parse_llm_output(self, llm_output: str) -> Dict[str, Any]:
        """解析新聞分析的輸出。

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
                'sentiment_analysis': {},
                'risk_factors': []
            }
            
            # 提取交易建議
            prediction = self._extract_trading_recommendation(llm_output)
            result['prediction'] = prediction
            
            # 提取置信度
            confidence = self._extract_confidence_score(llm_output)
            result['confidence'] = confidence
            
            # 提取情緒分析結果
            sentiment_analysis = self._extract_sentiment_analysis(llm_output)
            result['sentiment_analysis'] = sentiment_analysis
            
            # 提取風險因素
            risk_factors = self._extract_risk_factors(llm_output)
            result['risk_factors'] = risk_factors
            
            logger.info(f"新聞分析輸出解析完成: 建議={prediction}, 置信度={confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"解析新聞分析輸出失敗: {e}")
            raise LLMStrategyError(f"解析新聞分析輸出失敗: {e}") from e

    def _extract_trading_recommendation(self, output: str) -> str:
        """提取交易建議。

        Args:
            output: LLM輸出

        Returns:
            交易建議 ('上漲', '下跌', '持平')
        """
        if '[買入]' in output or '建議買入' in output:
            return '上漲'
        elif '[賣出]' in output or '建議賣出' in output:
            return '下跌'
        elif '[持有]' in output or '建議持有' in output:
            return '持平'
        else:
            # 基於其他關鍵詞判斷
            if '看好' in output or '正面' in output:
                return '上漲'
            elif '看空' in output or '負面' in output:
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
        patterns = [
            r'置信度[：:]?\s*(\d+)分',
            r'置信度[：:]?\s*(\d+)%',
            r'確定性[：:]?\s*(\d+)%'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                score = float(match.group(1))
                return min(score / 100.0, 1.0)
        
        # 基於文本內容估算
        return self._estimate_confidence_from_text(output)

    def _estimate_confidence_from_text(self, text: str) -> float:
        """基於文本內容估算置信度。

        Args:
            text: 文本內容

        Returns:
            估算的置信度
        """
        high_confidence_words = ['明確', '確定', '強烈', '顯著']
        low_confidence_words = ['可能', '或許', '不確定', '謹慎']
        
        high_count = sum(1 for word in high_confidence_words if word in text)
        low_count = sum(1 for word in low_confidence_words if word in text)
        
        base_confidence = 0.6
        adjustment = (high_count - low_count) * 0.1
        
        return max(0.0, min(1.0, base_confidence + adjustment))

    def _extract_sentiment_analysis(self, output: str) -> Dict[str, Any]:
        """提取情緒分析結果。

        Args:
            output: LLM輸出

        Returns:
            情緒分析結果字典
        """
        sentiment_info = {
            'overall_sentiment': '中性',
            'sentiment_strength': 0.5,
            'key_factors': []
        }
        
        # 提取整體情緒
        if '積極' in output or '正面' in output:
            sentiment_info['overall_sentiment'] = '正面'
            sentiment_info['sentiment_strength'] = 0.7
        elif '消極' in output or '負面' in output:
            sentiment_info['overall_sentiment'] = '負面'
            sentiment_info['sentiment_strength'] = 0.3
        
        return sentiment_info

    def _extract_risk_factors(self, output: str) -> List[str]:
        """提取風險因素。

        Args:
            output: LLM輸出

        Returns:
            風險因素列表
        """
        risk_factors = []
        
        # 查找風險相關的內容
        lines = output.split('\n')
        for line in lines:
            if any(keyword in line for keyword in ['風險', '注意', '警告', '不確定']):
                risk_factors.append(line.strip())
        
        return risk_factors

    def get_strategy_info(self) -> Dict[str, Any]:
        """獲取策略資訊。

        Returns:
            策略資訊字典
        """
        info = super().get_strategy_info()
        info.update({
            'strategy_type': '新聞分析',
            'sentiment_threshold': self.sentiment_threshold,
            'importance_threshold': self.importance_threshold,
            'time_decay_factor': self.time_decay_factor,
            'max_news_count': self.max_news_count
        })
        return info
