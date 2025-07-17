"""
批量操作用戶界面組件

提供批量操作的完整用戶界面，包括：
- 批量操作配置面板
- 進度監控儀表板
- 操作歷史管理
- 錯誤處理和重試
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import logging

from ..utils.batch_operations_manager import (
    batch_manager,
    BatchOperationType,
    BatchOperationStatus,
    BatchOperationConfig,
    start_batch_strategy_execution,
    start_batch_data_update,
    start_batch_trading_orders
)

logger = logging.getLogger(__name__)


def batch_operations_dashboard():
    """批量操作儀表板"""
    st.subheader("🚀 批量操作中心")
    
    # 操作統計
    operations = batch_manager.get_all_operations()
    
    if operations:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_ops = len(operations)
            st.metric("總操作數", total_ops)
        
        with col2:
            running_ops = len([op for op in operations.values() if op.status == BatchOperationStatus.RUNNING])
            st.metric("進行中", running_ops)
        
        with col3:
            completed_ops = len([op for op in operations.values() if op.status == BatchOperationStatus.COMPLETED])
            success_rate = (completed_ops / total_ops * 100) if total_ops > 0 else 0
            st.metric("完成率", f"{success_rate:.1f}%")
        
        with col4:
            if st.button("🧹 清理舊操作"):
                cleaned = batch_manager.cleanup_completed_operations()
                st.success(f"已清理 {cleaned} 個操作")
                st.rerun()
    
    # 標籤頁
    tab1, tab2, tab3, tab4 = st.tabs(["🆕 新建操作", "📊 監控面板", "📋 操作歷史", "⚙️ 設定"])
    
    with tab1:
        show_new_operation_panel()
    
    with tab2:
        show_monitoring_panel()
    
    with tab3:
        show_operation_history()
    
    with tab4:
        show_batch_settings()


def show_new_operation_panel():
    """顯示新建操作面板"""
    st.markdown("### 創建新的批量操作")
    
    operation_type = st.selectbox(
        "操作類型",
        options=[
            BatchOperationType.STRATEGY_EXECUTION.value,
            BatchOperationType.DATA_UPDATE.value,
            BatchOperationType.TRADING_ORDERS.value,
            BatchOperationType.PORTFOLIO_REBALANCE.value,
            BatchOperationType.REPORT_GENERATION.value
        ],
        format_func=lambda x: {
            "strategy_execution": "🎯 策略執行",
            "data_update": "📊 數據更新",
            "trading_orders": "💰 交易訂單",
            "portfolio_rebalance": "⚖️ 投資組合再平衡",
            "report_generation": "📋 報告生成"
        }.get(x, x)
    )
    
    if operation_type == BatchOperationType.STRATEGY_EXECUTION.value:
        show_strategy_execution_form()
    elif operation_type == BatchOperationType.DATA_UPDATE.value:
        show_data_update_form()
    elif operation_type == BatchOperationType.TRADING_ORDERS.value:
        show_trading_orders_form()
    elif operation_type == BatchOperationType.PORTFOLIO_REBALANCE.value:
        show_portfolio_rebalance_form()
    else:
        show_report_generation_form()


def show_strategy_execution_form():
    """顯示策略執行表單"""
    st.markdown("#### 🎯 批量策略執行")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 策略選擇
        strategies = st.multiselect(
            "選擇策略",
            options=["均線策略", "動量策略", "價值策略", "技術分析策略"],
            default=["均線策略"]
        )
        
        symbols = st.text_area(
            "股票代碼 (每行一個)",
            value="2330.TW\n2317.TW\n2454.TW",
            height=100
        )
    
    with col2:
        batch_size = st.slider("批次大小", 1, 50, 10)
        max_concurrent = st.slider("最大並發數", 1, 10, 3)
        timeout = st.slider("超時時間 (秒)", 60, 600, 300)
    
    if st.button("🚀 開始批量執行", type="primary"):
        if strategies and symbols:
            symbol_list = [s.strip() for s in symbols.split('\n') if s.strip()]
            
            # 創建策略執行項目
            execution_items = []
            for strategy in strategies:
                for symbol in symbol_list:
                    execution_items.append({
                        "strategy": strategy,
                        "symbol": symbol,
                        "timestamp": datetime.now()
                    })
            
            # 模擬執行函數
            def mock_strategy_execution(item):
                import time
                time.sleep(0.1)  # 模擬執行時間
                return {
                    "strategy": item["strategy"],
                    "symbol": item["symbol"],
                    "result": "success",
                    "profit": 0.05
                }
            
            operation_id = start_batch_strategy_execution(
                strategies=execution_items,
                execution_func=mock_strategy_execution,
                batch_size=batch_size
            )
            
            st.success(f"批量策略執行已啟動！操作ID: {operation_id}")
        else:
            st.error("請選擇策略和股票代碼")


def show_data_update_form():
    """顯示數據更新表單"""
    st.markdown("#### 📊 批量數據更新")
    
    col1, col2 = st.columns(2)
    
    with col1:
        data_sources = st.multiselect(
            "數據來源",
            options=["Yahoo Finance", "Alpha Vantage", "Quandl", "本地數據庫"],
            default=["Yahoo Finance"]
        )
        
        symbols = st.text_area(
            "股票代碼 (每行一個)",
            value="2330.TW\n2317.TW\n2454.TW\nAAPL\nTSLA",
            height=100
        )
    
    with col2:
        start_date = st.date_input("開始日期", value=datetime.now().date() - timedelta(days=30))
        end_date = st.date_input("結束日期", value=datetime.now().date())
        batch_size = st.slider("批次大小", 10, 100, 50)
    
    if st.button("📊 開始數據更新", type="primary"):
        if data_sources and symbols:
            symbol_list = [s.strip() for s in symbols.split('\n') if s.strip()]
            
            # 模擬更新函數
            def mock_data_update(symbol):
                import time
                time.sleep(0.2)  # 模擬更新時間
                return {
                    "symbol": symbol,
                    "records_updated": 100,
                    "status": "success"
                }
            
            operation_id = start_batch_data_update(
                symbols=symbol_list,
                update_func=mock_data_update,
                batch_size=batch_size
            )
            
            st.success(f"批量數據更新已啟動！操作ID: {operation_id}")
        else:
            st.error("請選擇數據來源和股票代碼")


def show_trading_orders_form():
    """顯示交易訂單表單"""
    st.markdown("#### 💰 批量交易訂單")
    
    # CSV 上傳
    uploaded_file = st.file_uploader("上傳訂單 CSV 文件", type=["csv"])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("**訂單預覽:**")
            st.dataframe(df)
            
            col1, col2 = st.columns(2)
            with col1:
                batch_size = st.slider("批次大小", 1, 50, 20)
                validate_orders = st.checkbox("驗證訂單", value=True)
            
            with col2:
                dry_run = st.checkbox("模擬執行", value=True)
                error_threshold = st.slider("錯誤率閾值 (%)", 1, 20, 5) / 100
            
            if st.button("💰 提交批量訂單", type="primary"):
                orders = df.to_dict('records')
                
                # 模擬訂單執行函數
                def mock_order_execution(order):
                    import time
                    time.sleep(0.1)
                    return {
                        "order_id": f"ORD_{datetime.now().timestamp()}",
                        "symbol": order.get("symbol", ""),
                        "status": "filled",
                        "executed_price": order.get("price", 100.0)
                    }
                
                operation_id = start_batch_trading_orders(
                    orders=orders,
                    order_func=mock_order_execution,
                    batch_size=batch_size
                )
                
                st.success(f"批量交易訂單已提交！操作ID: {operation_id}")
                
        except Exception as e:
            st.error(f"文件格式錯誤: {e}")
    
    else:
        # 提供範例格式
        st.write("**範例 CSV 格式:**")
        sample_df = pd.DataFrame({
            "symbol": ["2330.TW", "2317.TW", "AAPL"],
            "action": ["buy", "sell", "buy"],
            "quantity": [100, 200, 50],
            "order_type": ["market", "limit", "limit"],
            "price": [None, 100.0, 150.0]
        })
        st.dataframe(sample_df)


def show_portfolio_rebalance_form():
    """顯示投資組合再平衡表單"""
    st.markdown("#### ⚖️ 投資組合再平衡")
    st.info("此功能正在開發中...")


def show_report_generation_form():
    """顯示報告生成表單"""
    st.markdown("#### 📋 批量報告生成")
    st.info("此功能正在開發中...")


def show_monitoring_panel():
    """顯示監控面板"""
    st.markdown("### 📊 實時監控")
    
    operations = batch_manager.get_all_operations()
    active_operations = {
        op_id: op for op_id, op in operations.items()
        if op.status in [BatchOperationStatus.RUNNING, BatchOperationStatus.PENDING]
    }
    
    if active_operations:
        for op_id, operation in active_operations.items():
            show_operation_progress(op_id, operation)
    else:
        st.info("目前沒有進行中的操作")
    
    # 自動刷新
    if active_operations and st.checkbox("自動刷新 (5秒)", value=True):
        import time
        time.sleep(5)
        st.rerun()


def show_operation_progress(operation_id: str, operation):
    """顯示操作進度"""
    with st.container():
        # 操作信息
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            session_info = st.session_state.batch_operations.get(operation_id, {})
            operation_name = session_info.get("name", "未知操作")
            st.write(f"**{operation_name}** ({operation_id[:8]}...)")
        
        with col2:
            status_color = {
                "pending": "🟡",
                "running": "🟢",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "⏹️"
            }
            st.write(f"{status_color.get(operation.status.value, '⚪')} {operation.status.value}")
        
        with col3:
            if operation.status == BatchOperationStatus.RUNNING:
                if st.button("⏹️ 取消", key=f"cancel_{operation_id}"):
                    batch_manager.cancel_operation(operation_id)
                    st.rerun()
        
        # 進度條
        progress = operation.processed_items / operation.total_items if operation.total_items > 0 else 0
        st.progress(progress)
        
        # 統計信息
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("總項目", operation.total_items)
        with col2:
            st.metric("已處理", operation.processed_items)
        with col3:
            st.metric("成功", operation.successful_items)
        with col4:
            st.metric("失敗", operation.failed_items)
        
        # 錯誤信息
        if operation.error_messages:
            with st.expander("❌ 錯誤信息"):
                for error in operation.error_messages[-5:]:  # 顯示最近5個錯誤
                    st.error(error)
        
        st.markdown("---")


def show_operation_history():
    """顯示操作歷史"""
    st.markdown("### 📋 操作歷史")
    
    operations = batch_manager.get_all_operations()
    
    if operations:
        # 創建歷史數據表
        history_data = []
        for op_id, operation in operations.items():
            session_info = st.session_state.batch_operations.get(op_id, {})
            history_data.append({
                "操作ID": op_id[:8] + "...",
                "名稱": session_info.get("name", "未知"),
                "類型": session_info.get("type", "未知"),
                "狀態": operation.status.value,
                "總項目": operation.total_items,
                "成功": operation.successful_items,
                "失敗": operation.failed_items,
                "成功率": f"{operation.success_rate:.1%}",
                "開始時間": operation.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "執行時間": str(operation.duration) if operation.duration else "進行中"
            })
        
        df = pd.DataFrame(history_data)
        st.dataframe(df, use_container_width=True)
        
        # 統計圖表
        if len(history_data) > 1:
            st.markdown("#### 📈 統計圖表")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # 狀態分布
                status_counts = df["狀態"].value_counts()
                fig_pie = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="操作狀態分布"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # 成功率趨勢
                df_sorted = df.sort_values("開始時間")
                fig_line = px.line(
                    df_sorted,
                    x="開始時間",
                    y="成功率",
                    title="成功率趨勢",
                    markers=True
                )
                st.plotly_chart(fig_line, use_container_width=True)
    
    else:
        st.info("沒有操作歷史")


def show_batch_settings():
    """顯示批量操作設定"""
    st.markdown("### ⚙️ 批量操作設定")
    
    # 默認配置
    st.markdown("#### 默認配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        default_batch_size = st.slider("默認批次大小", 10, 200, 50)
        default_timeout = st.slider("默認超時時間 (秒)", 60, 1200, 300)
        default_retry_attempts = st.slider("默認重試次數", 1, 10, 3)
    
    with col2:
        default_error_threshold = st.slider("默認錯誤率閾值 (%)", 1, 50, 10) / 100
        auto_cleanup_hours = st.slider("自動清理時間 (小時)", 1, 168, 24)
        enable_notifications = st.checkbox("啟用完成通知", value=True)
    
    if st.button("💾 保存設定"):
        # 保存設定到 session state
        st.session_state.batch_settings = {
            "default_batch_size": default_batch_size,
            "default_timeout": default_timeout,
            "default_retry_attempts": default_retry_attempts,
            "default_error_threshold": default_error_threshold,
            "auto_cleanup_hours": auto_cleanup_hours,
            "enable_notifications": enable_notifications
        }
        st.success("設定已保存")
    
    # 系統狀態
    st.markdown("#### 系統狀態")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        active_threads = len(batch_manager.active_operations)
        st.metric("活躍線程", active_threads)
    
    with col2:
        total_operations = len(batch_manager.operations)
        st.metric("總操作數", total_operations)
    
    with col3:
        if st.button("🔄 重置系統"):
            # 取消所有進行中的操作
            for op_id in list(batch_manager.active_operations.keys()):
                batch_manager.cancel_operation(op_id)
            st.success("系統已重置")
            st.rerun()
