# -*- coding: utf-8 -*-
"""
錯誤分析工具

此模組提供交易錯誤的深度分析功能，包括：
- 錯誤模式識別
- 錯誤成本計算
- 錯誤頻率分析
- 改正建議生成
- 學習進度追蹤

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

logger = logging.getLogger(__name__)


class MistakeAnalyzer:
    """
    錯誤分析工具

    提供交易錯誤的深度分析功能，幫助用戶識別、
    理解和改正常見的交易錯誤。

    Attributes:
        mistake_records (List): 錯誤記錄
        mistake_categories (Dict): 錯誤分類
        learning_progress (Dict): 學習進度

    Example:
        >>> analyzer = MistakeAnalyzer()
        >>> analyzer.record_mistake('overtrading', '今天交易過於頻繁', -0.02)
        >>> analysis = analyzer.analyze_mistake_patterns()
    """

    def __init__(self):
        """初始化錯誤分析工具"""
        self.mistake_records = []
        self.mistake_categories = self._initialize_mistake_categories()
        self.learning_progress = self._initialize_learning_progress()

    def _initialize_mistake_categories(self) -> Dict[str, Dict[str, Any]]:
        """
        初始化錯誤分類

        Returns:
            Dict[str, Dict[str, Any]]: 錯誤分類字典
        """
        return {
            'overtrading': {
                'name': '過度交易',
                'description': '交易頻率過高，導致交易成本增加',
                'severity': 'high',
                'common_causes': [
                    '缺乏耐心等待好機會',
                    '情緒化決策',
                    '對市場過度反應',
                    '沒有明確的交易計劃'
                ],
                'prevention_tips': [
                    '制定明確的交易規則',
                    '設定每日最大交易次數',
                    '計算交易成本影響',
                    '培養耐心等待的習慣'
                ],
                'cost_impact': 'high'
            },
            'poor_timing': {
                'name': '進出場時機不當',
                'description': '在不適當的時機進入或退出市場',
                'severity': 'high',
                'common_causes': [
                    '缺乏技術分析技能',
                    '忽視市場環境',
                    '情緒化決策',
                    '沒有等待確認信號'
                ],
                'prevention_tips': [
                    '學習技術分析方法',
                    '等待明確的進場信號',
                    '考慮市場整體環境',
                    '使用止損保護部位'
                ],
                'cost_impact': 'high'
            },
            'inadequate_risk_management': {
                'name': '風險管理不當',
                'description': '沒有適當控制風險，導致過大損失',
                'severity': 'critical',
                'common_causes': [
                    '沒有設定停損點',
                    '部位過大',
                    '沒有分散投資',
                    '忽視風險評估'
                ],
                'prevention_tips': [
                    '強制設定停損點',
                    '控制單一部位大小',
                    '分散投資組合',
                    '定期評估風險'
                ],
                'cost_impact': 'critical'
            },
            'emotional_decisions': {
                'name': '情緒化決策',
                'description': '受恐懼、貪婪等情緒影響做出錯誤決策',
                'severity': 'medium',
                'common_causes': [
                    '市場恐慌時賣出',
                    '市場狂熱時買入',
                    '報復性交易',
                    '過度自信'
                ],
                'prevention_tips': [
                    '制定交易規則並嚴格執行',
                    '使用自動化交易',
                    '學習情緒管理技巧',
                    '定期檢討交易決策'
                ],
                'cost_impact': 'medium'
            },
            'insufficient_research': {
                'name': '研究不足',
                'description': '沒有充分研究就進行交易',
                'severity': 'medium',
                'common_causes': [
                    '急於進場',
                    '依賴小道消息',
                    '忽視基本面分析',
                    '沒有驗證資訊來源'
                ],
                'prevention_tips': [
                    '建立研究檢查清單',
                    '多方驗證資訊',
                    '學習基本面分析',
                    '保持懷疑態度'
                ],
                'cost_impact': 'medium'
            },
            'ignoring_stop_loss': {
                'name': '忽視停損',
                'description': '沒有執行預設的停損策略',
                'severity': 'high',
                'common_causes': [
                    '希望價格反彈',
                    '不願承認錯誤',
                    '移動停損點',
                    '情緒化堅持'
                ],
                'prevention_tips': [
                    '嚴格執行停損規則',
                    '使用自動停損單',
                    '接受小額損失',
                    '學習認錯的重要性'
                ],
                'cost_impact': 'high'
            }
        }

    def _initialize_learning_progress(self) -> Dict[str, Any]:
        """
        初始化學習進度

        Returns:
            Dict[str, Any]: 學習進度字典
        """
        return {
            'total_mistakes': 0,
            'resolved_mistakes': 0,
            'improvement_rate': 0.0,
            'last_mistake_date': None,
            'mistake_free_days': 0,
            'learning_milestones': []
        }

    def record_mistake(self, mistake_type: str, description: str,
                      cost_impact: float = 0.0, trade_id: str = '',
                      lessons_learned: str = '') -> str:
        """
        記錄交易錯誤

        Args:
            mistake_type: 錯誤類型
            description: 錯誤描述
            cost_impact: 成本影響（負數表示損失）
            trade_id: 相關交易ID
            lessons_learned: 學習心得

        Returns:
            str: 錯誤記錄ID
        """
        mistake_id = f"mistake_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        mistake_record = {
            'id': mistake_id,
            'timestamp': datetime.now().isoformat(),
            'mistake_type': mistake_type,
            'description': description,
            'cost_impact': cost_impact,
            'trade_id': trade_id,
            'lessons_learned': lessons_learned,
            'severity': self.mistake_categories.get(mistake_type, {}).get('severity', 'medium'),
            'resolved': False,
            'resolution_date': None,
            'prevention_actions': [],
            'recurrence_count': 1
        }

        # 檢查是否為重複錯誤
        similar_mistakes = [
            m for m in self.mistake_records
            if m['mistake_type'] == mistake_type and
            (datetime.now() - datetime.fromisoformat(m['timestamp'])).days <= 30
        ]

        if similar_mistakes:
            mistake_record['recurrence_count'] = len(similar_mistakes) + 1

        self.mistake_records.append(mistake_record)
        self._update_learning_progress()

        logger.info("錯誤已記錄: %s - %s", mistake_id, mistake_type)

        return mistake_id

    def _update_learning_progress(self) -> None:
        """更新學習進度"""
        total_mistakes = len(self.mistake_records)
        resolved_mistakes = len([m for m in self.mistake_records if m['resolved']])

        self.learning_progress.update({
            'total_mistakes': total_mistakes,
            'resolved_mistakes': resolved_mistakes,
            'improvement_rate': resolved_mistakes / total_mistakes if total_mistakes > 0 else 0,
            'last_mistake_date': max([m['timestamp'] for m in self.mistake_records]) if self.mistake_records else None
        })

        # 計算無錯誤天數
        if self.learning_progress['last_mistake_date']:
            last_date = datetime.fromisoformat(self.learning_progress['last_mistake_date'])
            self.learning_progress['mistake_free_days'] = (datetime.now() - last_date).days

    def mark_mistake_resolved(self, mistake_id: str,
                            prevention_actions: List[str] = None) -> bool:
        """
        標記錯誤已解決

        Args:
            mistake_id: 錯誤記錄ID
            prevention_actions: 預防措施

        Returns:
            bool: 標記是否成功
        """
        for mistake in self.mistake_records:
            if mistake['id'] == mistake_id:
                mistake['resolved'] = True
                mistake['resolution_date'] = datetime.now().isoformat()
                mistake['prevention_actions'] = prevention_actions or []

                self._update_learning_progress()
                logger.info("錯誤已標記為解決: %s", mistake_id)
                return True

        logger.warning("找不到錯誤記錄: %s", mistake_id)
        return False

    def analyze_mistake_patterns(self) -> Dict[str, Any]:
        """
        分析錯誤模式

        Returns:
            Dict[str, Any]: 錯誤模式分析結果
        """
        if not self.mistake_records:
            return {'message': '尚無錯誤記錄可供分析'}

        df = pd.DataFrame(self.mistake_records)

        # 錯誤類型分布
        type_distribution = df['mistake_type'].value_counts().to_dict()

        # 嚴重程度分析
        severity_distribution = df['severity'].value_counts().to_dict()

        # 成本影響分析
        total_cost = df['cost_impact'].sum()
        avg_cost = df['cost_impact'].mean()

        # 重複錯誤分析
        recurring_mistakes = df[df['recurrence_count'] > 1]

        # 時間趨勢分析
        df['date'] = pd.to_datetime(df['timestamp']).dt.date
        daily_mistakes = df.groupby('date').size()

        # 解決率分析
        resolution_rate = df['resolved'].mean()

        return {
            'total_mistakes': len(df),
            'type_distribution': type_distribution,
            'severity_distribution': severity_distribution,
            'total_cost_impact': total_cost,
            'average_cost_impact': avg_cost,
            'recurring_mistakes': len(recurring_mistakes),
            'resolution_rate': resolution_rate,
            'daily_average': daily_mistakes.mean(),
            'most_common_mistake': df['mistake_type'].mode().iloc[0] if not df.empty else None,
            'improvement_suggestions': self._generate_pattern_suggestions(df)
        }

    def _generate_pattern_suggestions(self, df: pd.DataFrame) -> List[str]:
        """基於模式生成建議"""
        suggestions = []

        # 分析最常見錯誤
        most_common = df['mistake_type'].value_counts()
        if len(most_common) > 0:
            top_mistake = most_common.index[0]
            count = most_common.iloc[0]
            if count >= 3:
                suggestions.append(f"最常見錯誤是「{self.mistake_categories[top_mistake]['name']}」，建議重點改進")

        # 分析重複錯誤
        recurring = df[df['recurrence_count'] > 1]
        if len(recurring) > 0:
            suggestions.append("存在重複錯誤，建議加強預防措施的執行")

        # 分析成本影響
        high_cost_mistakes = df[df['cost_impact'] < -0.05]  # 損失超過5%
        if len(high_cost_mistakes) > 0:
            suggestions.append("存在高成本錯誤，建議加強風險控制")

        # 分析解決率
        resolution_rate = df['resolved'].mean()
        if resolution_rate < 0.5:
            suggestions.append("錯誤解決率偏低，建議更積極地採取改進措施")

        # 分析錯誤頻率
        days = (pd.to_datetime(df['timestamp']).max() - pd.to_datetime(df['timestamp']).min()).days
        if days > 0:
            frequency = len(df) / days
            if frequency > 0.5:  # 每兩天一個錯誤
                suggestions.append("錯誤頻率較高，建議放慢交易節奏，加強學習")

        return suggestions

    def generate_improvement_plan(self, mistake_type: str = None) -> Dict[str, Any]:
        """
        生成改進計劃

        Args:
            mistake_type: 特定錯誤類型（可選）

        Returns:
            Dict[str, Any]: 改進計劃
        """
        if mistake_type:
            # 針對特定錯誤類型的改進計劃
            if mistake_type not in self.mistake_categories:
                return {'error': f'未知的錯誤類型: {mistake_type}'}

            category = self.mistake_categories[mistake_type]

            # 分析該類型錯誤的歷史記錄
            related_mistakes = [
                m for m in self.mistake_records
                if m['mistake_type'] == mistake_type
            ]

            plan = {
                'mistake_type': mistake_type,
                'mistake_name': category['name'],
                'severity': category['severity'],
                'occurrence_count': len(related_mistakes),
                'total_cost': sum(m['cost_impact'] for m in related_mistakes),
                'prevention_tips': category['prevention_tips'],
                'action_items': self._generate_action_items(mistake_type, related_mistakes),
                'timeline': self._generate_timeline(category['severity']),
                'success_metrics': self._generate_success_metrics(mistake_type)
            }

        else:
            # 綜合改進計劃
            analysis = self.analyze_mistake_patterns()

            if 'message' in analysis:
                return analysis

            # 識別優先改進的錯誤類型
            priority_mistakes = self._identify_priority_mistakes()

            plan = {
                'type': 'comprehensive',
                'priority_mistakes': priority_mistakes,
                'overall_goals': [
                    '減少錯誤頻率',
                    '提高錯誤解決率',
                    '降低錯誤成本影響',
                    '建立預防機制'
                ],
                'action_plan': self._generate_comprehensive_action_plan(),
                'timeline': '3個月',
                'review_schedule': '每週檢討進度'
            }

        return plan

    def _generate_action_items(self, mistake_type: str,
                             related_mistakes: List[Dict]) -> List[str]:
        """生成具體行動項目"""
        category = self.mistake_categories[mistake_type]
        actions = []

        # 基於錯誤類型的通用行動
        if mistake_type == 'overtrading':
            actions.extend([
                '設定每日最大交易次數限制',
                '計算並監控交易成本',
                '建立交易日誌記錄決策過程',
                '學習耐心等待的技巧'
            ])
        elif mistake_type == 'inadequate_risk_management':
            actions.extend([
                '為每筆交易設定停損點',
                '限制單一部位不超過總資金的10%',
                '建立風險評估檢查清單',
                '定期檢視投資組合風險'
            ])
        elif mistake_type == 'emotional_decisions':
            actions.extend([
                '制定交易規則並寫下來',
                '使用冷靜期制度（決策前等待24小時）',
                '學習冥想或其他情緒管理技巧',
                '尋找交易夥伴互相監督'
            ])

        # 基於歷史記錄的個人化行動
        if len(related_mistakes) > 2:
            actions.append('該錯誤重複出現，需要更嚴格的預防措施')

        if any(m['cost_impact'] < -0.1 for m in related_mistakes):
            actions.append('該錯誤造成重大損失，列為最高優先級改進項目')

        return actions

    def _generate_timeline(self, severity: str) -> str:
        """根據嚴重程度生成時間表"""
        timelines = {
            'critical': '立即開始，1週內見效',
            'high': '1週內開始，2週內見效',
            'medium': '2週內開始，1個月內見效',
            'low': '1個月內開始，2個月內見效'
        }
        return timelines.get(severity, '1個月內開始')

    def _generate_success_metrics(self, mistake_type: str) -> List[str]:
        """生成成功指標"""
        base_metrics = [
            '該類型錯誤發生頻率降低50%',
            '錯誤造成的平均損失減少30%',
            '連續30天無此類錯誤'
        ]

        specific_metrics = {
            'overtrading': ['每日交易次數不超過3次', '月交易成本低於總資金1%'],
            'inadequate_risk_management': ['100%交易設定停損', '單筆最大損失不超過2%'],
            'emotional_decisions': ['決策前冷靜期執行率100%', '情緒化交易次數為零']
        }

        return base_metrics + specific_metrics.get(mistake_type, [])

    def _identify_priority_mistakes(self) -> List[Dict[str, Any]]:
        """識別優先改進的錯誤"""
        if not self.mistake_records:
            return []

        df = pd.DataFrame(self.mistake_records)

        # 計算每種錯誤的優先級分數
        mistake_priority = []

        for mistake_type in df['mistake_type'].unique():
            type_mistakes = df[df['mistake_type'] == mistake_type]

            # 計算優先級分數（頻率 + 成本影響 + 嚴重程度）
            frequency_score = len(type_mistakes) * 10
            cost_score = abs(type_mistakes['cost_impact'].sum()) * 100
            severity_score = {'critical': 50, 'high': 30, 'medium': 20, 'low': 10}.get(
                self.mistake_categories.get(mistake_type, {}).get('severity', 'medium'), 20
            )

            total_score = frequency_score + cost_score + severity_score

            mistake_priority.append({
                'mistake_type': mistake_type,
                'mistake_name': self.mistake_categories.get(mistake_type, {}).get('name', mistake_type),
                'frequency': len(type_mistakes),
                'total_cost': type_mistakes['cost_impact'].sum(),
                'priority_score': total_score
            })

        # 按優先級分數排序
        mistake_priority.sort(key=lambda x: x['priority_score'], reverse=True)

        return mistake_priority[:3]  # 返回前3個優先級最高的錯誤

    def _generate_comprehensive_action_plan(self) -> List[Dict[str, Any]]:
        """生成綜合行動計劃"""
        return [
            {
                'phase': '第一階段（第1-2週）',
                'focus': '錯誤識別和記錄',
                'actions': [
                    '建立錯誤記錄習慣',
                    '學習錯誤分類方法',
                    '設定錯誤提醒機制',
                    '分析歷史交易記錄'
                ]
            },
            {
                'phase': '第二階段（第3-6週）',
                'focus': '預防措施實施',
                'actions': [
                    '針對高優先級錯誤制定預防措施',
                    '建立交易檢查清單',
                    '實施風險控制規則',
                    '開始情緒管理訓練'
                ]
            },
            {
                'phase': '第三階段（第7-12週）',
                'focus': '習慣養成和優化',
                'actions': [
                    '鞏固良好的交易習慣',
                    '優化預防措施',
                    '定期檢討和調整',
                    '分享經驗和學習'
                ]
            }
        ]


def show_mistake_analyzer() -> None:
    """
    顯示錯誤分析工具頁面

    提供交易錯誤的深度分析功能，幫助用戶識別、
    理解和改正常見的交易錯誤。

    Side Effects:
        - 在 Streamlit 界面顯示錯誤分析工具
        - 提供錯誤記錄和分析功能
    """
    st.title("🔍 錯誤分析工具")
    st.markdown("深入分析交易錯誤，從錯誤中學習，持續改進！")

    # 初始化錯誤分析器
    if 'mistake_analyzer' not in st.session_state:
        st.session_state.mistake_analyzer = MistakeAnalyzer()

    analyzer = st.session_state.mistake_analyzer

    # 主要功能區域
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["記錄錯誤", "錯誤分析", "改進計劃", "學習進度", "錯誤百科"])

    with tab1:
        st.subheader("📝 記錄新錯誤")

        with st.form("mistake_form"):
            col1, col2 = st.columns(2)

            with col1:
                mistake_type = st.selectbox(
                    "錯誤類型",
                    list(analyzer.mistake_categories.keys()),
                    format_func=lambda x: analyzer.mistake_categories[x]['name']
                )

                cost_impact = st.number_input(
                    "成本影響 (%)",
                    min_value=-100.0,
                    max_value=100.0,
                    value=0.0,
                    step=0.1,
                    help="負數表示損失，正數表示避免的損失"
                )

            with col2:
                trade_id = st.text_input("相關交易ID（可選）", placeholder="例如: trade_20231201_001")

                severity_display = analyzer.mistake_categories[mistake_type]['severity']
                st.info(f"嚴重程度: {severity_display}")

            description = st.text_area(
                "錯誤描述",
                placeholder="詳細描述發生了什麼錯誤...",
                help="請詳細說明錯誤的具體情況"
            )

            lessons_learned = st.text_area(
                "學習心得（可選）",
                placeholder="從這個錯誤中學到了什麼..."
            )

            if st.form_submit_button("記錄錯誤"):
                if description:
                    mistake_id = analyzer.record_mistake(
                        mistake_type=mistake_type,
                        description=description,
                        cost_impact=cost_impact / 100,  # 轉換為小數
                        trade_id=trade_id,
                        lessons_learned=lessons_learned
                    )
                    st.success(f"✅ 錯誤已記錄！ID: {mistake_id}")

                    # 顯示相關建議
                    category = analyzer.mistake_categories[mistake_type]
                    st.subheader("💡 預防建議")
                    for tip in category['prevention_tips']:
                        st.write(f"• {tip}")
                else:
                    st.error("請填寫錯誤描述")

    with tab2:
        st.subheader("📊 錯誤模式分析")

        if analyzer.mistake_records:
            analysis = analyzer.analyze_mistake_patterns()

            # 基本統計
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("總錯誤數", analysis['total_mistakes'])
            with col2:
                st.metric("解決率", f"{analysis['resolution_rate']:.1%}")
            with col3:
                st.metric("總成本影響", f"{analysis['total_cost_impact']:.2%}")
            with col4:
                st.metric("重複錯誤", analysis['recurring_mistakes'])

            # 錯誤類型分布
            if analysis['type_distribution']:
                st.subheader("📈 錯誤類型分布")

                types = list(analysis['type_distribution'].keys())
                counts = list(analysis['type_distribution'].values())

                # 轉換為中文名稱
                type_names = [analyzer.mistake_categories.get(t, {}).get('name', t) for t in types]

                fig = px.bar(x=type_names, y=counts, title="錯誤類型頻率")
                fig.update_layout(xaxis_title="錯誤類型", yaxis_title="發生次數")
                st.plotly_chart(fig, use_container_width=True)

            # 嚴重程度分析
            if analysis['severity_distribution']:
                st.subheader("⚠️ 嚴重程度分布")

                severity_names = {
                    'critical': '嚴重',
                    'high': '高',
                    'medium': '中',
                    'low': '低'
                }

                severities = list(analysis['severity_distribution'].keys())
                severity_counts = list(analysis['severity_distribution'].values())
                severity_labels = [severity_names.get(s, s) for s in severities]

                fig = px.pie(values=severity_counts, names=severity_labels, title="錯誤嚴重程度分布")
                st.plotly_chart(fig, use_container_width=True)

            # 改進建議
            st.subheader("💡 模式分析建議")
            for suggestion in analysis['improvement_suggestions']:
                st.write(f"• {suggestion}")

        else:
            st.info("尚無錯誤記錄，請先記錄一些錯誤")

    with tab3:
        st.subheader("📋 改進計劃")

        plan_type = st.radio(
            "計劃類型",
            ["綜合改進計劃", "特定錯誤改進"],
            horizontal=True
        )

        if plan_type == "特定錯誤改進":
            mistake_type = st.selectbox(
                "選擇錯誤類型",
                list(analyzer.mistake_categories.keys()),
                format_func=lambda x: analyzer.mistake_categories[x]['name']
            )

            if st.button("生成改進計劃"):
                plan = analyzer.generate_improvement_plan(mistake_type)

                if 'error' in plan:
                    st.error(plan['error'])
                else:
                    st.write(f"**錯誤類型**: {plan['mistake_name']}")
                    st.write(f"**嚴重程度**: {plan['severity']}")
                    st.write(f"**發生次數**: {plan['occurrence_count']}")
                    st.write(f"**總成本影響**: {plan['total_cost']:.2%}")

                    st.subheader("🎯 行動項目")
                    for action in plan['action_items']:
                        st.write(f"• {action}")

                    st.subheader("📅 時間表")
                    st.write(plan['timeline'])

                    st.subheader("📊 成功指標")
                    for metric in plan['success_metrics']:
                        st.write(f"• {metric}")

        else:
            if st.button("生成綜合改進計劃"):
                plan = analyzer.generate_improvement_plan()

                if 'message' in plan:
                    st.info(plan['message'])
                else:
                    st.subheader("🎯 優先改進錯誤")
                    for i, mistake in enumerate(plan['priority_mistakes'], 1):
                        st.write(f"{i}. **{mistake['mistake_name']}** - 發生{mistake['frequency']}次，成本影響{mistake['total_cost']:.2%}")

                    st.subheader("📋 分階段行動計劃")
                    for phase in plan['action_plan']:
                        with st.expander(phase['phase']):
                            st.write(f"**重點**: {phase['focus']}")
                            st.write("**行動項目**:")
                            for action in phase['actions']:
                                st.write(f"• {action}")

    with tab4:
        st.subheader("📈 學習進度")

        progress = analyzer.learning_progress

        # 進度指標
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("總錯誤數", progress['total_mistakes'])
            st.metric("已解決錯誤", progress['resolved_mistakes'])

        with col2:
            st.metric("改進率", f"{progress['improvement_rate']:.1%}")
            st.metric("無錯誤天數", progress['mistake_free_days'])

        with col3:
            if progress['last_mistake_date']:
                last_date = datetime.fromisoformat(progress['last_mistake_date']).strftime('%Y-%m-%d')
                st.metric("最後錯誤日期", last_date)

        # 進度圖表
        if analyzer.mistake_records:
            df = pd.DataFrame(analyzer.mistake_records)
            df['date'] = pd.to_datetime(df['timestamp']).dt.date

            # 每日錯誤數量趨勢
            daily_mistakes = df.groupby('date').size().reset_index(name='count')

            fig = px.line(daily_mistakes, x='date', y='count', title='每日錯誤數量趨勢')
            fig.update_layout(xaxis_title="日期", yaxis_title="錯誤數量")
            st.plotly_chart(fig, use_container_width=True)

            # 累積解決錯誤數
            resolved_df = df[df['resolved'] == True]
            if not resolved_df.empty:
                resolved_df['resolve_date'] = pd.to_datetime(resolved_df['resolution_date']).dt.date
                cumulative_resolved = resolved_df.groupby('resolve_date').size().cumsum().reset_index(name='cumulative')

                fig2 = px.line(cumulative_resolved, x='resolve_date', y='cumulative', title='累積解決錯誤數')
                fig2.update_layout(xaxis_title="日期", yaxis_title="累積解決數")
                st.plotly_chart(fig2, use_container_width=True)

        # 標記錯誤為已解決
        st.subheader("✅ 標記錯誤已解決")

        unresolved_mistakes = [m for m in analyzer.mistake_records if not m['resolved']]

        if unresolved_mistakes:
            mistake_options = {
                f"{m['id']}: {analyzer.mistake_categories.get(m['mistake_type'], {}).get('name', m['mistake_type'])} ({m['timestamp'][:10]})": m['id']
                for m in unresolved_mistakes[-10:]  # 顯示最近10個未解決錯誤
            }

            selected_mistake = st.selectbox("選擇要標記的錯誤", list(mistake_options.keys()))

            prevention_actions = st.text_area(
                "預防措施",
                placeholder="描述您採取了哪些措施來預防此錯誤再次發生..."
            )

            if st.button("標記為已解決"):
                if prevention_actions:
                    mistake_id = mistake_options[selected_mistake]
                    success = analyzer.mark_mistake_resolved(
                        mistake_id,
                        prevention_actions.split('\n')
                    )
                    if success:
                        st.success("✅ 錯誤已標記為解決")
                        st.rerun()
                    else:
                        st.error("標記失敗")
                else:
                    st.error("請描述預防措施")
        else:
            st.info("所有錯誤都已解決！")

    with tab5:
        st.subheader("📚 錯誤百科")

        st.markdown("了解各種常見的交易錯誤，學習如何預防。")

        for mistake_type, category in analyzer.mistake_categories.items():
            with st.expander(f"{category['name']} ({category['severity']} 嚴重程度)"):
                st.write(f"**描述**: {category['description']}")

                st.write("**常見原因**:")
                for cause in category['common_causes']:
                    st.write(f"• {cause}")

                st.write("**預防建議**:")
                for tip in category['prevention_tips']:
                    st.write(f"• {tip}")

                st.write(f"**成本影響**: {category['cost_impact']}")

                # 顯示該類型錯誤的統計
                related_mistakes = [m for m in analyzer.mistake_records if m['mistake_type'] == mistake_type]
                if related_mistakes:
                    st.write(f"**您的記錄**: 發生 {len(related_mistakes)} 次")
                    total_cost = sum(m['cost_impact'] for m in related_mistakes)
                    st.write(f"**總成本影響**: {total_cost:.2%}")

    # 側邊欄：快速統計和操作
    with st.sidebar:
        st.subheader("📊 快速統計")

        if analyzer.mistake_records:
            total_mistakes = len(analyzer.mistake_records)
            resolved_mistakes = len([m for m in analyzer.mistake_records if m['resolved']])
            total_cost = sum(m['cost_impact'] for m in analyzer.mistake_records)

            st.metric("總錯誤數", total_mistakes)
            st.metric("已解決", resolved_mistakes)
            st.metric("總成本影響", f"{total_cost:.2%}")

            # 最近錯誤
            recent_mistakes = sorted(
                analyzer.mistake_records,
                key=lambda x: x['timestamp'],
                reverse=True
            )[:3]

            st.subheader("🕒 最近錯誤")
            for mistake in recent_mistakes:
                mistake_name = analyzer.mistake_categories.get(
                    mistake['mistake_type'], {}
                ).get('name', mistake['mistake_type'])

                date = mistake['timestamp'][:10]
                status = "✅" if mistake['resolved'] else "⏳"
                st.write(f"{status} {mistake_name} ({date})")

        else:
            st.info("尚無錯誤記錄")

        # 快速操作
        st.subheader("⚡ 快速操作")

        if st.button("📥 匯入範例錯誤"):
            # 添加一些範例錯誤記錄
            example_mistakes = [
                ('overtrading', '今天進行了8次交易，過於頻繁', -0.015),
                ('poor_timing', '在股價高點買入，沒有等待回調', -0.05),
                ('inadequate_risk_management', '沒有設定停損，損失擴大', -0.08),
                ('emotional_decisions', '看到新聞恐慌賣出', -0.03),
                ('insufficient_research', '聽信朋友推薦就買入', -0.02)
            ]

            for mistake_type, description, cost in example_mistakes:
                analyzer.record_mistake(mistake_type, description, cost)

            st.success("✅ 範例錯誤已匯入")
            st.rerun()

        if st.button("🗑️ 清除所有錯誤"):
            analyzer.mistake_records = []
            analyzer.learning_progress = analyzer._initialize_learning_progress()
            st.success("✅ 錯誤記錄已清除")
            st.rerun()

        # 學習提醒
        st.subheader("💡 學習提醒")

        if analyzer.mistake_records:
            unresolved_count = len([m for m in analyzer.mistake_records if not m['resolved']])
            if unresolved_count > 0:
                st.warning(f"您有 {unresolved_count} 個未解決的錯誤")

            # 檢查是否有重複錯誤
            df = pd.DataFrame(analyzer.mistake_records)
            recent_df = df[pd.to_datetime(df['timestamp']) >= datetime.now() - timedelta(days=7)]

            if not recent_df.empty:
                recurring = recent_df[recent_df['recurrence_count'] > 1]
                if not recurring.empty:
                    st.error("⚠️ 發現重複錯誤，請加強預防措施")

        else:
            st.info("開始記錄錯誤以獲得學習建議")