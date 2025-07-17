# -*- coding: utf-8 -*-
"""
交互式學習系統

此模組提供完整的交互式金融量化學習體驗，包括：
- 量化交易概念解釋器
- 策略模擬和回測教學
- 風險管理教育模組
- 進階技術指標學習

主要功能：
- 概念可視化解釋
- 互動式策略構建
- 實時回測演示
- 風險場景模擬
- 學習進度追蹤

設計特色：
- 中文界面友好
- 循序漸進的學習路徑
- 實戰案例教學
- 個性化學習建議
"""

import logging
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class LearningModule:
    """學習模組數據類"""
    id: str
    title: str
    description: str
    difficulty_level: int
    estimated_time: int  # 分鐘
    prerequisites: List[str]
    learning_objectives: List[str]
    content_sections: List[Dict[str, Any]]
    exercises: List[Dict[str, Any]]
    resources: List[Dict[str, Any]]


@dataclass
class LearningProgress:
    """學習進度數據類"""
    user_id: str
    module_id: str
    completion_percentage: float
    time_spent: int  # 分鐘
    exercises_completed: int
    last_accessed: datetime
    quiz_scores: List[float]
    notes: str


class ConceptExplainer:
    """量化交易概念解釋器"""
    
    def __init__(self):
        self.concepts = self._load_concepts()
        logger.info("概念解釋器初始化完成")
    
    def _load_concepts(self) -> Dict[str, Dict[str, Any]]:
        """載入概念定義"""
        return {
            "sharpe_ratio": {
                "name": "夏普比率",
                "definition": "衡量投資組合風險調整後收益的指標",
                "formula": "(投資組合收益率 - 無風險利率) / 投資組合標準差",
                "interpretation": {
                    "> 1": "優秀",
                    "0.5-1": "良好", 
                    "0-0.5": "一般",
                    "< 0": "差"
                },
                "example_calculation": True
            },
            "max_drawdown": {
                "name": "最大回撤",
                "definition": "投資組合從峰值到谷值的最大跌幅",
                "formula": "(峰值 - 谷值) / 峰值",
                "interpretation": {
                    "< 5%": "風險很低",
                    "5-10%": "風險較低",
                    "10-20%": "風險中等",
                    "> 20%": "風險較高"
                },
                "example_calculation": True
            },
            "beta": {
                "name": "貝塔係數",
                "definition": "衡量投資組合相對於市場的系統性風險",
                "formula": "Cov(投資組合收益, 市場收益) / Var(市場收益)",
                "interpretation": {
                    "β = 1": "與市場同步",
                    "β > 1": "比市場波動大",
                    "β < 1": "比市場波動小",
                    "β < 0": "與市場反向"
                },
                "example_calculation": True
            },
            "moving_average": {
                "name": "移動平均線",
                "definition": "一定期間內價格的平均值，用於平滑價格波動",
                "types": ["簡單移動平均(SMA)", "指數移動平均(EMA)", "加權移動平均(WMA)"],
                "applications": ["趨勢識別", "支撐阻力", "交易信號"],
                "example_calculation": True
            },
            "rsi": {
                "name": "相對強弱指標",
                "definition": "衡量價格變動速度和幅度的動量振盪器",
                "formula": "RSI = 100 - (100 / (1 + RS))",
                "interpretation": {
                    "> 70": "超買區域",
                    "30-70": "正常區域",
                    "< 30": "超賣區域"
                },
                "example_calculation": True
            }
        }
    
    def explain_concept(self, concept_key: str) -> None:
        """解釋概念"""
        if concept_key not in self.concepts:
            st.error(f"概念 '{concept_key}' 不存在")
            return
        
        concept = self.concepts[concept_key]
        
        st.subheader(f"📚 {concept['name']}")
        
        # 定義
        st.markdown("**定義:**")
        st.write(concept['definition'])
        
        # 公式
        if 'formula' in concept:
            st.markdown("**計算公式:**")
            st.latex(concept['formula'])
        
        # 解釋
        if 'interpretation' in concept:
            st.markdown("**數值解釋:**")
            for range_val, meaning in concept['interpretation'].items():
                st.write(f"• {range_val}: {meaning}")
        
        # 類型或應用
        if 'types' in concept:
            st.markdown("**類型:**")
            for type_name in concept['types']:
                st.write(f"• {type_name}")
        
        if 'applications' in concept:
            st.markdown("**應用場景:**")
            for app in concept['applications']:
                st.write(f"• {app}")
        
        # 示例計算
        if concept.get('example_calculation'):
            if st.button(f"查看 {concept['name']} 計算示例"):
                self._show_calculation_example(concept_key)
    
    def _show_calculation_example(self, concept_key: str):
        """顯示計算示例"""
        if concept_key == "sharpe_ratio":
            self._demo_sharpe_ratio()
        elif concept_key == "max_drawdown":
            self._demo_max_drawdown()
        elif concept_key == "beta":
            self._demo_beta()
        elif concept_key == "moving_average":
            self._demo_moving_average()
        elif concept_key == "rsi":
            self._demo_rsi()
    
    def _demo_sharpe_ratio(self):
        """夏普比率計算演示"""
        st.markdown("### 夏普比率計算示例")
        
        # 生成示例數據
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)  # 日收益率
        risk_free_rate = 0.02 / 252  # 年化2%的無風險利率
        
        # 計算夏普比率
        excess_returns = returns - risk_free_rate
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**計算步驟:**")
            st.write(f"1. 平均超額收益: {np.mean(excess_returns):.6f}")
            st.write(f"2. 收益標準差: {np.std(returns):.6f}")
            st.write(f"3. 年化夏普比率: {sharpe_ratio:.4f}")
        
        with col2:
            # 可視化
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=returns, name="日收益率分佈"))
            fig.update_layout(title="收益率分佈", xaxis_title="收益率", yaxis_title="頻次")
            st.plotly_chart(fig, use_container_width=True)
    
    def _demo_max_drawdown(self):
        """最大回撤計算演示"""
        st.markdown("### 最大回撤計算示例")
        
        # 生成示例數據
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 252)
        cumulative_returns = (1 + returns).cumprod()
        
        # 計算回撤
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = np.min(drawdown)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**計算結果:**")
            st.write(f"最大回撤: {max_drawdown:.2%}")
            st.write(f"回撤開始: 第{np.argmax(peak)}天")
            st.write(f"回撤結束: 第{np.argmin(drawdown)}天")
        
        with col2:
            # 可視化
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=cumulative_returns, name="累積收益"))
            fig.add_trace(go.Scatter(y=peak, name="歷史峰值"))
            fig.update_layout(title="累積收益與回撤", yaxis_title="累積收益")
            st.plotly_chart(fig, use_container_width=True)
    
    def _demo_moving_average(self):
        """移動平均線演示"""
        st.markdown("### 移動平均線計算示例")
        
        # 生成示例價格數據
        np.random.seed(42)
        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
        price = 100 + np.cumsum(np.random.normal(0, 1, 100))
        
        # 計算不同移動平均
        ma5 = pd.Series(price).rolling(5).mean()
        ma20 = pd.Series(price).rolling(20).mean()
        
        # 可視化
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=price, name="價格"))
        fig.add_trace(go.Scatter(x=dates, y=ma5, name="5日移動平均"))
        fig.add_trace(go.Scatter(x=dates, y=ma20, name="20日移動平均"))
        fig.update_layout(title="移動平均線示例", xaxis_title="日期", yaxis_title="價格")
        st.plotly_chart(fig, use_container_width=True)


