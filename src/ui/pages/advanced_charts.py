"""
進階圖表頁面

展示AI股票自動交易系統顯示邏輯改進功能，包括：
- 整合特徵計算器
- 進階縮放與互動圖表
- AI自動訊號生成
- 自學優化功能

基於AI股票自動交易系統顯示邏輯改進指南實現。
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

# 導入改進的組件
from src.ui.components.interactive_charts import (
    agent_integrated_display,
    generate_trading_signals,
    create_integrated_chart,
    ChartTheme
)
from src.core.integrated_feature_calculator import IntegratedFeatureCalculator
from src.ai.self_learning_agent import SelfLearningAgent

logger = logging.getLogger(__name__)


def show():
    """顯示進階圖表頁面"""
    st.title("🚀 進階圖表分析系統")
    st.markdown("基於AI股票自動交易系統顯示邏輯改進指南的完整實現")
    
    # 側邊欄配置
    with st.sidebar:
        st.header("📊 圖表配置")
        
        # 股票選擇
        stock_id = st.selectbox(
            "選擇股票",
            options=["2330.TW", "2317.TW", "2454.TW", "1101.TW", "2382.TW"],
            index=0,
            help="選擇要分析的股票代號"
        )
        
        # 技術指標選擇
        st.subheader("技術指標")
        indicators = st.multiselect(
            "選擇技術指標",
            options=["RSI", "MACD", "SMA", "EMA", "BBANDS"],
            default=["RSI", "MACD"],
            help="選擇要計算的技術指標"
        )
        
        # 參數倍數設定
        st.subheader("參數倍數")
        multiplier_mode = st.radio(
            "倍數模式",
            options=["預設", "自定義"],
            help="選擇參數倍數設定方式"
        )
        
        if multiplier_mode == "預設":
            multipliers = [0.5, 1.0, 1.5]
        else:
            multiplier_input = st.text_input(
                "輸入倍數（用逗號分隔）",
                value="0.5,1.0,1.5",
                help="例如：0.5,1.0,1.5,2.0"
            )
            try:
                multipliers = [float(x.strip()) for x in multiplier_input.split(",")]
            except ValueError:
                st.error("倍數格式錯誤，使用預設值")
                multipliers = [0.5, 1.0, 1.5]
        
        # 日期範圍設定
        st.subheader("日期範圍")
        date_range_days = st.slider(
            "分析天數",
            min_value=30,
            max_value=730,
            value=365,
            step=30,
            help="選擇分析的歷史天數"
        )
        
        # AI功能設定
        st.subheader("🤖 AI功能")
        enable_ai_signals = st.checkbox(
            "啟用AI訊號生成",
            value=True,
            help="自動生成買賣訊號"
        )
        
        enable_self_learning = st.checkbox(
            "啟用自學優化",
            value=False,
            help="根據使用習慣優化參數"
        )
        
        seasonal_analysis = st.checkbox(
            "季節性分析",
            value=True,
            help="包含季節性趨勢分析"
        )
    
    # 主要內容區域
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 生成圖表按鈕
        if st.button("🎯 生成進階圖表", type="primary"):
            with st.spinner("正在生成進階圖表..."):
                try:
                    # 計算日期範圍
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(days=date_range_days)).strftime('%Y-%m-%d')
                    date_range = [start_date, end_date]
                    
                    # 記錄用戶互動（如果啟用自學）
                    if enable_self_learning:
                        agent = SelfLearningAgent("chart_user")
                        agent.record_user_interaction(
                            interaction_type="chart_generation",
                            parameters={
                                "stock_id": stock_id,
                                "indicators": indicators,
                                "multipliers": multipliers,
                                "date_range_days": date_range_days,
                                "seasonal_analysis": seasonal_analysis
                            },
                            result_quality=0.8  # 假設品質評分
                        )
                        
                        # 嘗試學習和優化
                        if len(agent.user_interactions) >= 5:
                            agent.learn_from_interactions()
                            optimized_params = agent.predict_optimal_parameters(
                                stock_id, {
                                    "indicators": indicators,
                                    "multipliers": multipliers,
                                    "date_range_days": date_range_days
                                }
                            )
                            
                            # 顯示AI建議
                            if optimized_params != {
                                "indicators": indicators,
                                "multipliers": multipliers,
                                "date_range_days": date_range_days
                            }:
                                st.info("🤖 AI建議了優化參數，已自動應用")
                                indicators = optimized_params.get("indicators", indicators)
                                multipliers = optimized_params.get("multipliers", multipliers)
                    
                    # 生成整合圖表
                    fig = agent_integrated_display(
                        stock_id=stock_id,
                        data_dict=None,  # 使用模擬數據
                        indicators=indicators,
                        multipliers=multipliers,
                        date_range=date_range,
                        enable_ai_signals=enable_ai_signals
                    )
                    
                    # 顯示圖表
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 顯示成功訊息
                    st.success(f"✅ 成功生成 {stock_id} 的進階圖表")
                    
                except Exception as e:
                    st.error(f"❌ 生成圖表時發生錯誤: {str(e)}")
                    logger.error(f"圖表生成錯誤: {e}")
    
    with col2:
        # 功能說明
        st.subheader("📋 功能說明")
        
        with st.expander("🔧 整合特徵計算器"):
            st.markdown("""
            - **多倍數支援**: 同時計算不同參數倍數的指標
            - **季節性分析**: 識別月份和週期性模式
            - **LRU快取**: 提升計算性能
            - **錯誤處理**: 完整的異常處理機制
            """)
        
        with st.expander("📊 進階圖表功能"):
            st.markdown("""
            - **TradingView風格**: 專業的圖表界面
            - **進階縮放**: 滾輪、拖曳、按鈕控制
            - **互動元素**: 趨勢線、標記、工具提示
            - **多時間框架**: 靈活的時間範圍選擇
            """)
        
        with st.expander("🤖 AI自動訊號"):
            st.markdown("""
            - **MACD金叉**: 自動檢測買入訊號
            - **RSI超買超賣**: 識別反轉機會
            - **智能標記**: 自動在圖表上標記訊號
            - **多策略融合**: 綜合多種技術指標
            """)
        
        with st.expander("🧠 自學優化"):
            st.markdown("""
            - **用戶行為學習**: 記錄和分析使用習慣
            - **參數優化**: 基於歷史偏好調整參數
            - **Optuna整合**: 先進的超參數優化
            - **LSTM預測**: 深度學習價格預測
            """)
        
        # 系統狀態
        st.subheader("⚙️ 系統狀態")
        
        # 檢查依賴
        try:
            import optuna
            optuna_status = "✅ 已安裝"
        except ImportError:
            optuna_status = "❌ 未安裝"
        
        try:
            import tensorflow
            tf_status = "✅ 已安裝"
        except ImportError:
            tf_status = "❌ 未安裝"
        
        try:
            import talib
            talib_status = "✅ 已安裝"
        except ImportError:
            talib_status = "❌ 未安裝"
        
        st.markdown(f"""
        **依賴狀態:**
        - Optuna: {optuna_status}
        - TensorFlow: {tf_status}
        - TA-Lib: {talib_status}
        """)
        
        # 快取狀態
        if st.button("🔄 清除快取"):
            try:
                calculator = IntegratedFeatureCalculator()
                calculator.clear_cache()
                st.success("快取已清除")
            except Exception as e:
                st.error(f"清除快取失敗: {e}")
    
    # 底部資訊
    st.markdown("---")
    st.markdown("""
    ### 📚 使用指南
    
    1. **選擇股票**: 從側邊欄選擇要分析的股票代號
    2. **配置指標**: 選擇技術指標和參數倍數
    3. **設定範圍**: 調整分析的時間範圍
    4. **啟用AI**: 開啟AI訊號生成和自學優化
    5. **生成圖表**: 點擊按鈕生成進階圖表
    
    ### 🎯 進階功能
    
    - **多倍數比較**: 同時顯示不同參數設定的指標效果
    - **智能訊號**: AI自動識別買賣時機並在圖表上標記
    - **個性化學習**: 系統學習您的使用習慣並提供優化建議
    - **專業界面**: TradingView風格的專業圖表界面
    
    ### 💡 提示
    
    - 首次使用建議啟用所有功能體驗完整效果
    - 自學功能需要多次使用後才會生效
    - 可以通過調整倍數來微調指標敏感度
    - 支援多種主題和個性化設定
    """)


if __name__ == "__main__":
    show()
