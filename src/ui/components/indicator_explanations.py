#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技術指標使用說明組件

提供各種技術指標的詳細說明，包括：
- 指標原理和計算方法
- 使用方法和交易信號
- 參數設置建議
- 實戰應用技巧
"""

import streamlit as st
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class IndicatorExplanations:
    """技術指標說明類"""
    
    def __init__(self):
        """初始化指標說明"""
        self.explanations = self._load_explanations()
    
    def _load_explanations(self) -> Dict[str, Dict]:
        """載入所有指標說明"""
        return {
            'williams_r': {
                'name': 'Williams %R (威廉指標)',
                'category': '動量指標',
                'range': '-100 到 0',
                'description': '''
                Williams %R 是一個動量指標，由 Larry Williams 開發，用於測量收盤價在過去 N 期的最高價和最低價範圍內的位置。
                ''',
                'formula': '''
                **計算公式：**
                ```
                %R = (最高價 - 收盤價) / (最高價 - 最低價) × (-100)
                ```
                
                其中：
                - 最高價：N 期內的最高價
                - 最低價：N 期內的最低價
                - 收盤價：當期收盤價
                ''',
                'interpretation': '''
                **數值解讀：**
                - **-20 以上**：超買區域，可能出現賣出信號
                - **-80 以下**：超賣區域，可能出現買入信號
                - **-50 附近**：中性區域
                
                **交易信號：**
                1. **買入信號**：從超賣區域（-80以下）向上突破
                2. **賣出信號**：從超買區域（-20以上）向下跌破
                3. **背離信號**：價格創新高/低但指標未創新高/低
                ''',
                'parameters': '''
                **參數設置：**
                - **標準週期**：14 天
                - **短期交易**：5-9 天
                - **長期分析**：21-28 天
                
                **注意事項：**
                - 週期越短，信號越敏感但假信號較多
                - 週期越長，信號越穩定但滯後性較強
                ''',
                'tips': '''
                **實戰技巧：**
                1. 結合趨勢分析，在趨勢方向上使用信號
                2. 注意背離現象，往往預示趨勢反轉
                3. 避免在震盪市場中頻繁交易
                4. 配合成交量分析提高準確性
                '''
            },
            
            'stochastic': {
                'name': 'Stochastic Oscillator (隨機指標)',
                'category': '動量指標',
                'range': '0 到 100',
                'description': '''
                隨機指標由 George Lane 開發，包含兩條線：%K 和 %D，用於識別超買和超賣條件。
                基於「收盤價趨向於接近當日價格區間的同一端」的理論。
                ''',
                'formula': '''
                **計算公式：**
                ```
                %K = (收盤價 - 最低價) / (最高價 - 最低價) × 100
                %D = %K 的 N 期移動平均
                ```
                
                **快速隨機指標：**
                - Fast %K = 原始 %K
                - Fast %D = Fast %K 的移動平均
                
                **慢速隨機指標：**
                - Slow %K = Fast %D
                - Slow %D = Slow %K 的移動平均
                ''',
                'interpretation': '''
                **數值解讀：**
                - **80 以上**：超買區域，考慮賣出
                - **20 以下**：超賣區域，考慮買入
                - **50 附近**：中性區域
                
                **交易信號：**
                1. **金叉買入**：%K 線向上穿越 %D 線
                2. **死叉賣出**：%K 線向下穿越 %D 線
                3. **超買賣出**：在超買區域出現死叉
                4. **超賣買入**：在超賣區域出現金叉
                ''',
                'parameters': '''
                **標準參數：**
                - **%K 週期**：14
                - **%K 平滑**：3
                - **%D 週期**：3
                
                **參數調整：**
                - 縮短週期：提高敏感度，增加信號頻率
                - 延長週期：減少假信號，提高可靠性
                ''',
                'tips': '''
                **實戰技巧：**
                1. 優先使用慢速隨機指標，信號更可靠
                2. 在強趨勢中，指標可能長時間停留在極值區域
                3. 結合價格形態分析，提高信號準確性
                4. 注意背離現象，特別是在關鍵支撐阻力位
                '''
            },
            
            'cci': {
                'name': 'CCI (商品通道指數)',
                'category': '動量指標',
                'range': '無限制（通常 -200 到 +200）',
                'description': '''
                CCI 由 Donald Lambert 開發，最初用於商品期貨交易，現廣泛應用於股票市場。
                測量價格偏離其統計平均值的程度，幫助識別超買超賣和趨勢變化。
                ''',
                'formula': '''
                **計算公式：**
                ```
                典型價格 = (最高價 + 最低價 + 收盤價) / 3
                CCI = (典型價格 - 典型價格的移動平均) / (0.015 × 平均絕對偏差)
                ```
                
                其中 0.015 是常數，使約 70-80% 的 CCI 值落在 -100 到 +100 之間。
                ''',
                'interpretation': '''
                **數值解讀：**
                - **+100 以上**：超買區域，價格可能回調
                - **-100 以下**：超賣區域，價格可能反彈
                - **-100 到 +100**：正常波動範圍
                
                **交易信號：**
                1. **突破買入**：從 -100 以下向上突破 -100
                2. **突破賣出**：從 +100 以上向下跌破 +100
                3. **零軸交叉**：穿越零軸表示趨勢變化
                ''',
                'parameters': '''
                **標準參數：**
                - **計算週期**：20
                - **短期分析**：10-14
                - **長期分析**：30-50
                
                **參數影響：**
                - 短週期：信號敏感，適合短線交易
                - 長週期：信號穩定，適合中長線投資
                ''',
                'tips': '''
                **實戰技巧：**
                1. CCI 沒有上下限，適合捕捉強勢突破
                2. 在趨勢市場中效果較好
                3. 結合價格通道分析，提高交易效果
                4. 注意假突破，等待確認信號
                '''
            },
            
            'atr': {
                'name': 'ATR (平均真實範圍)',
                'category': '波動性指標',
                'range': '0 以上（無上限）',
                'description': '''
                ATR 由 J. Welles Wilder 開發，是衡量市場波動性的重要指標。
                不指示價格方向，只測量波動程度，常用於設置止損和倉位管理。
                ''',
                'formula': '''
                **計算公式：**
                ```
                真實範圍 TR = max(高-低, abs(高-前收), abs(低-前收))
                ATR = TR 的 N 期移動平均
                ```
                
                真實範圍考慮了跳空缺口的影響，更準確反映實際波動。
                ''',
                'interpretation': '''
                **數值解讀：**
                - **ATR 上升**：市場波動性增加
                - **ATR 下降**：市場波動性減少
                - **ATR 相對值**：與歷史水平比較更有意義
                
                **應用場景：**
                1. **止損設置**：ATR × 倍數作為止損距離
                2. **倉位管理**：根據 ATR 調整倉位大小
                3. **趨勢判斷**：ATR 突破可能預示趨勢變化
                ''',
                'parameters': '''
                **標準參數：**
                - **計算週期**：14
                - **短期分析**：7-10
                - **長期分析**：21-30
                
                **倍數設置：**
                - **保守止損**：1-1.5 倍 ATR
                - **標準止損**：2-2.5 倍 ATR
                - **寬鬆止損**：3-4 倍 ATR
                ''',
                'tips': '''
                **實戰技巧：**
                1. ATR 不是交易信號，而是風險管理工具
                2. 在高波動期間適當放寬止損
                3. 結合價格形態，在關鍵位置設置止損
                4. 定期調整 ATR 倍數以適應市場變化
                '''
            },
            
            'vwap': {
                'name': 'VWAP (成交量加權平均價格)',
                'category': '趨勢指標',
                'range': '價格範圍內',
                'description': '''
                VWAP 是機構交易者廣泛使用的基準指標，反映了在特定時間段內的平均成交價格。
                考慮了成交量因素，比簡單平均價格更能反映市場真實情況。
                ''',
                'formula': '''
                **計算公式：**
                ```
                典型價格 = (最高價 + 最低價 + 收盤價) / 3
                VWAP = Σ(典型價格 × 成交量) / Σ(成交量)
                ```
                
                通常以當日開盤為起點進行累積計算。
                ''',
                'interpretation': '''
                **數值解讀：**
                - **價格高於 VWAP**：買方力量較強
                - **價格低於 VWAP**：賣方力量較強
                - **價格圍繞 VWAP 波動**：市場均衡狀態
                
                **交易信號：**
                1. **突破買入**：價格向上突破 VWAP
                2. **跌破賣出**：價格向下跌破 VWAP
                3. **回歸交易**：價格偏離 VWAP 後的回歸
                ''',
                'parameters': '''
                **時間週期：**
                - **日內交易**：當日 VWAP
                - **短期交易**：週 VWAP
                - **中期投資**：月 VWAP
                
                **注意事項：**
                - VWAP 是累積指標，不適合長期分析
                - 在交易量大的時段更有參考價值
                ''',
                'tips': '''
                **實戰技巧：**
                1. 機構常以 VWAP 為執行基準，關注其支撐阻力作用
                2. 結合成交量分析，確認突破有效性
                3. 在開盤後 1-2 小時 VWAP 較為穩定
                4. 適合作為日內交易的參考基準
                '''
            }
        }
    
    def show_indicator_explanation(self, indicator_key: str):
        """顯示指標說明"""
        if indicator_key not in self.explanations:
            st.error(f"找不到指標 {indicator_key} 的說明")
            return
        
        explanation = self.explanations[indicator_key]
        
        # 指標基本信息
        st.subheader(f"📊 {explanation['name']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("指標類型", explanation['category'])
        with col2:
            st.metric("數值範圍", explanation['range'])
        with col3:
            st.metric("難度等級", "⭐⭐⭐")
        
        # 指標描述
        st.markdown("### 📝 指標說明")
        st.markdown(explanation['description'])
        
        # 計算公式
        st.markdown("### 🧮 計算公式")
        st.markdown(explanation['formula'])
        
        # 數值解讀
        st.markdown("### 📈 數值解讀與交易信號")
        st.markdown(explanation['interpretation'])
        
        # 參數設置
        st.markdown("### ⚙️ 參數設置")
        st.markdown(explanation['parameters'])
        
        # 實戰技巧
        st.markdown("### 💡 實戰技巧")
        st.markdown(explanation['tips'])
    
    def show_all_indicators_summary(self):
        """顯示所有指標摘要"""
        st.subheader("📚 技術指標總覽")
        
        # 創建指標分類
        categories = {}
        for key, info in self.explanations.items():
            category = info['category']
            if category not in categories:
                categories[category] = []
            categories[category].append((key, info))
        
        # 按分類顯示
        for category, indicators in categories.items():
            st.markdown(f"### {category}")
            
            for key, info in indicators:
                with st.expander(f"📊 {info['name']}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(info['description'][:200] + "...")
                    
                    with col2:
                        if st.button(f"查看詳細說明", key=f"detail_{key}"):
                            st.session_state[f'show_detail_{key}'] = True
                    
                    # 如果用戶點擊了詳細說明按鈕
                    if st.session_state.get(f'show_detail_{key}', False):
                        self.show_indicator_explanation(key)
                        if st.button(f"收起說明", key=f"hide_{key}"):
                            st.session_state[f'show_detail_{key}'] = False
    
    def get_indicator_list(self) -> List[str]:
        """獲取所有指標列表"""
        return list(self.explanations.keys())
    
    def get_indicator_name(self, key: str) -> str:
        """獲取指標名稱"""
        return self.explanations.get(key, {}).get('name', key)
