# -*- coding: utf-8 -*-
"""
量化交易基礎教育模組

此模組提供量化交易的基礎知識教育，包括：
- 量化交易概念介紹
- 技術分析基礎
- 交易策略類型
- 市場機制說明
- 互動式學習內容

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any
import logging

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


class TradingBasics:
    """
    量化交易基礎教育管理器

    提供量化交易基礎知識的教育內容，包括概念介紹、
    技術分析基礎、策略類型和市場機制說明。

    Attributes:
        course_modules (Dict): 課程模組
        interactive_examples (Dict): 互動式範例
        glossary (Dict): 術語詞典

    Example:
        >>> basics = TradingBasics()
        >>> module = basics.get_module('quantitative_trading')
        >>> basics.show_interactive_example('moving_average')
    """

    def __init__(self):
        """初始化量化交易基礎教育"""
        self.course_modules = self._initialize_course_modules()
        self.interactive_examples = self._initialize_interactive_examples()
        self.glossary = self._initialize_glossary()

    def _initialize_course_modules(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化課程模組

        Returns:
            Dict[str, Dict[str, Any]]: 課程模組字典
        """
        return {
            'quantitative_trading': {
                'title': '什麼是量化交易？',
                'duration': '15分鐘',
                'difficulty': '入門',
                'content': {
                    'introduction': """
                    ## 🤖 量化交易簡介

                    量化交易是使用數學模型、統計方法和電腦程式來進行投資決策的交易方式。
                    它結合了金融理論、數學統計和程式技術，目標是在市場中獲得穩定的收益。

                    ### 核心特點：
                    - **系統化**: 基於明確的規則和邏輯
                    - **客觀性**: 減少情緒化決策
                    - **可重複**: 策略可以重複執行
                    - **可測試**: 可以用歷史資料驗證
                    """,
                    'advantages': [
                        '消除情緒干擾，避免恐懼和貪婪',
                        '24小時監控市場，不會錯過機會',
                        '可以同時處理多個市場和股票',
                        '嚴格執行風險控制規則',
                        '可以回測驗證策略有效性'
                    ],
                    'challenges': [
                        '需要一定的技術和統計知識',
                        '市場環境變化可能影響策略效果',
                        '過度優化可能導致過擬合',
                        '技術故障可能造成損失',
                        '競爭激烈，優勢可能逐漸消失'
                    ]
                }
            },
            'technical_analysis': {
                'title': '技術分析基礎',
                'duration': '20分鐘',
                'difficulty': '入門',
                'content': {
                    'introduction': """
                    ## 📊 技術分析基礎

                    技術分析是通過研究價格圖表和交易量來預測未來價格走勢的方法。
                    它基於三個基本假設：

                    1. **市場行為包含一切信息**
                    2. **價格以趨勢方式移動**
                    3. **歷史會重演**
                    """,
                    'chart_types': {
                        '線圖': '最簡單的圖表，只顯示收盤價',
                        '柱狀圖': '顯示開盤、最高、最低、收盤價',
                        'K線圖': '視覺化的柱狀圖，更容易識別模式',
                        '成交量圖': '顯示交易活躍程度'
                    },
                    'key_concepts': {
                        '支撐位': '價格下跌時遇到的阻力水平',
                        '阻力位': '價格上漲時遇到的阻力水平',
                        '趨勢線': '連接價格高點或低點的直線',
                        '突破': '價格穿越支撐位或阻力位',
                        '成交量': '確認價格走勢的重要指標'
                    }
                }
            },
            'trading_strategies': {
                'title': '交易策略類型',
                'duration': '25分鐘',
                'difficulty': '中級',
                'content': {
                    'introduction': """
                    ## 🎯 交易策略分類

                    量化交易策略可以根據不同的標準進行分類，
                    了解各種策略類型有助於選擇適合的交易方法。
                    """,
                    'by_timeframe': {
                        '高頻交易': '毫秒級，利用微小價差',
                        '日內交易': '當日開倉平倉',
                        '短線交易': '持有數天到數週',
                        '中線交易': '持有數週到數月',
                        '長線投資': '持有數月到數年'
                    },
                    'by_methodology': {
                        '技術分析策略': '基於價格和成交量',
                        '基本面策略': '基於公司財務數據',
                        '量化因子策略': '基於統計因子',
                        '機器學習策略': '使用AI算法',
                        '套利策略': '利用價格差異'
                    }
                }
            },
            'market_mechanics': {
                'title': '市場機制與交易規則',
                'duration': '18分鐘',
                'difficulty': '入門',
                'content': {
                    'introduction': """
                    ## 🏛️ 市場機制

                    了解股票市場的基本運作機制對於量化交易至關重要。
                    這包括交易時間、訂單類型、結算規則等。
                    """,
                    'trading_hours': {
                        '台股': '09:00-13:30 (中午休息)',
                        '美股': '09:30-16:00 EST',
                        '港股': '09:30-12:00, 13:00-16:00'
                    },
                    'order_types': {
                        '市價單': '以當前市價立即成交',
                        '限價單': '指定價格，可能不會立即成交',
                        '停損單': '價格達到設定值時觸發',
                        '停利單': '獲利達到目標時賣出'
                    }
                }
            }
        }

    def _initialize_interactive_examples(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化互動式範例

        Returns:
            Dict[str, Dict[str, Any]]: 互動式範例字典
        """
        return {
            'moving_average': {
                'title': '移動平均線示範',
                'description': '觀察不同週期移動平均線的效果',
                'type': 'chart_demo'
            },
            'support_resistance': {
                'title': '支撐阻力位識別',
                'description': '學習如何識別支撐和阻力位',
                'type': 'interactive_chart'
            },
            'volume_analysis': {
                'title': '成交量分析',
                'description': '理解成交量與價格的關係',
                'type': 'chart_demo'
            },
            'trend_identification': {
                'title': '趨勢識別練習',
                'description': '練習識別上升、下降和橫盤趨勢',
                'type': 'quiz'
            }
        }

    def _initialize_glossary(self) -> Dict[str, str]:
        """
        初始化術語詞典

        Returns:
            Dict[str, str]: 術語詞典
        """
        return {
            '量化交易': '使用數學模型和電腦程式進行的系統化交易',
            '技術分析': '通過研究價格圖表預測未來走勢的方法',
            '基本面分析': '通過研究公司財務狀況評估股票價值',
            '移動平均線': '一定期間內價格的平均值，用於平滑價格波動',
            'RSI': '相對強弱指標，衡量價格變動的速度和幅度',
            '支撐位': '價格下跌過程中可能遇到支撐的價格水平',
            '阻力位': '價格上漲過程中可能遇到阻力的價格水平',
            '突破': '價格穿越重要的支撐或阻力位',
            '回測': '使用歷史資料測試交易策略的過程',
            '滑點': '實際成交價格與預期價格的差異',
            '手續費': '交易時需要支付給券商的費用',
            '停損': '當虧損達到預設水平時自動賣出',
            '止盈': '當獲利達到目標時自動賣出',
            '部位': '持有的股票數量',
            '槓桿': '使用借貸資金放大投資規模',
            '波動率': '價格變動的劇烈程度',
            '夏普比率': '衡量風險調整後收益的指標',
            '最大回撤': '投資組合價值從高點到低點的最大跌幅',
            '勝率': '獲利交易佔總交易次數的比例',
            '風險價值': 'VaR，在一定信心水平下的最大可能損失'
        }

    def get_module(self, module_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取課程模組

        Args:
            module_id: 模組ID

        Returns:
            Optional[Dict[str, Any]]: 課程模組
        """
        return self.course_modules.get(module_id)

    def get_interactive_example(self, example_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取互動式範例

        Args:
            example_id: 範例ID

        Returns:
            Optional[Dict[str, Any]]: 互動式範例
        """
        return self.interactive_examples.get(example_id)

    def search_glossary(self, term: str) -> Optional[str]:
        """
        搜尋術語詞典

        Args:
            term: 搜尋詞彙

        Returns:
            Optional[str]: 詞彙定義
        """
        return self.glossary.get(term)

    def generate_sample_data(self, days: int = 100) -> pd.DataFrame:
        """
        生成示範資料

        Args:
            days: 天數

        Returns:
            pd.DataFrame: 示範股價資料
        """
        np.random.seed(42)

        dates = pd.date_range(start='2023-01-01', periods=days, freq='D')

        # 生成價格序列
        returns = np.random.normal(0.001, 0.02, days)
        prices = 100 * np.exp(np.cumsum(returns))

        # 生成成交量
        volumes = np.random.randint(1000000, 5000000, days)

        return pd.DataFrame({
            'Date': dates,
            'Close': prices,
            'Volume': volumes,
            'Returns': returns
        })


def show_trading_basics() -> None:
    """
    顯示量化交易基礎教育頁面

    提供量化交易基礎知識的教育內容，包括概念介紹、
    技術分析基礎、策略類型和市場機制說明。

    Side Effects:
        - 在 Streamlit 界面顯示基礎教育內容
        - 提供互動式學習體驗
    """
    st.title("📚 量化交易基礎教育")
    st.markdown("從零開始學習量化交易，建立扎實的基礎知識！")

    # 初始化基礎教育管理器
    if 'trading_basics' not in st.session_state:
        st.session_state.trading_basics = TradingBasics()

    basics = st.session_state.trading_basics

    # 課程導航
    st.subheader("📖 課程目錄")

    modules = basics.course_modules
    module_titles = {k: v['title'] for k, v in modules.items()}

    selected_module = st.selectbox(
        "選擇學習模組",
        list(modules.keys()),
        format_func=lambda x: module_titles[x]
    )

    module_info = modules[selected_module]

    # 顯示模組資訊
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("預計時間", module_info['duration'])
    with col2:
        st.metric("難度等級", module_info['difficulty'])
    with col3:
        st.metric("模組", f"{list(modules.keys()).index(selected_module) + 1}/{len(modules)}")

    # 顯示課程內容
    content = module_info['content']

    # 主要內容
    if 'introduction' in content:
        st.markdown(content['introduction'])

    # 根據模組類型顯示特定內容
    if selected_module == 'quantitative_trading':
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("✅ 量化交易的優勢")
            for advantage in content['advantages']:
                st.write(f"• {advantage}")

        with col2:
            st.subheader("⚠️ 面臨的挑戰")
            for challenge in content['challenges']:
                st.write(f"• {challenge}")

    elif selected_module == 'technical_analysis':
        # 圖表類型說明
        st.subheader("📊 圖表類型")
        for chart_type, description in content['chart_types'].items():
            st.write(f"**{chart_type}**: {description}")

        # 關鍵概念
        st.subheader("🔑 關鍵概念")
        for concept, description in content['key_concepts'].items():
            st.write(f"**{concept}**: {description}")

        # 互動式圖表示範
        st.subheader("📈 移動平均線示範")

        # 生成示範資料
        demo_data = basics.generate_sample_data()

        # 移動平均線參數
        col1, col2 = st.columns(2)
        with col1:
            ma_short = st.slider("短期移動平均", 5, 30, 10)
        with col2:
            ma_long = st.slider("長期移動平均", 20, 100, 30)

        # 計算移動平均線
        demo_data[f'MA_{ma_short}'] = demo_data['Close'].rolling(ma_short).mean()
        demo_data[f'MA_{ma_long}'] = demo_data['Close'].rolling(ma_long).mean()

        # 繪製圖表
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=demo_data['Date'],
            y=demo_data['Close'],
            mode='lines',
            name='股價',
            line=dict(color='blue')
        ))

        fig.add_trace(go.Scatter(
            x=demo_data['Date'],
            y=demo_data[f'MA_{ma_short}'],
            mode='lines',
            name=f'MA{ma_short}',
            line=dict(color='red', dash='dash')
        ))

        fig.add_trace(go.Scatter(
            x=demo_data['Date'],
            y=demo_data[f'MA_{ma_long}'],
            mode='lines',
            name=f'MA{ma_long}',
            line=dict(color='green', dash='dash')
        ))

        fig.update_layout(
            title='移動平均線示範',
            xaxis_title='日期',
            yaxis_title='價格',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

        st.info("💡 觀察短期移動平均線與長期移動平均線的交叉點，這些通常被視為買賣信號。")

    elif selected_module == 'trading_strategies':
        # 按時間框架分類
        st.subheader("⏰ 按時間框架分類")
        for strategy, description in content['by_timeframe'].items():
            st.write(f"**{strategy}**: {description}")

        # 按方法論分類
        st.subheader("🔬 按方法論分類")
        for strategy, description in content['by_methodology'].items():
            st.write(f"**{strategy}**: {description}")

        # 策略比較圖表
        st.subheader("📊 策略風險收益比較")

        strategies = ['技術分析', '基本面', '量化因子', '機器學習', '套利']
        risk_levels = [3, 2, 4, 5, 1]
        return_potential = [3, 2, 4, 5, 2]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=risk_levels,
            y=return_potential,
            mode='markers+text',
            text=strategies,
            textposition="middle center",
            marker=dict(size=15, color='lightblue', line=dict(width=2, color='darkblue')),
            name='策略類型'
        ))

        fig.update_layout(
            title='策略風險收益分布',
            xaxis_title='風險等級',
            yaxis_title='收益潛力',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    elif selected_module == 'market_mechanics':
        # 交易時間
        st.subheader("🕐 主要市場交易時間")
        for market, hours in content['trading_hours'].items():
            st.write(f"**{market}**: {hours}")

        # 訂單類型
        st.subheader("📋 訂單類型")
        for order_type, description in content['order_types'].items():
            st.write(f"**{order_type}**: {description}")

    # 術語詞典
    st.subheader("📖 術語詞典")

    search_term = st.text_input("搜尋術語", placeholder="輸入要查詢的術語...")

    if search_term:
        definition = basics.search_glossary(search_term)
        if definition:
            st.success(f"**{search_term}**: {definition}")
        else:
            st.warning(f"找不到術語「{search_term}」")

            # 模糊搜尋
            similar_terms = [term for term in basics.glossary.keys()
                           if search_term.lower() in term.lower()]
            if similar_terms:
                st.write("您是否要找：")
                for term in similar_terms[:5]:
                    if st.button(term, key=f"suggest_{term}"):
                        st.success(f"**{term}**: {basics.glossary[term]}")

    # 顯示所有術語
    with st.expander("查看所有術語", expanded=False):
        for term, definition in basics.glossary.items():
            st.write(f"**{term}**: {definition}")

    # 學習進度追蹤
    st.subheader("📊 學習進度")

    if 'completed_modules' not in st.session_state:
        st.session_state.completed_modules = set()

    if st.button(f"標記「{module_info['title']}」為已完成"):
        st.session_state.completed_modules.add(selected_module)
        st.success("✅ 模組已標記為完成！")

    # 顯示進度
    total_modules = len(modules)
    completed_count = len(st.session_state.completed_modules)
    progress = completed_count / total_modules

    st.progress(progress)
    st.write(f"學習進度: {completed_count}/{total_modules} ({progress:.1%})")

    # 下一步建議
    if completed_count < total_modules:
        remaining_modules = [k for k in modules.keys()
                           if k not in st.session_state.completed_modules]
        next_module = remaining_modules[0]
        next_title = modules[next_module]['title']

        st.info(f"💡 建議下一步學習：{next_title}")
    else:
        st.success("🎉 恭喜！您已完成所有基礎課程！")
        st.info("現在可以開始實際操作，建議前往「策略模板」或「模擬交易」頁面。")

    # 側邊欄：快速導航
    with st.sidebar:
        st.subheader("🧭 快速導航")

        for module_id, module_data in modules.items():
            is_completed = module_id in st.session_state.completed_modules
            status = "✅" if is_completed else "⏳"

            if st.button(f"{status} {module_data['title']}", key=f"nav_{module_id}"):
                # 這裡可以添加跳轉邏輯
                st.info(f"跳轉到：{module_data['title']}")

        # 學習統計
        st.subheader("📈 學習統計")
        st.metric("已完成模組", f"{completed_count}/{total_modules}")
        st.metric("學習進度", f"{progress:.1%}")

        if completed_count > 0:
            avg_time = completed_count * 20  # 假設每模組20分鐘
            st.metric("累計學習時間", f"{avg_time} 分鐘")

        # 相關資源
        st.subheader("📚 相關資源")

        if st.button("📖 進階教程"):
            st.info("進階教程功能開發中...")

        if st.button("🎯 實戰練習"):
            st.info("實戰練習功能開發中...")

        if st.button("❓ 常見問題"):
            st.info("常見問題功能開發中...")