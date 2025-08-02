# -*- coding: utf-8 -*-
"""市場看盤頁面

此模組提供 Streamlit 市場看盤界面，整合原有 Excel 看盤工具的功能到 Web 環境。

主要功能：
- 實時行情數據展示
- 自選股監控面板
- 概念板塊漲幅榜
- 龍虎榜數據展示
- 漲停板股票池
- 可自定義的監控面板
- 預警系統和通知

Example:
    在 Streamlit 應用中使用：
    >>> import streamlit as st
    >>> from src.ui.pages.market_watch import render_market_watch_page
    >>> render_market_watch_page()
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from src.strategies.adapters.market_watch_adapter import MarketWatchAdapter
from src.utils.ui_helpers import format_number, format_percentage, create_metric_card
from src.utils.excel_exporter import ExcelExporter

# 頁面配置
st.set_page_config(
    page_title="市場看盤",
    page_icon="📈",
    layout="wide"
)


def initialize_market_watch_adapter():
    """初始化市場看盤適配器"""
    if 'market_watch_adapter' not in st.session_state:
        config = {
            'data_source': 'qstock',
            'refresh_interval': st.session_state.get('market_refresh_interval', 5),
            'enable_alerts': st.session_state.get('enable_alerts', True),
            'alert_config': {
                'price_change_threshold': st.session_state.get('alert_threshold', 0.05)
            }
        }
        st.session_state.market_watch_adapter = MarketWatchAdapter(config)
    
    return st.session_state.market_watch_adapter


def render_sidebar_config():
    """渲染側邊欄配置"""
    st.sidebar.header("⚙️ 看盤配置")
    
    # 刷新間隔設定
    market_refresh_interval = st.sidebar.slider(
        "刷新間隔 (秒)",
        min_value=1,
        max_value=60,
        value=st.session_state.get('market_refresh_interval', 5),
        help="設定數據自動刷新的間隔時間",
        key="market_refresh_slider"
    )
    st.session_state.market_refresh_interval = market_refresh_interval
    
    # 預警設定
    st.sidebar.subheader("🚨 預警設定")
    enable_alerts = st.sidebar.checkbox(
        "啟用預警",
        value=st.session_state.get('enable_alerts', True)
    )
    st.session_state.enable_alerts = enable_alerts
    
    if enable_alerts:
        alert_threshold = st.sidebar.slider(
            "價格變動預警閾值 (%)",
            min_value=1.0,
            max_value=20.0,
            value=st.session_state.get('alert_threshold', 5.0),
            step=0.5,
            format="%.1f%%"
        ) / 100
        st.session_state.alert_threshold = alert_threshold
    
    # 自選股設定
    st.sidebar.subheader("📊 自選股設定")
    
    # 預設股票列表
    default_stocks = ['000001', '000002', '000858', '002415', '300059']
    
    # 自選股輸入
    custom_stocks_input = st.sidebar.text_area(
        "自選股代碼 (每行一個)",
        value='\n'.join(st.session_state.get('custom_stocks', default_stocks)),
        height=100,
        help="輸入股票代碼，每行一個，例如：000001"
    )
    
    # 解析自選股
    custom_stocks = [
        stock.strip() for stock in custom_stocks_input.split('\n') 
        if stock.strip()
    ]
    st.session_state.custom_stocks = custom_stocks
    
    # 顯示配置摘要
    st.sidebar.info(f"""
    **當前配置**
    - 刷新間隔: {market_refresh_interval} 秒
    - 預警狀態: {'開啟' if enable_alerts else '關閉'}
    - 自選股數量: {len(custom_stocks)} 隻
    """)

    return {
        'refresh_interval': market_refresh_interval,
        'enable_alerts': enable_alerts,
        'alert_threshold': alert_threshold if enable_alerts else None,
        'custom_stocks': custom_stocks
    }


def render_custom_stocks_panel(adapter: MarketWatchAdapter, symbols: List[str]):
    """渲染自選股面板"""
    st.subheader("📊 自選股監控")

    if not symbols:
        st.warning("請在側邊欄配置自選股代碼")
        return

    try:
        # 獲取實時數據
        data = adapter.get_realtime_data('custom_stocks', symbols)

        if data.empty:
            st.warning("暫無自選股數據")
            return

        # 添加多股票比較功能
        col1, col2 = st.columns([3, 1])

        with col2:
            # 排序選項
            sort_options = {
                '漲跌幅': '漲跌幅',
                '現價': '現價(元)',
                '成交量': '成交量',
                '代碼': '代碼'
            }

            sort_by = st.selectbox(
                "排序方式",
                options=list(sort_options.keys()),
                index=0
            )

            sort_ascending = st.checkbox("升序排列", value=False)

            # 顯示選項
            show_comparison = st.checkbox("顯示比較圖表", value=True)

        with col1:
            # 排序數據
            if sort_options[sort_by] in data.columns:
                data_sorted = data.sort_values(
                    sort_options[sort_by],
                    ascending=sort_ascending
                )
            else:
                data_sorted = data

            # 創建指標卡片
            cols = st.columns(min(len(data_sorted), 4))
            for i, (_, row) in enumerate(data_sorted.head(8).iterrows()):
                with cols[i % 4]:
                    symbol = row.get('代碼', 'N/A')
                    name = row.get('名稱', 'N/A')
                    price = row.get('現價(元)', 0)
                    change_pct = row.get('漲跌幅', 0)

                    # 添加排名標識
                    rank = i + 1
                    rank_emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."

                    st.metric(
                        label=f"{rank_emoji} {name} ({symbol})",
                        value=f"¥{price:.2f}",
                        delta=f"{change_pct:.2%}",
                        delta_color="normal"
                    )

        # 比較圖表
        if show_comparison and len(data) > 1:
            st.subheader("📈 股票比較")

            # 漲跌幅比較圖
            if '漲跌幅' in data.columns and '名稱' in data.columns:
                fig = px.bar(
                    data_sorted.head(10),
                    x='名稱',
                    y='漲跌幅',
                    title="漲跌幅比較",
                    color='漲跌幅',
                    color_continuous_scale='RdYlGn'
                )

                fig.update_layout(
                    xaxis_tickangle=-45,
                    height=400,
                    showlegend=False
                )

                st.plotly_chart(fig, use_container_width=True)

        # 統計摘要
        st.subheader("📊 統計摘要")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if '漲跌幅' in data.columns:
                avg_change = data['漲跌幅'].mean()
                st.metric("平均漲跌幅", f"{avg_change:.2%}")

        with col2:
            if '漲跌幅' in data.columns:
                up_count = (data['漲跌幅'] > 0).sum()
                st.metric("上漲股票數", f"{up_count}/{len(data)}")

        with col3:
            if '漲跌幅' in data.columns:
                max_gain = data['漲跌幅'].max()
                st.metric("最大漲幅", f"{max_gain:.2%}")

        with col4:
            if '漲跌幅' in data.columns:
                max_loss = data['漲跌幅'].min()
                st.metric("最大跌幅", f"{max_loss:.2%}")

        # 詳細數據表格
        st.subheader("📋 詳細數據")

        # 格式化數據顯示
        display_data = data_sorted.copy()

        # 添加排名列
        display_data.insert(0, '排名', range(1, len(display_data) + 1))

        # 格式化數值列
        if '現價(元)' in display_data.columns:
            display_data['現價(元)'] = display_data['現價(元)'].apply(lambda x: f"¥{x:.2f}" if pd.notna(x) else "N/A")

        if '漲跌幅' in display_data.columns:
            display_data['漲跌幅'] = display_data['漲跌幅'].apply(lambda x: f"{x:.2%}" if pd.notna(x) else "N/A")

        # 添加顏色樣式
        def highlight_change(val):
            if isinstance(val, str) and '%' in val:
                try:
                    pct_str = val.replace('%', '')
                    pct = float(pct_str)
                    if pct > 0:
                        return 'color: red; font-weight: bold'
                    elif pct < 0:
                        return 'color: green; font-weight: bold'
                except:
                    pass
            return ''

        def highlight_rank(val):
            if val == 1:
                return 'background-color: gold'
            elif val == 2:
                return 'background-color: silver'
            elif val == 3:
                return 'background-color: #CD7F32'
            return ''

        styled_data = display_data.style.applymap(highlight_change, subset=['漲跌幅'])
        styled_data = styled_data.applymap(highlight_rank, subset=['排名'])

        st.dataframe(styled_data, use_container_width=True)

        # 更新時間
        last_update = adapter.data_manager.get_last_update_time('custom_stocks')
        if last_update:
            st.caption(f"最後更新: {last_update.strftime('%H:%M:%S')}")

    except Exception as e:
        st.error(f"獲取自選股數據失敗: {e}")


def render_concept_ranking_panel(adapter: MarketWatchAdapter):
    """渲染概念板塊漲幅榜面板"""
    st.subheader("🔥 概念板塊漲幅榜")
    
    try:
        data = adapter.get_realtime_data('concept_ranking')
        
        if data.empty:
            st.warning("暫無概念板塊數據")
            return
        
        # 顯示前10個概念板塊
        top_concepts = data.head(10)
        
        # 創建圖表
        fig = px.bar(
            top_concepts,
            x='板塊名稱' if '板塊名稱' in top_concepts.columns else top_concepts.columns[0],
            y='漲幅' if '漲幅' in top_concepts.columns else top_concepts.columns[1],
            title="概念板塊漲幅排行",
            color='漲幅' if '漲幅' in top_concepts.columns else top_concepts.columns[1],
            color_continuous_scale='RdYlGn'
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 詳細數據表格
        st.dataframe(data, use_container_width=True)
        
    except Exception as e:
        st.error(f"獲取概念板塊數據失敗: {e}")


def render_billboard_panel(adapter: MarketWatchAdapter):
    """渲染龍虎榜面板"""
    st.subheader("🐉 龍虎榜")
    
    try:
        data = adapter.get_realtime_data('billboard')
        
        if data.empty:
            st.warning("暫無龍虎榜數據")
            return
        
        # 顯示數據表格
        st.dataframe(data, use_container_width=True)
        
        # 統計信息
        if not data.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("上榜股票數", len(data))
            
            with col2:
                if '成交額' in data.columns:
                    total_amount = data['成交額'].sum()
                    st.metric("總成交額", f"¥{total_amount/1e8:.1f}億")
            
            with col3:
                if '漲幅' in data.columns:
                    avg_change = data['漲幅'].mean()
                    st.metric("平均漲幅", f"{avg_change:.2%}")
        
    except Exception as e:
        st.error(f"獲取龍虎榜數據失敗: {e}")


def render_limit_up_panel(adapter: MarketWatchAdapter):
    """渲染漲停板面板"""
    st.subheader("📈 漲停板")
    
    try:
        data = adapter.get_realtime_data('limit_up')
        
        if data.empty:
            st.warning("暫無漲停板數據")
            return
        
        # 統計信息
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("漲停股票數", len(data))
        
        with col2:
            if '成交額' in data.columns:
                total_amount = data['成交額'].sum()
                st.metric("總成交額", f"¥{total_amount/1e8:.1f}億")
        
        with col3:
            if '封板資金' in data.columns:
                total_limit_amount = data['封板資金'].sum()
                st.metric("總封板資金", f"¥{total_limit_amount/1e8:.1f}億")
        
        with col4:
            if '首次封板時間' in data.columns:
                early_limit = (data['首次封板時間'] < '10:00').sum()
                st.metric("早盤封板", f"{early_limit}隻")
        
        # 詳細數據表格
        st.dataframe(data, use_container_width=True)
        
    except Exception as e:
        st.error(f"獲取漲停板數據失敗: {e}")


def render_alerts_panel(adapter: MarketWatchAdapter):
    """渲染預警面板"""
    st.subheader("🚨 預警信息")
    
    try:
        alerts = adapter.get_alert_history(limit=20)
        
        if not alerts:
            st.info("暫無預警信息")
            return
        
        # 顯示最近的預警
        for alert in alerts[-5:]:  # 顯示最近5條
            alert_time = alert['time'].strftime('%H:%M:%S')
            symbol = alert['symbol']
            name = alert['name']
            change = alert['change']
            price = alert['price']
            
            # 確定預警類型和顏色
            alert_type = "📈 上漲" if change > 0 else "📉 下跌"
            color = "red" if change > 0 else "green"
            
            st.markdown(f"""
            <div style="padding: 10px; border-left: 4px solid {color}; margin: 5px 0; background-color: #f0f0f0;">
                <strong>{alert_time}</strong> - {alert_type}<br>
                <strong>{name} ({symbol})</strong><br>
                價格: ¥{price:.2f} | 漲跌幅: {change:.2%}
            </div>
            """, unsafe_allow_html=True)
        
        # 預警統計
        if len(alerts) > 0:
            st.subheader("預警統計")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("今日預警次數", len(alerts))
            
            with col2:
                up_alerts = sum(1 for alert in alerts if alert['change'] > 0)
                st.metric("上漲預警", up_alerts)
        
    except Exception as e:
        st.error(f"獲取預警信息失敗: {e}")


def export_market_data(adapter: MarketWatchAdapter, config: Dict[str, Any]):
    """導出市場數據到Excel"""
    try:
        # 初始化導出器
        exporter = ExcelExporter({
            'output_dir': 'exports/market_watch',
            'auto_format': True
        })

        # 收集所有數據
        market_data = {}

        # 自選股數據
        if config['custom_stocks']:
            custom_data = adapter.get_realtime_data('custom_stocks', config['custom_stocks'])
            if not custom_data.empty:
                market_data['custom_stocks'] = custom_data

        # 概念板塊數據
        concept_data = adapter.get_realtime_data('concept_ranking')
        if not concept_data.empty:
            market_data['concept_ranking'] = concept_data

        # 龍虎榜數據
        billboard_data = adapter.get_realtime_data('billboard')
        if not billboard_data.empty:
            market_data['billboard'] = billboard_data

        # 漲停板數據
        limit_up_data = adapter.get_realtime_data('limit_up')
        if not limit_up_data.empty:
            market_data['limit_up'] = limit_up_data

        if market_data:
            # 導出數據
            file_path = exporter.export_market_watch_data(market_data)

            # 顯示成功消息
            st.success(f"數據導出成功！")
            st.info(f"文件路徑: {file_path}")

            # 提供下載鏈接
            with open(file_path, 'rb') as file:
                st.download_button(
                    label="📥 下載Excel文件",
                    data=file.read(),
                    file_name=os.path.basename(file_path),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("沒有可導出的數據")

    except Exception as e:
        st.error(f"數據導出失敗: {e}")


def show():
    """顯示市場看盤頁面（Web UI 入口點）"""
    render_market_watch_page()


def render_market_watch_page():
    """渲染市場看盤主頁面"""
    st.title("📈 市場看盤")
    st.markdown("---")
    
    # 渲染側邊欄配置
    config = render_sidebar_config()
    
    # 初始化適配器
    adapter = initialize_market_watch_adapter()
    
    # 控制按鈕
    col1, col2, col3, col4 = st.columns([1, 1, 1, 3])

    with col1:
        if st.button("🔄 手動刷新", type="primary"):
            st.rerun()

    with col2:
        auto_refresh = st.checkbox("自動刷新", value=True)

    with col3:
        if st.button("📊 導出Excel"):
            export_market_data(adapter, config)
    
    # 自動刷新邏輯
    if auto_refresh:
        time.sleep(config['refresh_interval'])
        st.rerun()
    
    # 主要內容區域
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 自選股", "🔥 概念板塊", "🐉 龍虎榜", "📈 漲停板", "🚨 預警"
    ])
    
    with tab1:
        render_custom_stocks_panel(adapter, config['custom_stocks'])
    
    with tab2:
        render_concept_ranking_panel(adapter)
    
    with tab3:
        render_billboard_panel(adapter)
    
    with tab4:
        render_limit_up_panel(adapter)
    
    with tab5:
        render_alerts_panel(adapter)
    
    # 頁面底部信息
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption(f"數據源: {adapter.config.data_source}")
    
    with col2:
        st.caption(f"刷新間隔: {config['refresh_interval']}秒")
    
    with col3:
        st.caption(f"最後更新: {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    render_market_watch_page()
