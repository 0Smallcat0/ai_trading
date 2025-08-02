# -*- coding: utf-8 -*-
"""
交易決策記錄器

此模組提供交易決策的記錄和分析功能，包括：
- 決策過程記錄
- 決策理由分析
- 決策結果追蹤
- 決策模式識別
- 學習建議生成

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime, timedelta
import json

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


class DecisionLogger:
    """
    交易決策記錄器
    
    提供交易決策的完整記錄和分析功能，幫助用戶
    理解和改進自己的決策過程。
    
    Attributes:
        decision_history (List): 決策歷史記錄
        decision_categories (Dict): 決策分類
        analysis_metrics (Dict): 分析指標
        
    Example:
        >>> logger = DecisionLogger()
        >>> logger.log_decision('buy', 'AAPL', reasoning='技術分析顯示突破')
        >>> analysis = logger.analyze_decision_patterns()
    """
    
    def __init__(self):
        """初始化交易決策記錄器"""
        self.decision_history = []
        self.decision_categories = self._initialize_decision_categories()
        self.analysis_metrics = self._initialize_analysis_metrics()
        
    def _initialize_decision_categories(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化決策分類
        
        Returns:
            Dict[str, Dict[str, Any]]: 決策分類字典
        """
        return {
            'technical_analysis': {
                'name': '技術分析',
                'description': '基於技術指標和圖表分析的決策',
                'indicators': ['移動平均線', 'RSI', 'MACD', '支撐阻力位'],
                'weight': 0.4
            },
            'fundamental_analysis': {
                'name': '基本面分析',
                'description': '基於公司財務和經濟數據的決策',
                'indicators': ['財報數據', '估值指標', '行業分析', '經濟指標'],
                'weight': 0.3
            },
            'risk_management': {
                'name': '風險管理',
                'description': '基於風險控制考量的決策',
                'indicators': ['停損設定', '部位大小', '分散投資', '風險評估'],
                'weight': 0.2
            },
            'market_sentiment': {
                'name': '市場情緒',
                'description': '基於市場情緒和心理因素的決策',
                'indicators': ['新聞事件', '市場恐慌', '投資人情緒', '資金流向'],
                'weight': 0.1
            }
        }
    
    def _initialize_analysis_metrics(self) -> Dict[str, Any]:
        """
        初始化分析指標
        
        Returns:
            Dict[str, Any]: 分析指標字典
        """
        return {
            'decision_accuracy': 0.0,
            'avg_holding_period': 0.0,
            'risk_reward_ratio': 0.0,
            'decision_consistency': 0.0,
            'learning_progress': 0.0
        }
    
    def log_decision(self, action: str, symbol: str, reasoning: str,
                    confidence: float = 0.5, expected_outcome: str = '',
                    risk_level: str = 'medium') -> str:
        """
        記錄交易決策
        
        Args:
            action: 交易動作 ('buy', 'sell', 'hold')
            symbol: 股票代碼
            reasoning: 決策理由
            confidence: 信心程度 (0-1)
            expected_outcome: 預期結果
            risk_level: 風險等級
            
        Returns:
            str: 決策記錄ID
        """
        decision_id = f"decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        decision_record = {
            'id': decision_id,
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'symbol': symbol,
            'reasoning': reasoning,
            'confidence': confidence,
            'expected_outcome': expected_outcome,
            'risk_level': risk_level,
            'decision_category': self._categorize_decision(reasoning),
            'market_context': self._get_market_context(),
            'outcome': None,  # 待後續更新
            'actual_result': None,
            'lessons_learned': None
        }
        
        self.decision_history.append(decision_record)
        logger.info("決策已記錄: %s - %s %s", decision_id, action, symbol)
        
        return decision_id
    
    def _categorize_decision(self, reasoning: str) -> str:
        """
        根據決策理由分類決策
        
        Args:
            reasoning: 決策理由
            
        Returns:
            str: 決策分類
        """
        reasoning_lower = reasoning.lower()
        
        # 技術分析關鍵詞
        technical_keywords = ['技術', '圖表', 'rsi', 'macd', '移動平均', '突破', '支撐', '阻力']
        if any(keyword in reasoning_lower for keyword in technical_keywords):
            return 'technical_analysis'
        
        # 基本面分析關鍵詞
        fundamental_keywords = ['財報', '營收', '獲利', '估值', 'pe', '基本面', '經濟']
        if any(keyword in reasoning_lower for keyword in fundamental_keywords):
            return 'fundamental_analysis'
        
        # 風險管理關鍵詞
        risk_keywords = ['風險', '停損', '部位', '分散', '保護']
        if any(keyword in reasoning_lower for keyword in risk_keywords):
            return 'risk_management'
        
        # 市場情緒關鍵詞
        sentiment_keywords = ['新聞', '情緒', '恐慌', '樂觀', '市場氣氛']
        if any(keyword in reasoning_lower for keyword in sentiment_keywords):
            return 'market_sentiment'
        
        return 'technical_analysis'  # 預設分類
    
    def _get_market_context(self) -> Dict[str, Any]:
        """
        獲取市場環境背景
        
        Returns:
            Dict[str, Any]: 市場環境資訊
        """
        # 模擬市場環境資訊
        return {
            'market_trend': np.random.choice(['上升', '下降', '橫盤']),
            'volatility': np.random.uniform(0.1, 0.3),
            'volume': np.random.uniform(0.8, 1.5),
            'sentiment_index': np.random.uniform(0.3, 0.7)
        }
    
    def update_decision_outcome(self, decision_id: str, outcome: str,
                              actual_result: float, lessons_learned: str = '') -> bool:
        """
        更新決策結果
        
        Args:
            decision_id: 決策記錄ID
            outcome: 決策結果 ('success', 'failure', 'partial')
            actual_result: 實際收益率
            lessons_learned: 學習心得
            
        Returns:
            bool: 更新是否成功
        """
        for decision in self.decision_history:
            if decision['id'] == decision_id:
                decision['outcome'] = outcome
                decision['actual_result'] = actual_result
                decision['lessons_learned'] = lessons_learned
                decision['updated_at'] = datetime.now().isoformat()
                
                logger.info("決策結果已更新: %s - %s", decision_id, outcome)
                return True
        
        logger.warning("找不到決策記錄: %s", decision_id)
        return False
    
    def analyze_decision_patterns(self) -> Dict[str, Any]:
        """
        分析決策模式
        
        Returns:
            Dict[str, Any]: 決策模式分析結果
        """
        if not self.decision_history:
            return {'message': '尚無決策記錄可供分析'}
        
        df = pd.DataFrame(self.decision_history)
        
        # 決策準確率
        completed_decisions = df[df['outcome'].notna()]
        if len(completed_decisions) > 0:
            accuracy = len(completed_decisions[completed_decisions['outcome'] == 'success']) / len(completed_decisions)
        else:
            accuracy = 0.0
        
        # 決策分類分布
        category_distribution = df['decision_category'].value_counts().to_dict()
        
        # 信心程度與結果關係
        confidence_analysis = self._analyze_confidence_accuracy(completed_decisions)
        
        # 決策頻率分析
        frequency_analysis = self._analyze_decision_frequency(df)
        
        # 風險等級分析
        risk_analysis = df['risk_level'].value_counts().to_dict()
        
        return {
            'decision_accuracy': accuracy,
            'total_decisions': len(df),
            'completed_decisions': len(completed_decisions),
            'category_distribution': category_distribution,
            'confidence_analysis': confidence_analysis,
            'frequency_analysis': frequency_analysis,
            'risk_analysis': risk_analysis,
            'improvement_suggestions': self._generate_improvement_suggestions(df)
        }
    
    def _analyze_confidence_accuracy(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析信心程度與準確率的關係"""
        if df.empty:
            return {}
        
        # 將信心程度分組
        df['confidence_group'] = pd.cut(df['confidence'], 
                                      bins=[0, 0.3, 0.7, 1.0], 
                                      labels=['低信心', '中信心', '高信心'])
        
        confidence_accuracy = df.groupby('confidence_group')['outcome'].apply(
            lambda x: (x == 'success').mean()
        ).to_dict()
        
        return confidence_accuracy
    
    def _analyze_decision_frequency(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析決策頻率"""
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        daily_decisions = df.groupby('date').size()
        
        return {
            'avg_daily_decisions': daily_decisions.mean(),
            'max_daily_decisions': daily_decisions.max(),
            'decision_days': len(daily_decisions)
        }
    
    def _generate_improvement_suggestions(self, df: pd.DataFrame) -> List[str]:
        """生成改進建議"""
        suggestions = []
        
        # 分析決策準確率
        completed = df[df['outcome'].notna()]
        if len(completed) > 0:
            accuracy = (completed['outcome'] == 'success').mean()
            if accuracy < 0.5:
                suggestions.append("決策準確率偏低，建議加強分析技能和風險控制")
        
        # 分析決策頻率
        if len(df) > 0:
            days = (pd.to_datetime(df['timestamp']).max() - pd.to_datetime(df['timestamp']).min()).days
            if days > 0:
                daily_avg = len(df) / days
                if daily_avg > 5:
                    suggestions.append("決策頻率過高，可能存在過度交易問題")
        
        # 分析信心程度
        avg_confidence = df['confidence'].mean()
        if avg_confidence < 0.4:
            suggestions.append("平均信心程度偏低，建議加強學習和分析能力")
        elif avg_confidence > 0.8:
            suggestions.append("信心程度過高，注意避免過度自信的風險")
        
        # 分析決策分類多樣性
        categories = df['decision_category'].nunique()
        if categories < 2:
            suggestions.append("決策依據過於單一，建議多角度分析")
        
        if not suggestions:
            suggestions.append("決策模式良好，繼續保持並持續學習改進")
        
        return suggestions
    
    def generate_decision_report(self, period_days: int = 30) -> Dict[str, Any]:
        """
        生成決策報告
        
        Args:
            period_days: 報告期間（天數）
            
        Returns:
            Dict[str, Any]: 決策報告
        """
        cutoff_date = datetime.now() - timedelta(days=period_days)
        
        # 篩選期間內的決策
        period_decisions = [
            d for d in self.decision_history 
            if datetime.fromisoformat(d['timestamp']) >= cutoff_date
        ]
        
        if not period_decisions:
            return {'message': f'過去 {period_days} 天內無決策記錄'}
        
        df = pd.DataFrame(period_decisions)
        
        # 基本統計
        total_decisions = len(df)
        completed_decisions = len(df[df['outcome'].notna()])
        
        # 績效統計
        performance_stats = self._calculate_performance_stats(df)
        
        # 決策品質分析
        quality_analysis = self._analyze_decision_quality(df)
        
        # 學習進度評估
        learning_progress = self._assess_learning_progress(df)
        
        return {
            'period_days': period_days,
            'total_decisions': total_decisions,
            'completed_decisions': completed_decisions,
            'performance_stats': performance_stats,
            'quality_analysis': quality_analysis,
            'learning_progress': learning_progress,
            'recommendations': self._generate_personalized_recommendations(df)
        }
    
    def _calculate_performance_stats(self, df: pd.DataFrame) -> Dict[str, float]:
        """計算績效統計"""
        completed = df[df['outcome'].notna()]
        
        if completed.empty:
            return {}
        
        success_rate = (completed['outcome'] == 'success').mean()
        
        # 計算平均收益（如果有實際結果）
        with_results = completed[completed['actual_result'].notna()]
        avg_return = with_results['actual_result'].mean() if not with_results.empty else 0.0
        
        return {
            'success_rate': success_rate,
            'average_return': avg_return,
            'total_return': with_results['actual_result'].sum() if not with_results.empty else 0.0
        }
    
    def _analyze_decision_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析決策品質"""
        return {
            'avg_confidence': df['confidence'].mean(),
            'reasoning_completeness': df['reasoning'].str.len().mean(),
            'risk_awareness': (df['risk_level'] != 'high').mean()
        }
    
    def _assess_learning_progress(self, df: pd.DataFrame) -> Dict[str, Any]:
        """評估學習進度"""
        if len(df) < 10:
            return {'message': '決策數量不足，無法評估學習進度'}
        
        # 按時間排序
        df_sorted = df.sort_values('timestamp')
        
        # 分析前半期和後半期的表現
        mid_point = len(df_sorted) // 2
        first_half = df_sorted.iloc[:mid_point]
        second_half = df_sorted.iloc[mid_point:]
        
        first_half_accuracy = (first_half[first_half['outcome'].notna()]['outcome'] == 'success').mean()
        second_half_accuracy = (second_half[second_half['outcome'].notna()]['outcome'] == 'success').mean()
        
        improvement = second_half_accuracy - first_half_accuracy
        
        return {
            'first_half_accuracy': first_half_accuracy,
            'second_half_accuracy': second_half_accuracy,
            'improvement': improvement,
            'learning_trend': 'improving' if improvement > 0.05 else 'stable' if improvement > -0.05 else 'declining'
        }
    
    def _generate_personalized_recommendations(self, df: pd.DataFrame) -> List[str]:
        """生成個人化建議"""
        recommendations = []
        
        # 基於決策模式的建議
        analysis = self.analyze_decision_patterns()
        
        if analysis.get('decision_accuracy', 0) < 0.6:
            recommendations.append("建議加強基本分析技能，提高決策準確率")
        
        if analysis.get('frequency_analysis', {}).get('avg_daily_decisions', 0) > 3:
            recommendations.append("決策頻率較高，建議更謹慎地選擇交易時機")
        
        # 基於信心程度的建議
        avg_confidence = df['confidence'].mean()
        if avg_confidence < 0.5:
            recommendations.append("建議增強分析能力，提高決策信心")
        
        # 基於風險管理的建議
        high_risk_ratio = (df['risk_level'] == 'high').mean()
        if high_risk_ratio > 0.3:
            recommendations.append("高風險決策比例較高，建議加強風險控制")
        
        return recommendations


def show_decision_logger() -> None:
    """
    顯示交易決策記錄器頁面
    
    提供交易決策的記錄、分析和學習功能，
    幫助用戶改進決策過程。
    
    Side Effects:
        - 在 Streamlit 界面顯示決策記錄器
        - 提供決策記錄和分析功能
    """
    st.title("📝 交易決策記錄器")
    st.markdown("記錄和分析您的交易決策，持續改進決策品質！")
    
    # 初始化決策記錄器
    if 'decision_logger' not in st.session_state:
        st.session_state.decision_logger = DecisionLogger()
    
    logger_instance = st.session_state.decision_logger
    
    # 主要功能區域
    tab1, tab2, tab3, tab4 = st.tabs(["記錄決策", "決策分析", "學習報告", "歷史記錄"])
    
    with tab1:
        st.subheader("📝 記錄新決策")
        
        with st.form("decision_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                action = st.selectbox("交易動作", ["buy", "sell", "hold"], 
                                    format_func=lambda x: {"buy": "買入", "sell": "賣出", "hold": "持有"}[x])
                symbol = st.text_input("股票代碼", placeholder="例如: AAPL")
                confidence = st.slider("信心程度", 0.0, 1.0, 0.5, 0.1)
            
            with col2:
                risk_level = st.selectbox("風險等級", ["low", "medium", "high"],
                                        format_func=lambda x: {"low": "低風險", "medium": "中風險", "high": "高風險"}[x])
                expected_outcome = st.text_input("預期結果", placeholder="例如: 預期上漲10%")
            
            reasoning = st.text_area("決策理由", placeholder="詳細說明您的決策依據...")
            
            if st.form_submit_button("記錄決策"):
                if symbol and reasoning:
                    decision_id = logger_instance.log_decision(
                        action=action,
                        symbol=symbol,
                        reasoning=reasoning,
                        confidence=confidence,
                        expected_outcome=expected_outcome,
                        risk_level=risk_level
                    )
                    st.success(f"✅ 決策已記錄！ID: {decision_id}")
                else:
                    st.error("請填寫股票代碼和決策理由")
    
    with tab2:
        st.subheader("📊 決策模式分析")
        
        if logger_instance.decision_history:
            analysis = logger_instance.analyze_decision_patterns()
            
            # 基本統計
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("總決策數", analysis['total_decisions'])
            with col2:
                st.metric("已完成決策", analysis['completed_decisions'])
            with col3:
                st.metric("決策準確率", f"{analysis['decision_accuracy']:.1%}")
            with col4:
                st.metric("分析類別", len(analysis['category_distribution']))
            
            # 決策分類分布
            if analysis['category_distribution']:
                st.subheader("📈 決策分類分布")
                
                categories = list(analysis['category_distribution'].keys())
                values = list(analysis['category_distribution'].values())
                
                fig = px.pie(values=values, names=categories, title="決策依據分布")
                st.plotly_chart(fig, use_container_width=True)
            
            # 改進建議
            st.subheader("💡 改進建議")
            for suggestion in analysis['improvement_suggestions']:
                st.write(f"• {suggestion}")
        
        else:
            st.info("尚無決策記錄，請先記錄一些決策")
    
    with tab3:
        st.subheader("📋 學習報告")
        
        period_days = st.selectbox("報告期間", [7, 14, 30, 60, 90], index=2)
        
        if st.button("生成報告"):
            report = logger_instance.generate_decision_report(period_days)
            
            if 'message' in report:
                st.info(report['message'])
            else:
                # 顯示報告內容
                st.write(f"**報告期間**: 過去 {period_days} 天")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**基本統計**")
                    st.write(f"總決策數: {report['total_decisions']}")
                    st.write(f"已完成決策: {report['completed_decisions']}")
                
                with col2:
                    if 'performance_stats' in report and report['performance_stats']:
                        st.write("**績效統計**")
                        perf = report['performance_stats']
                        st.write(f"成功率: {perf.get('success_rate', 0):.1%}")
                        st.write(f"平均收益: {perf.get('average_return', 0):.2%}")
                
                # 個人化建議
                if 'recommendations' in report:
                    st.subheader("🎯 個人化建議")
                    for rec in report['recommendations']:
                        st.write(f"• {rec}")
    
    with tab4:
        st.subheader("📚 決策歷史記錄")
        
        if logger_instance.decision_history:
            # 顯示最近的決策記錄
            recent_decisions = sorted(
                logger_instance.decision_history, 
                key=lambda x: x['timestamp'], 
                reverse=True
            )[:10]
            
            for decision in recent_decisions:
                with st.expander(f"{decision['action'].upper()} {decision['symbol']} - {decision['timestamp'][:10]}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**動作**: {decision['action']}")
                        st.write(f"**股票**: {decision['symbol']}")
                        st.write(f"**信心程度**: {decision['confidence']:.1%}")
                        st.write(f"**風險等級**: {decision['risk_level']}")
                    
                    with col2:
                        st.write(f"**決策分類**: {decision['decision_category']}")
                        st.write(f"**結果**: {decision.get('outcome', '待確認')}")
                        if decision.get('actual_result'):
                            st.write(f"**實際收益**: {decision['actual_result']:.2%}")
                    
                    st.write(f"**決策理由**: {decision['reasoning']}")
                    
                    if decision.get('lessons_learned'):
                        st.write(f"**學習心得**: {decision['lessons_learned']}")
                    
                    # 更新結果按鈕
                    if decision.get('outcome') is None:
                        if st.button(f"更新結果", key=f"update_{decision['id']}"):
                            st.info("請在表單中更新決策結果")
        else:
            st.info("尚無決策記錄")
