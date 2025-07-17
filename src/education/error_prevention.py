# -*- coding: utf-8 -*-
"""
常見錯誤預防系統

此模組提供常見錯誤的預防和警告功能，包括：
- 常見錯誤類型識別
- 預防措施建議
- 實時警告系統
- 錯誤案例分析
- 最佳實踐指南

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


class ErrorPrevention:
    """
    常見錯誤預防系統

    提供常見錯誤的識別、預防和警告功能，包括錯誤類型分析、
    預防措施建議和實時警告系統。

    Attributes:
        common_errors (Dict): 常見錯誤庫
        prevention_strategies (Dict): 預防策略
        warning_rules (Dict): 警告規則

    Example:
        >>> prevention = ErrorPrevention()
        >>> errors = prevention.check_common_errors(config)
        >>> prevention.get_prevention_advice('overtrading')
    """

    def __init__(self):
        """初始化錯誤預防系統"""
        self.common_errors = self._initialize_common_errors()
        self.prevention_strategies = self._initialize_prevention_strategies()
        self.warning_rules = self._initialize_warning_rules()

    def _initialize_common_errors(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化常見錯誤庫

        Returns:
            Dict[str, Dict[str, Any]]: 常見錯誤字典
        """
        return {
            'overtrading': {
                'name': '過度交易',
                'category': '行為錯誤',
                'severity': 'high',
                'description': """
                ## 🔄 過度交易 (Overtrading)

                過度交易是新手最常犯的錯誤之一，指的是交易頻率過高，
                導致交易成本增加而收益下降。

                ### 表現形式：
                - 每天都要進行交易
                - 看到任何信號就立即行動
                - 頻繁調整投資組合
                - 追漲殺跌的行為

                ### 危害：
                - 交易成本累積過高
                - 增加犯錯機會
                - 情緒化決策增加
                - 偏離長期投資目標
                """,
                'warning_signs': [
                    '每日交易次數超過5次',
                    '月交易成本超過資金的1%',
                    '持股期間平均少於5天',
                    '頻繁修改策略參數'
                ],
                'consequences': [
                    '交易成本侵蝕收益',
                    '策略效果無法驗證',
                    '心理壓力增加',
                    '長期績效不佳'
                ],
                'prevention': [
                    '設定最小持有期間',
                    '限制每日交易次數',
                    '計算交易成本影響',
                    '制定明確的交易計劃'
                ]
            },
            'lack_diversification': {
                'name': '缺乏分散投資',
                'category': '投資組合錯誤',
                'severity': 'high',
                'description': """
                ## 🎯 缺乏分散投資

                將過多資金集中在少數股票或單一行業，
                增加投資組合的整體風險。

                ### 常見情況：
                - 單一股票佔比超過20%
                - 只投資單一行業
                - 地理位置過度集中
                - 投資期限過於一致

                ### 風險：
                - 個股風險放大
                - 行業風險集中
                - 缺乏風險緩衝
                - 波動率過高
                """,
                'warning_signs': [
                    '單一股票佔比超過20%',
                    '前三大持股佔比超過50%',
                    '只投資單一行業',
                    '所有股票相關性過高'
                ],
                'consequences': [
                    '投資組合波動率過高',
                    '單一事件影響巨大',
                    '風險調整後收益下降',
                    '心理壓力增加'
                ],
                'prevention': [
                    '限制單一股票比重',
                    '跨行業配置',
                    '定期檢視相關性',
                    '使用分散投資工具'
                ]
            },
            'ignoring_risk_management': {
                'name': '忽視風險管理',
                'category': '風險控制錯誤',
                'severity': 'critical',
                'description': """
                ## 🛡️ 忽視風險管理

                不設定停損點、不控制部位大小、不評估風險，
                是導致重大損失的主要原因。

                ### 表現：
                - 不設定停損點
                - 部位大小隨意決定
                - 不計算風險指標
                - 忽視市場環境變化

                ### 後果：
                - 可能面臨巨大損失
                - 無法控制風險暴露
                - 情緒化決策增加
                - 長期績效不穩定
                """,
                'warning_signs': [
                    '沒有設定停損點',
                    '單一部位超過總資金30%',
                    '不監控投資組合風險',
                    '忽視市場環境變化'
                ],
                'consequences': [
                    '可能面臨重大損失',
                    '無法控制下檔風險',
                    '投資組合不穩定',
                    '心理創傷'
                ],
                'prevention': [
                    '強制設定停損點',
                    '限制單一部位大小',
                    '定期計算風險指標',
                    '建立風險監控機制'
                ]
            },
            'emotional_trading': {
                'name': '情緒化交易',
                'category': '心理錯誤',
                'severity': 'medium',
                'description': """
                ## 😰 情緒化交易

                受恐懼、貪婪等情緒影響而做出非理性的交易決策，
                偏離原定的投資策略。

                ### 常見情緒：
                - **恐懼**：市場下跌時恐慌賣出
                - **貪婪**：市場上漲時追高買入
                - **後悔**：錯過機會後衝動交易
                - **過度自信**：連續獲利後增加風險

                ### 影響：
                - 買高賣低
                - 偏離策略
                - 增加交易頻率
                - 風險控制失效
                """,
                'warning_signs': [
                    '在市場恐慌時大量賣出',
                    '在市場狂熱時大量買入',
                    '頻繁改變投資策略',
                    '忽視既定的風險規則'
                ],
                'consequences': [
                    '買高賣低的惡性循環',
                    '策略一致性破壞',
                    '長期績效不佳',
                    '心理壓力增加'
                ],
                'prevention': [
                    '制定明確的交易規則',
                    '使用自動化交易',
                    '定期檢視交易記錄',
                    '學習情緒管理技巧'
                ]
            },
            'parameter_overfitting': {
                'name': '參數過度優化',
                'category': '技術錯誤',
                'severity': 'medium',
                'description': """
                ## 🔧 參數過度優化

                過度調整策略參數以適應歷史資料，
                導致策略在實際交易中表現不佳。

                ### 表現：
                - 頻繁調整策略參數
                - 追求完美的回測結果
                - 使用過多的技術指標
                - 忽視樣本外測試

                ### 問題：
                - 策略過度擬合歷史資料
                - 實際表現與回測差異大
                - 策略穩定性差
                - 適應性不足
                """,
                'warning_signs': [
                    '回測結果過於完美',
                    '參數調整過於頻繁',
                    '使用過多技術指標',
                    '忽視樣本外驗證'
                ],
                'consequences': [
                    '實際績效與回測差異大',
                    '策略穩定性差',
                    '市場適應性不足',
                    '信心受到打擊'
                ],
                'prevention': [
                    '使用樣本外測試',
                    '保持參數簡單',
                    '定期驗證策略',
                    '關注策略邏輯合理性'
                ]
            },
            'insufficient_capital': {
                'name': '資金不足',
                'category': '資金管理錯誤',
                'severity': 'medium',
                'description': """
                ## 💰 資金不足

                使用過少的資金進行量化交易，
                導致無法有效分散風險或承受正常波動。

                ### 問題：
                - 無法充分分散投資
                - 交易成本比例過高
                - 心理壓力過大
                - 策略執行困難

                ### 建議最低資金：
                - 股票投資：至少10萬元
                - 量化策略：至少50萬元
                - 多策略組合：至少100萬元
                """,
                'warning_signs': [
                    '總資金少於10萬元',
                    '無法買入5檔以上股票',
                    '交易成本超過收益5%',
                    '心理壓力過大'
                ],
                'consequences': [
                    '無法有效分散風險',
                    '交易成本比例過高',
                    '策略執行受限',
                    '心理壓力過大'
                ],
                'prevention': [
                    '累積足夠資金再開始',
                    '使用ETF等工具',
                    '降低交易頻率',
                    '選擇低成本券商'
                ]
            }
        }

    def _initialize_prevention_strategies(self) -> Dict[str, List[str]]:
        """
        初始化預防策略

        Returns:
            Dict[str, List[str]]: 預防策略字典
        """
        return {
            'general': [
                '制定明確的投資計劃',
                '設定嚴格的風險控制規則',
                '定期檢視和評估績效',
                '持續學習和改進',
                '保持理性和紀律'
            ],
            'technical': [
                '使用樣本外測試驗證策略',
                '避免過度優化參數',
                '建立多重驗證機制',
                '定期更新和維護系統',
                '備份重要資料和程式'
            ],
            'psychological': [
                '制定交易規則並嚴格執行',
                '使用自動化交易減少情緒干擾',
                '定期檢討交易決策',
                '學習情緒管理技巧',
                '尋求專業建議'
            ],
            'risk_management': [
                '設定停損和止盈點',
                '控制單一部位大小',
                '分散投資降低風險',
                '定期計算風險指標',
                '建立應急處理程序'
            ]
        }

    def _initialize_warning_rules(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化警告規則

        Returns:
            Dict[str, Dict[str, Any]]: 警告規則字典
        """
        return {
            'high_concentration': {
                'condition': 'single_position_ratio > 0.2',
                'message': '單一股票佔比過高，建議分散投資',
                'severity': 'warning',
                'action': '考慮減少部位或增加其他投資'
            },
            'no_stop_loss': {
                'condition': 'stop_loss_not_set',
                'message': '未設定停損點，風險過高',
                'severity': 'error',
                'action': '立即設定停損點'
            },
            'excessive_trading': {
                'condition': 'daily_trades > 5',
                'message': '交易頻率過高，可能導致過度交易',
                'severity': 'warning',
                'action': '檢視交易策略，減少不必要交易'
            },
            'high_volatility': {
                'condition': 'portfolio_volatility > 0.3',
                'message': '投資組合波動率過高',
                'severity': 'warning',
                'action': '考慮增加穩定性資產'
            }
        }

    def check_common_errors(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        檢查常見錯誤

        Args:
            config: 配置參數

        Returns:
            List[Dict[str, Any]]: 發現的錯誤清單
        """
        errors = []

        # 檢查部位集中度
        if config.get('position_size', 0) > 0.2:
            errors.append({
                'type': 'lack_diversification',
                'message': '單一部位過大，建議分散投資',
                'severity': 'high'
            })

        # 檢查停損設定
        if not config.get('stop_loss'):
            errors.append({
                'type': 'ignoring_risk_management',
                'message': '未設定停損點，風險過高',
                'severity': 'critical'
            })

        # 檢查交易頻率
        if config.get('rebalance_frequency') == 'daily' and config.get('position_size', 0) < 0.1:
            errors.append({
                'type': 'overtrading',
                'message': '可能存在過度交易風險',
                'severity': 'medium'
            })

        # 檢查資金充足性
        if config.get('initial_capital', 0) < 100000:
            errors.append({
                'type': 'insufficient_capital',
                'message': '資金可能不足以有效執行策略',
                'severity': 'medium'
            })

        return errors

    def get_prevention_advice(self, error_type: str) -> Optional[Dict[str, Any]]:
        """
        獲取預防建議

        Args:
            error_type: 錯誤類型

        Returns:
            Optional[Dict[str, Any]]: 預防建議
        """
        if error_type in self.common_errors:
            error_info = self.common_errors[error_type]
            return {
                'prevention_measures': error_info['prevention'],
                'warning_signs': error_info['warning_signs'],
                'consequences': error_info['consequences']
            }
        return None

    def generate_error_report(self, errors: List[Dict[str, Any]]) -> str:
        """
        生成錯誤報告

        Args:
            errors: 錯誤清單

        Returns:
            str: 錯誤報告
        """
        if not errors:
            return "✅ 未發現常見錯誤，配置良好！"

        report = "⚠️ 發現以下潛在問題：\n\n"

        for i, error in enumerate(errors, 1):
            severity_icon = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }.get(error['severity'], '⚪')

            report += f"{i}. {severity_icon} {error['message']}\n"

        return report


