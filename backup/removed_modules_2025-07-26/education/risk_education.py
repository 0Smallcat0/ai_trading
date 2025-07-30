# -*- coding: utf-8 -*-
"""
風險管理教育模組

此模組提供風險管理的教育內容，包括：
- 風險類型介紹
- 風險控制方法
- 風險指標計算
- 實例分析
- 互動式風險評估

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any, Tuple
import logging

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


class RiskEducation:
    """
    風險管理教育管理器
    
    提供風險管理的教育內容，包括風險類型介紹、
    控制方法、指標計算和實例分析。
    
    Attributes:
        risk_concepts (Dict): 風險概念庫
        risk_metrics (Dict): 風險指標定義
        case_studies (Dict): 案例研究
        
    Example:
        >>> education = RiskEducation()
        >>> concept = education.get_risk_concept('market_risk')
        >>> education.calculate_risk_metrics(data)
    """
    
    def __init__(self):
        """初始化風險管理教育"""
        self.risk_concepts = self._initialize_risk_concepts()
        self.risk_metrics = self._initialize_risk_metrics()
        self.case_studies = self._initialize_case_studies()
        
    def _initialize_risk_concepts(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化風險概念庫
        
        Returns:
            Dict[str, Dict[str, Any]]: 風險概念字典
        """
        return {
            'market_risk': {
                'name': '市場風險',
                'definition': '由於整體市場因素變動而導致投資損失的風險',
                'description': """
                ## 📈 市場風險 (Market Risk)
                
                市場風險是指由於市場整體因素變動而導致的投資損失風險。
                這是所有投資者都必須面對的系統性風險。
                
                ### 主要特徵：
                - **系統性風險**：影響整個市場
                - **不可分散**：無法通過分散投資完全消除
                - **週期性**：與經濟週期相關
                - **可預測性低**：難以準確預測時機
                
                ### 影響因素：
                - 經濟成長率變化
                - 通貨膨脹率
                - 利率變動
                - 政治事件
                - 國際情勢
                """,
                'examples': [
                    '2008年金融危機導致全球股市大跌',
                    '2020年疫情爆發引發市場恐慌',
                    '央行升息導致股市下跌',
                    '地緣政治衝突影響市場信心'
                ],
                'management_methods': [
                    '資產配置分散',
                    '使用避險工具',
                    '調整部位大小',
                    '設定停損點',
                    '定期檢視投資組合'
                ]
            },
            'specific_risk': {
                'name': '個股風險',
                'definition': '特定公司或行業面臨的獨特風險',
                'description': """
                ## 🏢 個股風險 (Specific Risk)
                
                個股風險是指特定公司或行業面臨的獨特風險，
                這種風險可以通過分散投資來降低。
                
                ### 主要類型：
                - **營運風險**：公司經營管理問題
                - **財務風險**：財務結構不當
                - **行業風險**：特定行業面臨的挑戰
                - **競爭風險**：市場競爭加劇
                
                ### 風險來源：
                - 公司治理問題
                - 產品競爭力下降
                - 財務槓桿過高
                - 法規變化影響
                - 技術革新衝擊
                """,
                'examples': [
                    '公司財報造假被發現',
                    '主要產品被競爭對手超越',
                    '關鍵管理層離職',
                    '法規變化影響營運',
                    '供應鏈中斷'
                ],
                'management_methods': [
                    '分散投資不同股票',
                    '深入研究公司基本面',
                    '設定個股部位上限',
                    '定期檢視持股',
                    '關注公司新聞動態'
                ]
            },
            'liquidity_risk': {
                'name': '流動性風險',
                'definition': '無法在合理價格下及時買賣資產的風險',
                'description': """
                ## 💧 流動性風險 (Liquidity Risk)
                
                流動性風險是指無法在合理價格下及時買賣資產的風險。
                在市場壓力下，這種風險會顯著增加。
                
                ### 風險表現：
                - **買賣價差擴大**：成交成本增加
                - **成交量萎縮**：難以找到交易對手
                - **價格衝擊**：大額交易影響價格
                - **時間延遲**：無法及時執行交易
                
                ### 影響因素：
                - 股票交易量大小
                - 市場參與者數量
                - 市場情緒狀況
                - 公司規模和知名度
                """,
                'examples': [
                    '小型股在市場恐慌時無人接手',
                    '大額賣單導致股價急跌',
                    '停牌股票無法交易',
                    '市場關閉時無法調整部位'
                ],
                'management_methods': [
                    '選擇流動性好的股票',
                    '避免過度集中投資',
                    '保留現金部位',
                    '分批進出場',
                    '避免在市場關閉前大額交易'
                ]
            },
            'operational_risk': {
                'name': '操作風險',
                'definition': '由於系統故障、人為錯誤或程序缺陷導致的風險',
                'description': """
                ## ⚙️ 操作風險 (Operational Risk)
                
                操作風險是指由於系統故障、人為錯誤或程序缺陷
                而導致的損失風險。在量化交易中尤其重要。
                
                ### 風險來源：
                - **技術故障**：系統當機、網路中斷
                - **人為錯誤**：下錯單、參數設定錯誤
                - **程序缺陷**：策略邏輯錯誤
                - **資料錯誤**：資料來源問題
                
                ### 常見情況：
                - 交易系統當機
                - 資料延遲或錯誤
                - 策略參數設定錯誤
                - 風控系統失效
                """,
                'examples': [
                    '交易系統在關鍵時刻當機',
                    '錯誤的資料導致策略失效',
                    '參數設定錯誤導致過度交易',
                    '風控系統未及時觸發停損'
                ],
                'management_methods': [
                    '建立備援系統',
                    '定期系統測試',
                    '設定多重檢查機制',
                    '建立應急處理程序',
                    '定期備份重要資料'
                ]
            }
        }
    
    def _initialize_risk_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化風險指標定義
        
        Returns:
            Dict[str, Dict[str, Any]]: 風險指標字典
        """
        return {
            'volatility': {
                'name': '波動率',
                'formula': 'σ = √(Σ(Ri - R̄)² / (n-1))',
                'description': '衡量價格變動的劇烈程度',
                'interpretation': {
                    'low': '< 15%：低波動，風險較小',
                    'medium': '15-25%：中等波動，風險適中',
                    'high': '> 25%：高波動，風險較大'
                },
                'calculation_method': 'standard_deviation'
            },
            'max_drawdown': {
                'name': '最大回撤',
                'formula': 'MDD = max((Peak - Trough) / Peak)',
                'description': '投資組合從高點到低點的最大跌幅',
                'interpretation': {
                    'low': '< 10%：回撤較小，風險控制良好',
                    'medium': '10-20%：回撤適中，需要注意',
                    'high': '> 20%：回撤較大，風險較高'
                },
                'calculation_method': 'peak_to_trough'
            },
            'var': {
                'name': '風險價值 (VaR)',
                'formula': 'VaR = μ - z * σ',
                'description': '在一定信心水平下的最大可能損失',
                'interpretation': {
                    '95%': '95%信心水平下的最大損失',
                    '99%': '99%信心水平下的最大損失',
                    '99.9%': '99.9%信心水平下的最大損失'
                },
                'calculation_method': 'parametric'
            },
            'sharpe_ratio': {
                'name': '夏普比率',
                'formula': 'SR = (Rp - Rf) / σp',
                'description': '衡量風險調整後的收益',
                'interpretation': {
                    'excellent': '> 2：優秀',
                    'good': '1-2：良好',
                    'poor': '< 1：較差'
                },
                'calculation_method': 'risk_adjusted_return'
            }
        }
    
    def _initialize_case_studies(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化案例研究
        
        Returns:
            Dict[str, Dict[str, Any]]: 案例研究字典
        """
        return {
            'over_leverage': {
                'title': '過度槓桿的教訓',
                'scenario': '某投資者使用5倍槓桿投資股票',
                'problem': '市場下跌20%，投資者損失100%本金',
                'lesson': '槓桿放大收益的同時也放大風險',
                'prevention': [
                    '謹慎使用槓桿',
                    '設定嚴格的停損點',
                    '分散投資降低風險',
                    '保留足夠的保證金'
                ]
            },
            'concentration_risk': {
                'title': '集中投資的風險',
                'scenario': '投資者將80%資金投入單一科技股',
                'problem': '該股票因醜聞下跌50%，投資組合損失40%',
                'lesson': '過度集中投資會放大個股風險',
                'prevention': [
                    '分散投資不同股票',
                    '限制單一股票比重',
                    '跨行業配置',
                    '定期檢視投資組合'
                ]
            },
            'timing_risk': {
                'title': '市場時機的挑戰',
                'scenario': '投資者試圖預測市場頂部和底部',
                'problem': '頻繁進出場導致交易成本高，收益不佳',
                'lesson': '市場時機難以準確預測',
                'prevention': [
                    '採用定期定額投資',
                    '長期持有優質資產',
                    '避免頻繁交易',
                    '專注於資產配置'
                ]
            }
        }
    
    def get_risk_concept(self, concept_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取風險概念
        
        Args:
            concept_id: 概念ID
            
        Returns:
            Optional[Dict[str, Any]]: 風險概念
        """
        return self.risk_concepts.get(concept_id)
    
    def calculate_risk_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """
        計算風險指標
        
        Args:
            returns: 收益率序列
            
        Returns:
            Dict[str, float]: 風險指標
        """
        # 年化波動率
        volatility = returns.std() * np.sqrt(252)
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # VaR (95% 信心水平)
        var_95 = returns.quantile(0.05)
        
        # 夏普比率 (假設無風險利率2%)
        risk_free_rate = 0.02 / 252  # 日無風險利率
        excess_returns = returns - risk_free_rate
        sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252)
        
        return {
            'volatility': volatility,
            'max_drawdown': abs(max_drawdown),
            'var_95': abs(var_95),
            'sharpe_ratio': sharpe_ratio
        }
    
    def generate_risk_scenario(self, scenario_type: str) -> pd.DataFrame:
        """
        生成風險情境資料
        
        Args:
            scenario_type: 情境類型
            
        Returns:
            pd.DataFrame: 情境資料
        """
        np.random.seed(42)
        days = 252
        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
        
        if scenario_type == 'normal':
            returns = np.random.normal(0.0005, 0.015, days)
        elif scenario_type == 'high_volatility':
            returns = np.random.normal(0.0005, 0.03, days)
        elif scenario_type == 'market_crash':
            returns = np.random.normal(0.0005, 0.015, days)
            # 模擬市場崩盤
            crash_start = 100
            crash_duration = 20
            returns[crash_start:crash_start+crash_duration] = np.random.normal(-0.05, 0.02, crash_duration)
        else:
            returns = np.random.normal(0.0005, 0.015, days)
        
        prices = 100 * np.exp(np.cumsum(returns))
        
        return pd.DataFrame({
            'Date': dates,
            'Price': prices,
            'Returns': returns
        })


def show_risk_education() -> None:
    """
    顯示風險管理教育頁面
    
    提供風險管理的教育內容，包括風險類型介紹、
    控制方法、指標計算和實例分析。
    
    Side Effects:
        - 在 Streamlit 界面顯示風險教育內容
        - 提供互動式風險學習體驗
    """
    st.title("🛡️ 風險管理教育")
    st.markdown("學習風險管理的核心概念，保護您的投資資產！")
    
    # 初始化風險教育管理器
    if 'risk_education' not in st.session_state:
        st.session_state.risk_education = RiskEducation()
    
    education = st.session_state.risk_education
    
    # 主要內容區域
    tab1, tab2, tab3, tab4 = st.tabs(["風險類型", "風險指標", "案例分析", "風險評估"])
    
    with tab1:
        st.subheader("📚 風險類型介紹")
        
        # 風險概念選擇
        concepts = education.risk_concepts
        concept_names = {k: v['name'] for k, v in concepts.items()}
        
        selected_concept = st.selectbox(
            "選擇風險類型",
            list(concepts.keys()),
            format_func=lambda x: concept_names[x]
        )
        
        concept_info = concepts[selected_concept]
        
        # 顯示風險概念
        st.markdown(concept_info['description'])
        
        # 實例說明
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 實際案例")
            for example in concept_info['examples']:
                st.write(f"• {example}")
        
        with col2:
            st.subheader("🛠️ 管理方法")
            for method in concept_info['management_methods']:
                st.write(f"• {method}")
    
    with tab2:
        st.subheader("📊 風險指標計算")
        
        # 風險指標選擇
        metrics = education.risk_metrics
        metric_names = {k: v['name'] for k, v in metrics.items()}
        
        selected_metric = st.selectbox(
            "選擇風險指標",
            list(metrics.keys()),
            format_func=lambda x: metric_names[x]
        )
        
        metric_info = metrics[selected_metric]
        
        # 顯示指標資訊
        st.write(f"**定義**: {metric_info['description']}")
        st.write(f"**公式**: {metric_info['formula']}")
        
        # 解釋標準
        st.subheader("📈 解釋標準")
        for level, description in metric_info['interpretation'].items():
            st.write(f"**{level}**: {description}")
        
        # 實際計算演示
        st.subheader("🧮 計算演示")
        
        # 生成示範資料
        scenario_type = st.selectbox(
            "選擇市場情境",
            ['normal', 'high_volatility', 'market_crash'],
            format_func=lambda x: {
                'normal': '正常市場',
                'high_volatility': '高波動市場',
                'market_crash': '市場崩盤'
            }[x]
        )
        
        demo_data = education.generate_risk_scenario(scenario_type)
        
        # 計算風險指標
        risk_metrics = education.calculate_risk_metrics(demo_data['Returns'])
        
        # 顯示計算結果
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("年化波動率", f"{risk_metrics['volatility']:.2%}")
        with col2:
            st.metric("最大回撤", f"{risk_metrics['max_drawdown']:.2%}")
        with col3:
            st.metric("VaR (95%)", f"{risk_metrics['var_95']:.2%}")
        with col4:
            st.metric("夏普比率", f"{risk_metrics['sharpe_ratio']:.2f}")
        
        # 價格走勢圖
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=demo_data['Date'],
            y=demo_data['Price'],
            mode='lines',
            name='價格',
            line=dict(color='blue')
        ))
        
        fig.update_layout(
            title=f'{scenario_type.replace("_", " ").title()} 市場情境',
            xaxis_title='日期',
            yaxis_title='價格',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("📖 風險案例分析")
        
        # 案例選擇
        cases = education.case_studies
        case_titles = {k: v['title'] for k, v in cases.items()}
        
        selected_case = st.selectbox(
            "選擇案例",
            list(cases.keys()),
            format_func=lambda x: case_titles[x]
        )
        
        case_info = cases[selected_case]
        
        # 顯示案例內容
        st.write(f"**情境**: {case_info['scenario']}")
        st.write(f"**問題**: {case_info['problem']}")
        st.write(f"**教訓**: {case_info['lesson']}")
        
        st.subheader("🛡️ 預防措施")
        for prevention in case_info['prevention']:
            st.write(f"• {prevention}")
        
        # 案例模擬
        if selected_case == 'over_leverage':
            st.subheader("📊 槓桿效應模擬")
            
            col1, col2 = st.columns(2)
            with col1:
                leverage = st.slider("槓桿倍數", 1, 10, 5)
            with col2:
                market_change = st.slider("市場變動 (%)", -50, 50, -20)
            
            # 計算結果
            portfolio_change = market_change * leverage
            
            st.write(f"**市場變動**: {market_change}%")
            st.write(f"**投資組合變動**: {portfolio_change}%")
            
            if portfolio_change <= -100:
                st.error("⚠️ 投資組合完全虧損！")
            elif portfolio_change < -50:
                st.warning("⚠️ 嚴重虧損！")
            elif portfolio_change < 0:
                st.info(f"虧損 {abs(portfolio_change)}%")
            else:
                st.success(f"獲利 {portfolio_change}%")
    
    with tab4:
        st.subheader("🎯 個人風險評估")
        
        # 風險評估問卷
        st.write("**請回答以下問題，評估您的風險承受能力：**")
        
        q1 = st.radio(
            "1. 您能接受的最大年度虧損是多少？",
            ["5%以下", "5-10%", "10-20%", "20%以上"]
        )
        
        q2 = st.radio(
            "2. 當投資虧損15%時，您會如何反應？",
            ["立即賣出", "減少部位", "保持不變", "加碼投資"]
        )
        
        q3 = st.radio(
            "3. 您的投資期限是多久？",
            ["1年以下", "1-3年", "3-5年", "5年以上"]
        )
        
        q4 = st.radio(
            "4. 您對投資波動的容忍度如何？",
            ["完全不能接受", "輕微波動可接受", "中等波動可接受", "大幅波動可接受"]
        )
        
        if st.button("計算風險評分"):
            # 簡單評分系統
            score = 0
            
            score += {"5%以下": 1, "5-10%": 2, "10-20%": 3, "20%以上": 4}[q1]
            score += {"立即賣出": 1, "減少部位": 2, "保持不變": 3, "加碼投資": 4}[q2]
            score += {"1年以下": 1, "1-3年": 2, "3-5年": 3, "5年以上": 4}[q3]
            score += {"完全不能接受": 1, "輕微波動可接受": 2, "中等波動可接受": 3, "大幅波動可接受": 4}[q4]
            
            # 風險等級判定
            if score <= 8:
                risk_level = "保守型"
                color = "green"
                recommendation = "建議選擇低風險投資，如債券或穩健型基金"
            elif score <= 12:
                risk_level = "穩健型"
                color = "orange"
                recommendation = "建議平衡配置股票和債券，控制風險"
            else:
                risk_level = "積極型"
                color = "red"
                recommendation = "可以承受較高風險，但仍需注意分散投資"
            
            st.success(f"您的風險等級：**{risk_level}**")
            st.info(f"建議：{recommendation}")
            
            # 風險配置建議
            st.subheader("📊 建議資產配置")
            
            if risk_level == "保守型":
                allocation = {"股票": 30, "債券": 60, "現金": 10}
            elif risk_level == "穩健型":
                allocation = {"股票": 60, "債券": 30, "現金": 10}
            else:
                allocation = {"股票": 80, "債券": 15, "現金": 5}
            
            fig = px.pie(
                values=list(allocation.values()),
                names=list(allocation.keys()),
                title="建議資產配置"
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # 側邊欄：風險管理工具
    with st.sidebar:
        st.subheader("🛠️ 風險管理工具")
        
        # 部位大小計算器
        st.write("**部位大小計算器**")
        
        total_capital = st.number_input("總資金", value=100000, step=10000)
        risk_per_trade = st.slider("單筆風險 (%)", 1, 10, 2) / 100
        stop_loss = st.slider("停損比例 (%)", 1, 20, 5) / 100
        
        position_size = (total_capital * risk_per_trade) / stop_loss
        position_ratio = position_size / total_capital
        
        st.write(f"建議部位大小：${position_size:,.0f}")
        st.write(f"佔總資金比例：{position_ratio:.1%}")
        
        # 風險提醒
        st.subheader("⚠️ 風險提醒")
        
        st.warning("投資有風險，入市需謹慎")
        st.info("分散投資是降低風險的最佳方法")
        st.error("永遠不要投入無法承受損失的資金")
        
        # 相關資源
        st.subheader("📚 相關資源")
        
        if st.button("📊 風險評估工具"):
            st.info("風險評估工具功能開發中...")
        
        if st.button("🎯 投資組合分析"):
            st.info("投資組合分析功能開發中...")
        
        if st.button("📖 風險管理指南"):
            st.info("風險管理指南功能開發中...")
