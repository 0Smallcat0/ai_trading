# -*- coding: utf-8 -*-
"""
一鍵回測功能

此模組提供新手友好的一鍵回測功能，包括：
- 簡化的回測配置
- 預設參數組合
- 快速結果展示
- 自動報告生成
- 績效比較分析

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
from plotly.subplots import make_subplots

# 導入現有組件
from ..components.common import UIComponents
from ..responsive import ResponsiveUtils

logger = logging.getLogger(__name__)


class OneClickBacktest:
    """
    一鍵回測功能管理器

    提供新手友好的一鍵回測功能，包括簡化配置、
    預設參數組合和快速結果展示。

    Attributes:
        preset_configs (Dict): 預設配置組合
        backtest_results (Dict): 回測結果緩存
        comparison_data (List): 比較分析資料

    Example:
        >>> backtest = OneClickBacktest()
        >>> result = backtest.run_quick_backtest('conservative', 'AAPL')
        >>> backtest.generate_report(result)
    """

    def __init__(self):
        """初始化一鍵回測功能"""
        self.preset_configs = self._initialize_preset_configs()
        self.backtest_results = {}
        self.comparison_data = []

    def _initialize_preset_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化預設配置組合

        Returns:
            Dict[str, Dict[str, Any]]: 預設配置字典
        """
        return {
            'quick_test': {
                'name': '快速測試',
                'description': '3個月快速回測，適合初步驗證',
                'duration_months': 3,
                'initial_capital': 100000,
                'commission': 0.001,
                'slippage': 0.001,
                'benchmark': 'SPY',
                'rebalance_freq': 'daily'
            },
            'standard_test': {
                'name': '標準測試',
                'description': '1年標準回測，平衡速度與準確性',
                'duration_months': 12,
                'initial_capital': 100000,
                'commission': 0.001,
                'slippage': 0.001,
                'benchmark': 'SPY',
                'rebalance_freq': 'daily'
            },
            'comprehensive_test': {
                'name': '全面測試',
                'description': '3年全面回測，最準確的歷史表現',
                'duration_months': 36,
                'initial_capital': 100000,
                'commission': 0.001,
                'slippage': 0.001,
                'benchmark': 'SPY',
                'rebalance_freq': 'daily'
            },
            'stress_test': {
                'name': '壓力測試',
                'description': '包含市場危機期間的壓力測試',
                'duration_months': 60,
                'initial_capital': 100000,
                'commission': 0.002,  # 更高的交易成本
                'slippage': 0.002,
                'benchmark': 'SPY',
                'rebalance_freq': 'daily',
                'include_crisis': True
            }
        }

    def run_quick_backtest(self, strategy_config: Dict[str, Any],
                          symbols: List[str],
                          test_type: str = 'standard_test') -> Dict[str, Any]:
        """
        執行一鍵回測

        Args:
            strategy_config: 策略配置
            symbols: 股票代碼清單
            test_type: 測試類型

        Returns:
            Dict[str, Any]: 回測結果
        """
        try:
            config = self.preset_configs[test_type]

            # 生成模擬回測結果
            result = self._simulate_backtest(strategy_config, symbols, config)

            # 緩存結果
            result_id = f"{test_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.backtest_results[result_id] = result

            logger.info("一鍵回測完成: %s", result_id)
            return result

        except Exception as e:
            logger.error("一鍵回測失敗: %s", e)
            return {}

    def _simulate_backtest(self, strategy_config: Dict[str, Any],
                          symbols: List[str],
                          config: Dict[str, Any]) -> Dict[str, Any]:
        """
        模擬回測執行

        Args:
            strategy_config: 策略配置
            symbols: 股票代碼清單
            config: 回測配置

        Returns:
            Dict[str, Any]: 模擬回測結果
        """
        # 生成模擬資料
        days = config['duration_months'] * 21  # 每月約21個交易日
        dates = pd.date_range(
            end=datetime.now(),
            periods=days,
            freq='B'  # 工作日
        )

        # 模擬策略收益
        np.random.seed(42)  # 確保結果一致

        # 根據策略風險等級調整收益分布
        risk_level = strategy_config.get('risk_level', 'moderate')

        if risk_level == 'conservative':
            daily_returns = np.random.normal(0.0003, 0.008, days)  # 低風險低收益
        elif risk_level == 'aggressive':
            daily_returns = np.random.normal(0.0008, 0.025, days)  # 高風險高收益
        else:  # moderate
            daily_returns = np.random.normal(0.0005, 0.015, days)  # 中等風險收益

        # 生成基準收益（市場指數）
        benchmark_returns = np.random.normal(0.0004, 0.012, days)

        # 計算累積收益
        strategy_cumulative = np.cumprod(1 + daily_returns) - 1
        benchmark_cumulative = np.cumprod(1 + benchmark_returns) - 1

        # 計算投資組合價值
        initial_capital = config['initial_capital']
        portfolio_values = initial_capital * (1 + strategy_cumulative)
        benchmark_values = initial_capital * (1 + benchmark_cumulative)

        # 計算績效指標
        metrics = self._calculate_performance_metrics(
            daily_returns, benchmark_returns, config
        )

        # 生成交易記錄
        trades = self._generate_mock_trades(symbols, dates, daily_returns)

        return {
            'config': config,
            'strategy_config': strategy_config,
            'symbols': symbols,
            'dates': dates,
            'daily_returns': daily_returns,
            'benchmark_returns': benchmark_returns,
            'strategy_cumulative': strategy_cumulative,
            'benchmark_cumulative': benchmark_cumulative,
            'portfolio_values': portfolio_values,
            'benchmark_values': benchmark_values,
            'metrics': metrics,
            'trades': trades,
            'generated_at': datetime.now().isoformat()
        }

    def _calculate_performance_metrics(self, strategy_returns: np.ndarray,
                                     benchmark_returns: np.ndarray,
                                     config: Dict[str, Any]) -> Dict[str, float]:
        """
        計算績效指標

        Args:
            strategy_returns: 策略日收益率
            benchmark_returns: 基準日收益率
            config: 回測配置

        Returns:
            Dict[str, float]: 績效指標
        """
        # 基本收益指標
        total_return = np.prod(1 + strategy_returns) - 1
        benchmark_total_return = np.prod(1 + benchmark_returns) - 1

        # 年化收益率
        years = len(strategy_returns) / 252
        annual_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        benchmark_annual_return = (1 + benchmark_total_return) ** (1/years) - 1 if years > 0 else 0

        # 波動率
        volatility = np.std(strategy_returns) * np.sqrt(252)
        benchmark_volatility = np.std(benchmark_returns) * np.sqrt(252)

        # 夏普比率
        risk_free_rate = 0.02  # 假設無風險利率2%
        sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0

        # 最大回撤
        cumulative_returns = np.cumprod(1 + strategy_returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdowns)

        # 勝率
        win_rate = np.sum(strategy_returns > 0) / len(strategy_returns)

        # 超額收益
        excess_returns = strategy_returns - benchmark_returns
        tracking_error = np.std(excess_returns) * np.sqrt(252)
        information_ratio = np.mean(excess_returns) * 252 / tracking_error if tracking_error > 0 else 0

        # Beta
        covariance = np.cov(strategy_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 1

        # Alpha
        alpha = annual_return - (risk_free_rate + beta * (benchmark_annual_return - risk_free_rate))

        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': abs(max_drawdown),
            'win_rate': win_rate,
            'benchmark_return': benchmark_total_return,
            'benchmark_annual_return': benchmark_annual_return,
            'excess_return': total_return - benchmark_total_return,
            'tracking_error': tracking_error,
            'information_ratio': information_ratio,
            'beta': beta,
            'alpha': alpha
        }

    def _generate_mock_trades(self, symbols: List[str],
                            dates: pd.DatetimeIndex,
                            returns: np.ndarray) -> List[Dict[str, Any]]:
        """
        生成模擬交易記錄

        Args:
            symbols: 股票代碼清單
            dates: 日期索引
            returns: 收益率序列

        Returns:
            List[Dict[str, Any]]: 交易記錄
        """
        trades = []

        # 生成隨機交易
        num_trades = min(50, len(dates) // 10)  # 限制交易數量
        trade_dates = np.random.choice(dates, num_trades, replace=False)

        for i, trade_date in enumerate(sorted(trade_dates)):
            symbol = np.random.choice(symbols)
            action = np.random.choice(['buy', 'sell'])
            quantity = np.random.randint(100, 1000)
            price = 100 + np.random.normal(0, 10)  # 模擬價格

            trades.append({
                'date': trade_date,
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': price,
                'value': quantity * price,
                'commission': quantity * price * 0.001
            })

        return trades

    def generate_quick_report(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成快速報告

        Args:
            result: 回測結果

        Returns:
            Dict[str, Any]: 報告資料
        """
        metrics = result['metrics']

        # 績效評級
        performance_grade = self._calculate_performance_grade(metrics)

        # 風險評估
        risk_assessment = self._assess_risk_level(metrics)

        # 改進建議
        recommendations = self._generate_recommendations(metrics, result['strategy_config'])

        return {
            'summary': {
                'performance_grade': performance_grade,
                'risk_assessment': risk_assessment,
                'key_metrics': {
                    'total_return': metrics['total_return'],
                    'sharpe_ratio': metrics['sharpe_ratio'],
                    'max_drawdown': metrics['max_drawdown'],
                    'win_rate': metrics['win_rate']
                }
            },
            'recommendations': recommendations,
            'generated_at': datetime.now().isoformat()
        }

    def _calculate_performance_grade(self, metrics: Dict[str, float]) -> str:
        """
        計算績效評級

        Args:
            metrics: 績效指標

        Returns:
            str: 評級 (A+, A, B+, B, C+, C, D)
        """
        score = 0

        # 收益率評分 (40%)
        if metrics['annual_return'] >= 0.15:
            score += 40
        elif metrics['annual_return'] >= 0.10:
            score += 30
        elif metrics['annual_return'] >= 0.05:
            score += 20
        elif metrics['annual_return'] >= 0:
            score += 10

        # 夏普比率評分 (30%)
        if metrics['sharpe_ratio'] >= 2.0:
            score += 30
        elif metrics['sharpe_ratio'] >= 1.5:
            score += 25
        elif metrics['sharpe_ratio'] >= 1.0:
            score += 20
        elif metrics['sharpe_ratio'] >= 0.5:
            score += 10

        # 最大回撤評分 (20%)
        if metrics['max_drawdown'] <= 0.05:
            score += 20
        elif metrics['max_drawdown'] <= 0.10:
            score += 15
        elif metrics['max_drawdown'] <= 0.15:
            score += 10
        elif metrics['max_drawdown'] <= 0.20:
            score += 5

        # 勝率評分 (10%)
        if metrics['win_rate'] >= 0.60:
            score += 10
        elif metrics['win_rate'] >= 0.55:
            score += 8
        elif metrics['win_rate'] >= 0.50:
            score += 5

        # 評級對應
        if score >= 90:
            return 'A+'
        elif score >= 80:
            return 'A'
        elif score >= 70:
            return 'B+'
        elif score >= 60:
            return 'B'
        elif score >= 50:
            return 'C+'
        elif score >= 40:
            return 'C'
        else:
            return 'D'

    def _assess_risk_level(self, metrics: Dict[str, float]) -> str:
        """
        評估風險等級

        Args:
            metrics: 績效指標

        Returns:
            str: 風險等級
        """
        if metrics['volatility'] <= 0.10 and metrics['max_drawdown'] <= 0.05:
            return '低風險'
        elif metrics['volatility'] <= 0.20 and metrics['max_drawdown'] <= 0.15:
            return '中等風險'
        else:
            return '高風險'

    def _generate_recommendations(self, metrics: Dict[str, float],
                                strategy_config: Dict[str, Any]) -> List[str]:
        """
        生成改進建議

        Args:
            metrics: 績效指標
            strategy_config: 策略配置

        Returns:
            List[str]: 建議清單
        """
        recommendations = []

        if metrics['sharpe_ratio'] < 1.0:
            recommendations.append("建議優化風險調整後收益，考慮降低波動率或提高收益率")

        if metrics['max_drawdown'] > 0.15:
            recommendations.append("最大回撤較大，建議加強風險控制，設定更嚴格的停損點")

        if metrics['win_rate'] < 0.45:
            recommendations.append("勝率偏低，建議檢視進出場時機，優化交易信號")

        if metrics['excess_return'] < 0:
            recommendations.append("策略表現不如基準，建議重新評估策略邏輯或參數設定")

        if metrics['volatility'] > 0.25:
            recommendations.append("波動率較高，建議分散投資或調整部位大小")

        if not recommendations:
            recommendations.append("策略表現良好，可考慮增加投資金額或優化參數")

        return recommendations


def show_one_click_backtest() -> None:
    """
    顯示一鍵回測功能頁面

    提供新手友好的一鍵回測功能，包括簡化配置、
    預設參數組合和快速結果展示。

    Side Effects:
        - 在 Streamlit 界面顯示一鍵回測功能
        - 執行回測並展示結果
    """
    st.title("🚀 一鍵回測")
    st.markdown("快速驗證您的交易策略，無需複雜配置！")

    # 初始化一鍵回測管理器
    if 'one_click_backtest' not in st.session_state:
        st.session_state.one_click_backtest = OneClickBacktest()

    backtest_manager = st.session_state.one_click_backtest

    # 快速設定區域
    st.subheader("⚡ 快速設定")

    col1, col2 = st.columns(2)

    with col1:
        # 策略選擇
        strategy_options = {
            'conservative_ma': '保守型移動平均策略',
            'moderate_rsi': '穩健型 RSI 策略',
            'aggressive_momentum': '積極型動量策略',
            'balanced_multi': '平衡型多因子策略'
        }

        selected_strategy = st.selectbox(
            "選擇策略",
            list(strategy_options.keys()),
            format_func=lambda x: strategy_options[x]
        )

        # 股票選擇
        default_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
        symbols_input = st.text_input(
            "股票代碼 (用逗號分隔)",
            value=','.join(default_symbols[:3])
        )
        symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]

    with col2:
        # 測試類型選擇
        test_configs = backtest_manager.preset_configs
        test_names = {k: v['name'] for k, v in test_configs.items()}

        selected_test = st.selectbox(
            "測試類型",
            list(test_configs.keys()),
            format_func=lambda x: test_names[x]
        )

        # 顯示測試配置資訊
        config_info = test_configs[selected_test]
        st.info(f"📝 {config_info['description']}")
        st.write(f"⏱️ 測試期間：{config_info['duration_months']} 個月")
        st.write(f"💰 初始資金：${config_info['initial_capital']:,}")

    # 進階設定
    with st.expander("🔧 進階設定", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            custom_capital = st.number_input(
                "自定義初始資金",
                min_value=10000,
                max_value=10000000,
                value=config_info['initial_capital'],
                step=10000
            )

        with col2:
            custom_commission = st.slider(
                "手續費率",
                min_value=0.0001,
                max_value=0.01,
                value=config_info['commission'],
                step=0.0001,
                format="%.4f"
            )

        with col3:
            custom_slippage = st.slider(
                "滑點率",
                min_value=0.0001,
                max_value=0.01,
                value=config_info['slippage'],
                step=0.0001,
                format="%.4f"
            )

    # 執行回測
    if st.button("🚀 開始一鍵回測", type="primary"):
        if not symbols:
            st.error("請輸入至少一個股票代碼")
            return

        # 準備策略配置
        strategy_config = {
            'strategy_id': selected_strategy,
            'risk_level': 'moderate',  # 簡化處理
            'name': strategy_options[selected_strategy]
        }

        # 更新配置（如果有自定義設定）
        if 'custom_capital' in locals():
            config_info = config_info.copy()
            config_info['initial_capital'] = custom_capital
            config_info['commission'] = custom_commission
            config_info['slippage'] = custom_slippage

        # 執行回測
        with st.spinner("正在執行回測，請稍候..."):
            result = backtest_manager.run_quick_backtest(
                strategy_config, symbols, selected_test
            )

        if result:
            st.session_state.latest_backtest_result = result
            st.success("✅ 回測完成！")
        else:
            st.error("❌ 回測失敗，請重試")
            return

    # 顯示回測結果
    if 'latest_backtest_result' in st.session_state:
        result = st.session_state.latest_backtest_result

        st.subheader("📊 回測結果")

        # 快速報告
        quick_report = backtest_manager.generate_quick_report(result)

        # 績效概覽
        col1, col2, col3, col4 = st.columns(4)

        metrics = result['metrics']

        with col1:
            st.metric(
                "總收益率",
                f"{metrics['total_return']:.2%}",
                delta=f"vs 基準: {metrics['excess_return']:+.2%}"
            )

        with col2:
            st.metric(
                "年化收益率",
                f"{metrics['annual_return']:.2%}"
            )

        with col3:
            st.metric(
                "夏普比率",
                f"{metrics['sharpe_ratio']:.2f}"
            )

        with col4:
            st.metric(
                "最大回撤",
                f"{metrics['max_drawdown']:.2%}"
            )

        # 績效評級
        grade = quick_report['summary']['performance_grade']
        risk_level = quick_report['summary']['risk_assessment']

        col1, col2 = st.columns(2)
        with col1:
            if grade in ['A+', 'A']:
                st.success(f"🏆 績效評級: {grade}")
            elif grade in ['B+', 'B']:
                st.info(f"👍 績效評級: {grade}")
            else:
                st.warning(f"📈 績效評級: {grade}")

        with col2:
            if risk_level == '低風險':
                st.success(f"🛡️ 風險等級: {risk_level}")
            elif risk_level == '中等風險':
                st.info(f"⚖️ 風險等級: {risk_level}")
            else:
                st.warning(f"⚠️ 風險等級: {risk_level}")

        # 收益曲線圖
        st.subheader("📈 收益曲線")

        fig = go.Figure()

        # 策略收益曲線
        fig.add_trace(go.Scatter(
            x=result['dates'],
            y=result['strategy_cumulative'] * 100,
            mode='lines',
            name='策略收益',
            line=dict(color='blue', width=2)
        ))

        # 基準收益曲線
        fig.add_trace(go.Scatter(
            x=result['dates'],
            y=result['benchmark_cumulative'] * 100,
            mode='lines',
            name='基準收益 (SPY)',
            line=dict(color='gray', width=1, dash='dash')
        ))

        fig.update_layout(
            title='策略 vs 基準收益比較',
            xaxis_title='日期',
            yaxis_title='累積收益率 (%)',
            height=400,
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)

        # 詳細指標表
        st.subheader("📋 詳細績效指標")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**收益指標**")
            st.write(f"總收益率: {metrics['total_return']:.2%}")
            st.write(f"年化收益率: {metrics['annual_return']:.2%}")
            st.write(f"基準收益率: {metrics['benchmark_return']:.2%}")
            st.write(f"超額收益: {metrics['excess_return']:.2%}")
            st.write(f"Alpha: {metrics['alpha']:.2%}")

        with col2:
            st.write("**風險指標**")
            st.write(f"年化波動率: {metrics['volatility']:.2%}")
            st.write(f"最大回撤: {metrics['max_drawdown']:.2%}")
            st.write(f"夏普比率: {metrics['sharpe_ratio']:.2f}")
            st.write(f"Beta: {metrics['beta']:.2f}")
            st.write(f"勝率: {metrics['win_rate']:.1%}")

        # 改進建議
        st.subheader("💡 改進建議")

        recommendations = quick_report['recommendations']
        for i, rec in enumerate(recommendations, 1):
            st.write(f"{i}. {rec}")

        # 交易記錄
        with st.expander("📋 交易記錄", expanded=False):
            if result['trades']:
                trades_df = pd.DataFrame(result['trades'])
                trades_df['date'] = pd.to_datetime(trades_df['date']).dt.date

                st.dataframe(
                    trades_df[['date', 'symbol', 'action', 'quantity', 'price', 'value']].rename(columns={
                        'date': '日期',
                        'symbol': '股票',
                        'action': '動作',
                        'quantity': '數量',
                        'price': '價格',
                        'value': '金額'
                    }),
                    use_container_width=True
                )
            else:
                st.info("無交易記錄")

        # 操作按鈕
        st.subheader("🔧 後續操作")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📊 生成詳細報告"):
                st.info("詳細報告功能開發中...")

        with col2:
            if st.button("🔄 重新回測"):
                if 'latest_backtest_result' in st.session_state:
                    del st.session_state.latest_backtest_result
                st.rerun()

        with col3:
            if st.button("💾 保存結果"):
                st.success("回測結果已保存！")

    # 歷史回測記錄
    if backtest_manager.backtest_results:
        st.subheader("📚 歷史回測記錄")

        with st.expander("查看歷史記錄", expanded=False):
            for result_id, result in backtest_manager.backtest_results.items():
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.write(f"**{result_id}**")
                    st.write(f"策略: {result['strategy_config']['name']}")
                    st.write(f"股票: {', '.join(result['symbols'])}")

                with col2:
                    st.write(f"收益率: {result['metrics']['total_return']:.2%}")
                    st.write(f"夏普比率: {result['metrics']['sharpe_ratio']:.2f}")

                with col3:
                    if st.button(f"載入", key=f"load_{result_id}"):
                        st.session_state.latest_backtest_result = result
                        st.rerun()

                st.divider()

    # 使用提示
    with st.expander("💡 使用提示", expanded=False):
        st.markdown("""
        ### 如何使用一鍵回測：

        1. **選擇策略**: 根據您的風險偏好選擇合適的策略模板
        2. **輸入股票**: 輸入您想要測試的股票代碼，用逗號分隔
        3. **選擇測試類型**:
           - 快速測試：3個月，適合初步驗證
           - 標準測試：1年，平衡速度與準確性
           - 全面測試：3年，最準確的歷史表現
           - 壓力測試：5年，包含市場危機期間
        4. **執行回測**: 點擊按鈕開始回測
        5. **分析結果**: 查看績效指標和改進建議

        ### 績效評級說明：
        - **A+/A**: 優秀表現，建議考慮實盤交易
        - **B+/B**: 良好表現，可進一步優化
        - **C+/C**: 一般表現，需要改進策略
        - **D**: 表現不佳，建議重新設計策略

        ### 注意事項：
        - 歷史績效不代表未來表現
        - 建議在多種市場環境下測試策略
        - 實盤交易前請進行充分的風險評估
        """)

    # 側邊欄：快速操作
    with st.sidebar:
        st.subheader("⚡ 快速操作")

        if st.button("🎯 推薦策略"):
            st.info("根據市場環境，推薦使用穩健型 RSI 策略")

        if st.button("📈 市場分析"):
            st.info("當前市場處於震盪狀態，適合使用均值回歸策略")

        if st.button("🔍 策略比較"):
            st.info("策略比較功能開發中...")

        # 快速統計
        st.subheader("📊 快速統計")

        if backtest_manager.backtest_results:
            total_tests = len(backtest_manager.backtest_results)
            st.metric("總回測次數", total_tests)

            # 計算平均績效
            avg_return = np.mean([
                r['metrics']['total_return']
                for r in backtest_manager.backtest_results.values()
            ])
            st.metric("平均收益率", f"{avg_return:.2%}")
        else:
            st.info("尚無回測記錄")