class StrategySimulator:
    """策略模擬器"""
    
    def __init__(self):
        self.strategies = self._load_strategies()
        logger.info("策略模擬器初始化完成")
    
    def _load_strategies(self) -> Dict[str, Dict[str, Any]]:
        """載入策略模板"""
        return {
            "ma_crossover": {
                "name": "移動平均交叉策略",
                "description": "當短期移動平均線上穿長期移動平均線時買入，下穿時賣出",
                "parameters": {
                    "short_window": {"default": 5, "min": 3, "max": 20},
                    "long_window": {"default": 20, "min": 10, "max": 50}
                },
                "difficulty": 1
            },
            "rsi_reversal": {
                "name": "RSI反轉策略", 
                "description": "當RSI低於30時買入，高於70時賣出",
                "parameters": {
                    "rsi_period": {"default": 14, "min": 5, "max": 30},
                    "oversold": {"default": 30, "min": 20, "max": 40},
                    "overbought": {"default": 70, "min": 60, "max": 80}
                },
                "difficulty": 2
            },
            "bollinger_bands": {
                "name": "布林帶策略",
                "description": "價格觸及下軌時買入，觸及上軌時賣出",
                "parameters": {
                    "period": {"default": 20, "min": 10, "max": 30},
                    "std_dev": {"default": 2, "min": 1, "max": 3}
                },
                "difficulty": 3
            }
        }
    
    def simulate_strategy(self, strategy_key: str, parameters: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
        """模擬策略"""
        if strategy_key == "ma_crossover":
            return self._simulate_ma_crossover(parameters, data)
        elif strategy_key == "rsi_reversal":
            return self._simulate_rsi_reversal(parameters, data)
        elif strategy_key == "bollinger_bands":
            return self._simulate_bollinger_bands(parameters, data)
        else:
            return {"error": "未知策略"}
    
    def _simulate_ma_crossover(self, params: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
        """模擬移動平均交叉策略"""
        short_window = params.get('short_window', 5)
        long_window = params.get('long_window', 20)
        
        # 計算移動平均
        data['MA_short'] = data['close'].rolling(short_window).mean()
        data['MA_long'] = data['close'].rolling(long_window).mean()
        
        # 生成信號
        data['signal'] = 0
        data['signal'][short_window:] = np.where(
            data['MA_short'][short_window:] > data['MA_long'][short_window:], 1, 0
        )
        data['positions'] = data['signal'].diff()
        
        # 計算收益
        data['returns'] = data['close'].pct_change()
        data['strategy_returns'] = data['signal'].shift(1) * data['returns']
        
        # 計算績效指標
        total_return = (1 + data['strategy_returns']).prod() - 1
        volatility = data['strategy_returns'].std() * np.sqrt(252)
        sharpe_ratio = data['strategy_returns'].mean() / data['strategy_returns'].std() * np.sqrt(252)
        
        return {
            "data": data,
            "total_return": total_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "signals": data[data['positions'] != 0]
        }


class RiskEducator:
    """風險管理教育模組"""
    
    def __init__(self):
        self.risk_scenarios = self._load_risk_scenarios()
        logger.info("風險教育模組初始化完成")
    
    def _load_risk_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """載入風險場景"""
        return {
            "market_crash": {
                "name": "市場崩盤",
                "description": "模擬2008年金融危機或2020年疫情初期的市場暴跌",
                "parameters": {
                    "crash_magnitude": 0.3,  # 30%跌幅
                    "crash_duration": 30,    # 30天
                    "recovery_time": 180     # 180天恢復
                }
            },
            "high_volatility": {
                "name": "高波動期",
                "description": "模擬市場高波動期的投資組合表現",
                "parameters": {
                    "volatility_multiplier": 3,
                    "duration": 60
                }
            },
            "sector_rotation": {
                "name": "板塊輪動",
                "description": "模擬不同板塊間的資金流動",
                "parameters": {
                    "rotation_frequency": 30,
                    "sector_impact": 0.15
                }
            }
        }
    
    def simulate_risk_scenario(self, scenario_key: str, portfolio_data: pd.DataFrame) -> Dict[str, Any]:
        """模擬風險場景"""
        scenario = self.risk_scenarios.get(scenario_key)
        if not scenario:
            return {"error": "未知風險場景"}
        
        if scenario_key == "market_crash":
            return self._simulate_market_crash(scenario['parameters'], portfolio_data)
        elif scenario_key == "high_volatility":
            return self._simulate_high_volatility(scenario['parameters'], portfolio_data)
        else:
            return {"error": "場景模擬未實現"}
    
    def _simulate_market_crash(self, params: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
        """模擬市場崩盤"""
        crash_magnitude = params['crash_magnitude']
        crash_duration = params['crash_duration']
        
        # 創建崩盤場景
        crash_returns = np.random.normal(-crash_magnitude/crash_duration, 0.05, crash_duration)
        normal_returns = np.random.normal(0.001, 0.02, len(data) - crash_duration)
        
        scenario_returns = np.concatenate([normal_returns[:len(data)//2], 
                                         crash_returns, 
                                         normal_returns[len(data)//2:]])[:len(data)]
        
        # 計算投資組合在崩盤場景下的表現
        portfolio_returns = data['close'].pct_change().fillna(0)
        scenario_portfolio = (1 + scenario_returns).cumprod()
        normal_portfolio = (1 + portfolio_returns).cumprod()
        
        return {
            "scenario_portfolio": scenario_portfolio,
            "normal_portfolio": normal_portfolio,
            "max_drawdown": (scenario_portfolio.min() - scenario_portfolio.max()) / scenario_portfolio.max(),
            "recovery_time": crash_duration + params.get('recovery_time', 180)
        }


class InteractiveLearningSystem:
    """交互式學習系統主類"""
    
    def __init__(self):
        self.concept_explainer = ConceptExplainer()
        self.strategy_simulator = StrategySimulator()
        self.risk_educator = RiskEducator()
        self.learning_modules = self._load_learning_modules()
        
        logger.info("交互式學習系統初始化完成")
    
    def _load_learning_modules(self) -> Dict[str, LearningModule]:
        """載入學習模組"""
        modules = {}
        
        # 基礎模組
        modules["basics"] = LearningModule(
            id="basics",
            title="量化交易基礎",
            description="學習量化交易的基本概念和原理",
            difficulty_level=1,
            estimated_time=60,
            prerequisites=[],
            learning_objectives=[
                "理解量化交易的基本概念",
                "掌握常用的金融指標",
                "學會基本的數據分析方法"
            ],
            content_sections=[
                {"title": "什麼是量化交易", "type": "text"},
                {"title": "常用金融指標", "type": "interactive"},
                {"title": "數據分析基礎", "type": "exercise"}
            ],
            exercises=[],
            resources=[]
        )
        
        # 策略開發模組
        modules["strategy_dev"] = LearningModule(
            id="strategy_dev",
            title="策略開發與回測",
            description="學習如何開發和測試交易策略",
            difficulty_level=3,
            estimated_time=120,
            prerequisites=["basics"],
            learning_objectives=[
                "掌握策略開發流程",
                "學會回測方法",
                "理解績效評估指標"
            ],
            content_sections=[
                {"title": "策略開發流程", "type": "text"},
                {"title": "回測框架", "type": "interactive"},
                {"title": "績效評估", "type": "exercise"}
            ],
            exercises=[],
            resources=[]
        )
        
        return modules
    
    def show_learning_dashboard(self):
        """顯示學習儀表板"""
        st.title("🎓 量化交易學習中心")
        
        # 學習進度概覽
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("已完成模組", "3", "1")
        
        with col2:
            st.metric("學習時間", "5.2小時", "1.5小時")
        
        with col3:
            st.metric("掌握概念", "15", "3")
        
        # 學習模組選擇
        st.subheader("📚 學習模組")
        
        module_tabs = st.tabs(["概念學習", "策略模擬", "風險教育", "進度追蹤"])
        
        with module_tabs[0]:
            self._show_concept_learning()
        
        with module_tabs[1]:
            self._show_strategy_simulation()
        
        with module_tabs[2]:
            self._show_risk_education()
        
        with module_tabs[3]:
            self._show_progress_tracking()
    
    def _show_concept_learning(self):
        """顯示概念學習界面"""
        st.subheader("📖 概念學習")
        
        concept_options = {
            "sharpe_ratio": "夏普比率",
            "max_drawdown": "最大回撤", 
            "beta": "貝塔係數",
            "moving_average": "移動平均線",
            "rsi": "相對強弱指標"
        }
        
        selected_concept = st.selectbox("選擇要學習的概念", 
                                       options=list(concept_options.keys()),
                                       format_func=lambda x: concept_options[x])
        
        if selected_concept:
            self.concept_explainer.explain_concept(selected_concept)
    
    def _show_strategy_simulation(self):
        """顯示策略模擬界面"""
        st.subheader("🎯 策略模擬")
        
        strategy_options = {
            "ma_crossover": "移動平均交叉策略",
            "rsi_reversal": "RSI反轉策略",
            "bollinger_bands": "布林帶策略"
        }
        
        selected_strategy = st.selectbox("選擇策略", 
                                        options=list(strategy_options.keys()),
                                        format_func=lambda x: strategy_options[x])
        
        if selected_strategy:
            strategy_info = self.strategy_simulator.strategies[selected_strategy]
            
            st.write(f"**策略描述**: {strategy_info['description']}")
            st.write(f"**難度等級**: {'⭐' * strategy_info['difficulty']}")
            
            # 參數設置
            st.subheader("參數設置")
            params = {}
            for param_name, param_info in strategy_info['parameters'].items():
                params[param_name] = st.slider(
                    param_name,
                    min_value=param_info['min'],
                    max_value=param_info['max'],
                    value=param_info['default']
                )
            
            # 生成示例數據並運行模擬
            if st.button("運行策略模擬"):
                # 生成示例數據
                np.random.seed(42)
                dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
                prices = 100 + np.cumsum(np.random.normal(0.001, 0.02, 252))
                data = pd.DataFrame({'close': prices}, index=dates)
                
                # 運行模擬
                result = self.strategy_simulator.simulate_strategy(selected_strategy, params, data)
                
                if 'error' not in result:
                    # 顯示結果
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("總收益率", f"{result['total_return']:.2%}")
                    
                    with col2:
                        st.metric("年化波動率", f"{result['volatility']:.2%}")
                    
                    with col3:
                        st.metric("夏普比率", f"{result['sharpe_ratio']:.2f}")
                    
                    # 繪製結果圖表
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=result['data'].index, 
                                           y=result['data']['close'], 
                                           name="價格"))
                    if 'MA_short' in result['data'].columns:
                        fig.add_trace(go.Scatter(x=result['data'].index, 
                                               y=result['data']['MA_short'], 
                                               name="短期均線"))
                        fig.add_trace(go.Scatter(x=result['data'].index, 
                                               y=result['data']['MA_long'], 
                                               name="長期均線"))
                    
                    fig.update_layout(title="策略模擬結果", xaxis_title="日期", yaxis_title="價格")
                    st.plotly_chart(fig, use_container_width=True)
    
    def _show_risk_education(self):
        """顯示風險教育界面"""
        st.subheader("⚠️ 風險教育")
        
        scenario_options = {
            "market_crash": "市場崩盤",
            "high_volatility": "高波動期",
            "sector_rotation": "板塊輪動"
        }
        
        selected_scenario = st.selectbox("選擇風險場景", 
                                        options=list(scenario_options.keys()),
                                        format_func=lambda x: scenario_options[x])
        
        if selected_scenario:
            scenario_info = self.risk_educator.risk_scenarios[selected_scenario]
            st.write(f"**場景描述**: {scenario_info['description']}")
            
            if st.button("模擬風險場景"):
                # 生成示例投資組合數據
                np.random.seed(42)
                dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
                prices = 100 + np.cumsum(np.random.normal(0.001, 0.015, 252))
                portfolio_data = pd.DataFrame({'close': prices}, index=dates)
                
                # 運行風險模擬
                result = self.risk_educator.simulate_risk_scenario(selected_scenario, portfolio_data)
                
                if 'error' not in result:
                    # 顯示風險指標
                    st.metric("最大回撤", f"{result['max_drawdown']:.2%}")
                    
                    # 繪製對比圖
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(y=result['normal_portfolio'], name="正常情況"))
                    fig.add_trace(go.Scatter(y=result['scenario_portfolio'], name="風險場景"))
                    fig.update_layout(title="風險場景對比", yaxis_title="投資組合價值")
                    st.plotly_chart(fig, use_container_width=True)
    
    def _show_progress_tracking(self):
        """顯示進度追蹤界面"""
        st.subheader("📈 學習進度")
        
        # 模擬學習進度數據
        progress_data = {
            "量化交易基礎": 85,
            "技術指標分析": 70,
            "策略開發": 45,
            "風險管理": 30,
            "高級技術": 10
        }
        
        # 進度條顯示
        for topic, progress in progress_data.items():
            st.write(f"**{topic}**")
            st.progress(progress / 100)
            st.write(f"完成度: {progress}%")
            st.write("")
        
        # 學習建議
        st.subheader("💡 個性化學習建議")
        st.info("建議您接下來學習「策略開發」模組，這將幫助您將理論知識應用到實際策略中。")
        
        # 學習統計
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 學習統計")
            stats_data = pd.DataFrame({
                '指標': ['總學習時間', '完成練習', '掌握概念', '策略模擬'],
                '數值': ['12.5小時', '23個', '18個', '8次']
            })
            st.table(stats_data)
        
        with col2:
            st.subheader("🏆 學習成就")
            achievements = [
                "🥉 量化新手 - 完成基礎學習",
                "🥈 策略探索者 - 完成5次策略模擬", 
                "🥇 風險管理師 - 掌握風險控制"
            ]
            for achievement in achievements:
                st.write(achievement)