def show_error_prevention() -> None:
    """
    顯示錯誤預防系統頁面

    提供常見錯誤的識別、預防和警告功能，包括錯誤類型分析、
    預防措施建議和實時警告系統。

    Side Effects:
        - 在 Streamlit 界面顯示錯誤預防內容
        - 提供錯誤檢查和預防建議
    """
    st.title("🚨 錯誤預防系統")
    st.markdown("學習識別和預防常見的交易錯誤，避免不必要的損失！")

    # 初始化錯誤預防系統
    if 'error_prevention' not in st.session_state:
        st.session_state.error_prevention = ErrorPrevention()

    prevention = st.session_state.error_prevention

    # 主要內容區域
    tab1, tab2, tab3, tab4 = st.tabs(["常見錯誤", "錯誤檢查", "預防策略", "最佳實踐"])

    with tab1:
        st.subheader("📚 常見錯誤類型")

        # 錯誤類型選擇
        errors = prevention.common_errors
        error_names = {k: v['name'] for k, v in errors.items()}

        selected_error = st.selectbox(
            "選擇錯誤類型",
            list(errors.keys()),
            format_func=lambda x: error_names[x]
        )

        error_info = errors[selected_error]

        # 顯示錯誤資訊
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("錯誤類別", error_info['category'])
        with col2:
            severity_color = {
                'critical': '🔴 嚴重',
                'high': '🟠 高',
                'medium': '🟡 中等',
                'low': '🟢 低'
            }
            st.metric("嚴重程度", severity_color[error_info['severity']])
        with col3:
            st.metric("影響範圍", "投資績效")

        # 錯誤描述
        st.markdown(error_info['description'])

        # 警告信號
        st.subheader("⚠️ 警告信號")
        for sign in error_info['warning_signs']:
            st.write(f"• {sign}")

        # 可能後果
        st.subheader("💥 可能後果")
        for consequence in error_info['consequences']:
            st.write(f"• {consequence}")

        # 預防措施
        st.subheader("🛡️ 預防措施")
        for measure in error_info['prevention']:
            st.write(f"• {measure}")

        # 錯誤嚴重程度統計
        st.subheader("📊 錯誤嚴重程度分布")

        severity_counts = {}
        for error_data in errors.values():
            severity = error_data['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        fig = px.pie(
            values=list(severity_counts.values()),
            names=list(severity_counts.keys()),
            title="錯誤嚴重程度分布",
            color_discrete_map={
                'critical': '#dc3545',
                'high': '#fd7e14',
                'medium': '#ffc107',
                'low': '#28a745'
            }
        )

        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("🔍 配置錯誤檢查")

        st.write("輸入您的交易配置，系統將檢查潛在錯誤：")

        # 配置輸入
        col1, col2 = st.columns(2)

        with col1:
            initial_capital = st.number_input("初始資金", value=100000, step=10000)
            position_size = st.slider("單一部位比例", 0.01, 0.5, 0.1, 0.01)
            max_positions = st.slider("最大持倉數", 1, 20, 5)

        with col2:
            stop_loss = st.slider("停損比例", 0.0, 0.2, 0.05, 0.01)
            rebalance_freq = st.selectbox("調整頻率", ['daily', 'weekly', 'monthly'])
            use_stop_loss = st.checkbox("使用停損", value=True)

        # 構建配置字典
        config = {
            'initial_capital': initial_capital,
            'position_size': position_size,
            'max_positions': max_positions,
            'stop_loss': stop_loss if use_stop_loss else None,
            'rebalance_frequency': rebalance_freq
        }

        # 執行錯誤檢查
        if st.button("🔍 執行錯誤檢查"):
            detected_errors = prevention.check_common_errors(config)

            if not detected_errors:
                st.success("✅ 未發現明顯錯誤，配置看起來不錯！")
            else:
                st.warning(f"⚠️ 發現 {len(detected_errors)} 個潛在問題：")

                for i, error in enumerate(detected_errors, 1):
                    severity_icon = {
                        'critical': '🔴',
                        'high': '🟠',
                        'medium': '🟡',
                        'low': '🟢'
                    }.get(error['severity'], '⚪')

                    st.write(f"{i}. {severity_icon} {error['message']}")

                    # 顯示詳細建議
                    if error['type'] in prevention.common_errors:
                        with st.expander(f"查看 {prevention.common_errors[error['type']]['name']} 的詳細建議"):
                            advice = prevention.get_prevention_advice(error['type'])
                            if advice:
                                st.write("**預防措施：**")
                                for measure in advice['prevention_measures']:
                                    st.write(f"• {measure}")

        # 風險評分
        st.subheader("📊 風險評分")

        # 簡單的風險評分算法
        risk_score = 0

        # 部位大小風險
        if position_size > 0.2:
            risk_score += 3
        elif position_size > 0.15:
            risk_score += 2
        elif position_size > 0.1:
            risk_score += 1

        # 停損設定風險
        if not use_stop_loss:
            risk_score += 4
        elif stop_loss < 0.02:
            risk_score += 2
        elif stop_loss > 0.1:
            risk_score += 1

        # 分散程度風險
        total_allocation = position_size * max_positions
        if total_allocation > 0.8:
            risk_score += 2
        elif total_allocation > 0.6:
            risk_score += 1

        # 資金充足性風險
        if initial_capital < 50000:
            risk_score += 3
        elif initial_capital < 100000:
            risk_score += 1

        # 顯示風險評分
        max_score = 12
        risk_percentage = (risk_score / max_score) * 100

        if risk_score <= 3:
            risk_level = "低風險"
            color = "green"
        elif risk_score <= 6:
            risk_level = "中等風險"
            color = "orange"
        else:
            risk_level = "高風險"
            color = "red"

        st.metric("風險評分", f"{risk_score}/{max_score} ({risk_level})")

        # 風險評分條
        progress_color = {"green": 0.3, "orange": 0.6, "red": 1.0}[color]
        st.progress(risk_percentage / 100)

        if risk_score > 6:
            st.error("⚠️ 配置風險較高，建議調整參數")
        elif risk_score > 3:
            st.warning("⚠️ 配置風險適中，可以進一步優化")
        else:
            st.success("✅ 配置風險較低，設定合理")

    with tab3:
        st.subheader("🛡️ 預防策略指南")

        strategies = prevention.prevention_strategies

        for category, strategy_list in strategies.items():
            category_names = {
                'general': '🎯 一般策略',
                'technical': '🔧 技術策略',
                'psychological': '🧠 心理策略',
                'risk_management': '🛡️ 風險管理策略'
            }

            with st.expander(category_names.get(category, category), expanded=False):
                for strategy in strategy_list:
                    st.write(f"• {strategy}")

        # 預防策略重要性排名
        st.subheader("📊 預防策略重要性排名")

        importance_data = {
            '風險管理': 95,
            '情緒控制': 85,
            '分散投資': 80,
            '技術驗證': 75,
            '持續學習': 70
        }

        fig = px.bar(
            x=list(importance_data.values()),
            y=list(importance_data.keys()),
            orientation='h',
            title='預防策略重要性評分',
            color=list(importance_data.values()),
            color_continuous_scale='RdYlGn'
        )

        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        # 實施建議
        st.subheader("💡 實施建議")

        st.info("""
        **階段性實施預防策略：**

        1. **第一階段（立即實施）**
           - 設定停損點
           - 限制單一部位大小
           - 制定基本交易規則

        2. **第二階段（1週內）**
           - 建立風險監控機制
           - 制定詳細投資計劃
           - 學習情緒管理技巧

        3. **第三階段（1個月內）**
           - 完善技術驗證流程
           - 建立績效評估體系
           - 持續學習和改進
        """)

    with tab4:
        st.subheader("🏆 最佳實踐指南")

        # 最佳實踐清單
        best_practices = {
            '交易前準備': [
                '制定詳細的交易計劃',
                '設定明確的風險參數',
                '準備充足的資金',
                '選擇合適的交易工具',
                '測試交易系統'
            ],
            '交易執行': [
                '嚴格執行交易規則',
                '避免情緒化決策',
                '及時記錄交易過程',
                '監控風險指標',
                '保持冷靜和紀律'
            ],
            '交易後檢討': [
                '分析交易結果',
                '檢討決策過程',
                '更新交易記錄',
                '調整策略參數',
                '總結經驗教訓'
            ],
            '持續改進': [
                '定期評估績效',
                '學習新的知識',
                '優化交易策略',
                '改進風險管理',
                '保持學習心態'
            ]
        }

        for phase, practices in best_practices.items():
            with st.expander(f"📋 {phase}", expanded=False):
                for practice in practices:
                    st.write(f"✓ {practice}")

        # 成功交易者特質
        st.subheader("🌟 成功交易者的特質")

        traits_data = {
            '紀律性': 90,
            '耐心': 85,
            '學習能力': 80,
            '風險意識': 95,
            '情緒控制': 88,
            '分析能力': 75,
            '適應性': 70,
            '決斷力': 82
        }

        fig = go.Figure()

        fig.add_trace(go.Scatterpolar(
            r=list(traits_data.values()),
            theta=list(traits_data.keys()),
            fill='toself',
            name='成功交易者特質'
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=True,
            title="成功交易者特質雷達圖"
        )

        st.plotly_chart(fig, use_container_width=True)

        # 行動計劃模板
        st.subheader("📝 個人行動計劃")

        with st.form("action_plan"):
            st.write("**制定您的個人改進計劃：**")

            current_weakness = st.selectbox(
                "您認為自己最需要改進的方面是？",
                ['風險管理', '情緒控制', '技術分析', '資金管理', '策略執行']
            )

            improvement_goal = st.text_area(
                "具體改進目標",
                placeholder="例如：在未來一個月內，將單一部位比例控制在10%以下..."
            )

            action_steps = st.text_area(
                "具體行動步驟",
                placeholder="例如：1. 重新設定部位大小參數 2. 每週檢視風險指標..."
            )

            timeline = st.selectbox(
                "預計完成時間",
                ['1週內', '2週內', '1個月內', '3個月內']
            )

            if st.form_submit_button("💾 保存行動計劃"):
                st.success("✅ 行動計劃已保存！")
                st.info(f"""
                **您的改進計劃：**

                **改進重點**: {current_weakness}
                **目標**: {improvement_goal}
                **行動步驟**: {action_steps}
                **時間框架**: {timeline}

                建議定期檢視進度並調整計劃。
                """)

    # 側邊欄：快速檢查工具
    with st.sidebar:
        st.subheader("🔧 快速檢查工具")

        # 部位大小檢查
        st.write("**部位大小檢查**")
        total_capital = st.number_input("總資金", value=100000, step=10000, key="sidebar_capital")
        position_value = st.number_input("單一部位金額", value=10000, step=1000, key="sidebar_position")

        if total_capital > 0:
            position_ratio = position_value / total_capital
            st.write(f"部位比例: {position_ratio:.1%}")

            if position_ratio > 0.2:
                st.error("⚠️ 部位過大")
            elif position_ratio > 0.15:
                st.warning("⚠️ 部位偏大")
            else:
                st.success("✅ 部位合理")

        # 風險快速評估
        st.subheader("⚡ 風險快速評估")

        has_stop_loss = st.checkbox("已設定停損", key="sidebar_stop_loss")
        is_diversified = st.checkbox("已分散投資", key="sidebar_diversified")
        has_plan = st.checkbox("有交易計劃", key="sidebar_plan")

        risk_factors = [has_stop_loss, is_diversified, has_plan]
        risk_score = sum(risk_factors)

        if risk_score == 3:
            st.success("✅ 風險控制良好")
        elif risk_score == 2:
            st.warning("⚠️ 需要改進")
        else:
            st.error("🔴 風險較高")

        # 緊急聯絡
        st.subheader("🆘 緊急情況")

        if st.button("🔴 市場崩盤應對"):
            st.error("""
            **市場崩盤應對措施：**
            1. 保持冷靜，不要恐慌
            2. 檢查停損設定
            3. 評估現金部位
            4. 避免衝動交易
            5. 等待市場穩定
            """)

        if st.button("📞 尋求幫助"):
            st.info("""
            **獲得幫助的途徑：**
            - 查閱系統文檔
            - 聯繫客服支援
            - 參與社群討論
            - 諮詢專業顧問
            """)