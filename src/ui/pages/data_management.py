#!/usr/bin/env python3
"""
數據管理頁面 - 基礎版本

此頁面提供基本的數據管理功能，包括數據可視化和圖表功能。

功能特點：
- 基本股票數據顯示
- 簡單的 Plotly 圖表（K線圖和成交量）
- 基本技術指標（RSI、MACD、SMA）
- 性能優化和緩存
- 輕量化設計
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Setup logging
logger = logging.getLogger(__name__)

# Import memory optimizer (keep basic performance optimization)
try:
    from src.ui.utils.memory_optimizer import memory_optimizer, start_memory_monitoring
    MEMORY_OPTIMIZER_AVAILABLE = True
except ImportError:
    MEMORY_OPTIMIZER_AVAILABLE = False
    logger.warning("Memory optimizer not available")

# Module cache for performance
_module_cache = {}


@st.cache_resource
def get_core_modules():
    """Get core modules with caching"""
    if 'core_modules' not in _module_cache:
        try:
            from src.core.data_management_service import DataManagementService
            from src.data_sources.taiwan_stock_list_manager import TaiwanStockListManager
            
            _module_cache['core_modules'] = {
                'DataManagementService': DataManagementService,
                'TaiwanStockListManager': TaiwanStockListManager
            }
        except ImportError as e:
            logger.warning(f"Core modules not available: {e}")
            _module_cache['core_modules'] = None
    
    return _module_cache['core_modules']


@st.cache_data
def get_stock_data_from_db(symbol: str, days: int = 180) -> pd.DataFrame:
    """Get stock data from database with caching"""
    try:
        core_modules = get_core_modules()
        if not core_modules or not core_modules.get('DataManagementService'):
            return pd.DataFrame()
        
        service = core_modules['DataManagementService']()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        df = service.get_stock_data(symbol, start_date, end_date)
        return df if df is not None else pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Failed to get stock data for {symbol}: {e}")
        return pd.DataFrame()


def calculate_basic_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate basic technical indicators without AI dependencies"""
    if df.empty:
        return df
    
    result = df.copy()
    
    try:
        # Simple RSI calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        result['RSI'] = 100 - (100 / (1 + rs))
        
        # Simple MACD calculation
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        result['MACD'] = ema12 - ema26
        result['MACD_signal'] = result['MACD'].ewm(span=9).mean()
        
        # Simple SMA calculation
        result['SMA_20'] = df['close'].rolling(window=20).mean()
        result['SMA_50'] = df['close'].rolling(window=50).mean()
        
    except Exception as e:
        logger.error(f"Technical indicators calculation failed: {e}")
    
    return result


def show_basic_chart(df: pd.DataFrame, symbol: str, show_volume: bool = True) -> None:
    """Display basic chart without AI features"""
    if df.empty:
        st.warning("No data available for chart display")
        return
    
    try:
        rows = 2 if show_volume else 1
        subplot_titles = [f'{symbol} Stock Price']
        if show_volume:
            subplot_titles.append('Volume')
        
        fig = make_subplots(
            rows=rows, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=subplot_titles,
            row_heights=[0.7, 0.3] if show_volume else [1.0]
        )
        
        # Candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df['date'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name="Stock Price"
            ),
            row=1, col=1
        )
        
        # Volume chart
        if show_volume and 'volume' in df.columns:
            colors = ['green' if close >= open else 'red' 
                     for close, open in zip(df['close'], df['open'])]
            
            fig.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['volume'],
                    name='Volume',
                    marker_color=colors,
                    opacity=0.7
                ),
                row=2, col=1
            )
        
        fig.update_layout(
            title=f'{symbol} Stock Analysis',
            xaxis_title='Date',
            yaxis_title='Price',
            template='plotly_white',
            height=600,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        logger.error(f"Chart display failed: {e}")
        st.error(f"Chart display failed: {e}")


def show_technical_indicators(df: pd.DataFrame) -> None:
    """Display basic technical indicators"""
    if df.empty:
        return
    
    try:
        indicators_df = calculate_basic_technical_indicators(df)
        
        if not indicators_df.empty and len(indicators_df) > 0:
            latest = indicators_df.iloc[-1]
            
            st.markdown("#### 📈 Technical Indicators")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if 'RSI' in indicators_df.columns and not pd.isna(latest.get('RSI')):
                    rsi_val = latest['RSI']
                    rsi_status = "Oversold" if rsi_val < 30 else "Overbought" if rsi_val > 70 else "Neutral"
                    st.metric("RSI", f"{rsi_val:.1f}", help="Relative Strength Index")
                    st.caption(f"Status: {rsi_status}")
            
            with col2:
                if 'MACD' in indicators_df.columns and not pd.isna(latest.get('MACD')):
                    macd_val = latest['MACD']
                    macd_signal = latest.get('MACD_signal', 0)
                    macd_status = "Bullish" if macd_val > macd_signal else "Bearish"
                    st.metric("MACD", f"{macd_val:.4f}", help="Moving Average Convergence Divergence")
                    st.caption(f"Status: {macd_status}")
            
            with col3:
                if 'SMA_20' in indicators_df.columns and not pd.isna(latest.get('SMA_20')):
                    sma_val = latest['SMA_20']
                    current_price = df['close'].iloc[-1]
                    sma_status = "Above SMA" if current_price > sma_val else "Below SMA"
                    st.metric("SMA(20)", f"{sma_val:.2f}", help="20-day Simple Moving Average")
                    st.caption(f"Price: {sma_status}")
        
    except Exception as e:
        logger.error(f"Technical indicators display failed: {e}")


def show_sample_stock_search() -> Optional[str]:
    """Show sample stock search when stock manager is not available"""
    # Sample Taiwan stocks for testing
    sample_stocks = [
        {'symbol': '2330.TW', 'name': '台積電', 'market': 'TWSE', 'industry': '半導體'},
        {'symbol': '2317.TW', 'name': '鴻海', 'market': 'TWSE', 'industry': '電子'},
        {'symbol': '2454.TW', 'name': '聯發科', 'market': 'TWSE', 'industry': '半導體'},
        {'symbol': '2881.TW', 'name': '富邦金', 'market': 'TWSE', 'industry': '金融'},
        {'symbol': '2412.TW', 'name': '中華電', 'market': 'TWSE', 'industry': '電信'},
        {'symbol': '1301.TW', 'name': '台塑', 'market': 'TWSE', 'industry': '塑膠'},
        {'symbol': '2303.TW', 'name': '聯電', 'market': 'TWSE', 'industry': '半導體'},
        {'symbol': '1216.TW', 'name': '統一', 'market': 'TWSE', 'industry': '食品'},
    ]

    stocks_df = pd.DataFrame(sample_stocks)

    # Search input
    search_term = st.text_input(
        "輸入股票代碼或名稱:",
        placeholder="例如: 2330 或 台積電",
        help="按股票代碼或公司名稱搜尋（範例數據）"
    )

    if search_term:
        # Filter stocks
        filtered_stocks = stocks_df[
            stocks_df['symbol'].str.contains(search_term, case=False, na=False) |
            stocks_df['name'].str.contains(search_term, case=False, na=False)
        ]

        if not filtered_stocks.empty:
            # Display search results
            selected_stock = st.selectbox(
                "Select a stock:",
                options=filtered_stocks['symbol'].tolist(),
                format_func=lambda x: f"{x} - {filtered_stocks[filtered_stocks['symbol']==x]['name'].iloc[0]}"
            )

            return selected_stock
        else:
            st.warning("No stocks found matching your search")

    return None


def show_stock_search() -> Optional[str]:
    """Show stock search interface"""
    st.markdown("### 🔍 Stock Search")
    
    # Get available stocks
    core_modules = get_core_modules()
    if not core_modules or not core_modules.get('TaiwanStockListManager'):
        st.warning("Stock list manager not available - using sample data")
        return show_sample_stock_search()
    
    try:
        stock_manager = core_modules['TaiwanStockListManager']()
        stocks_list = stock_manager.get_all_stocks()

        if not stocks_list:
            st.warning("No stocks available")
            return None

        # Convert list of StockInfo objects to DataFrame
        stocks_data = []
        for stock in stocks_list:
            stocks_data.append({
                'symbol': stock.symbol,
                'name': stock.name,
                'market': stock.market,
                'industry': stock.industry
            })

        stocks_df = pd.DataFrame(stocks_data)
        
        # Search input
        search_term = st.text_input(
            "Enter stock symbol or name:",
            placeholder="e.g., 2330 or TSMC",
            help="Search by stock symbol or company name"
        )
        
        if search_term:
            # Filter stocks
            filtered_stocks = stocks_df[
                stocks_df['symbol'].str.contains(search_term, case=False, na=False) |
                stocks_df['name'].str.contains(search_term, case=False, na=False)
            ]
            
            if not filtered_stocks.empty:
                # Display search results
                selected_stock = st.selectbox(
                    "Select a stock:",
                    options=filtered_stocks['symbol'].tolist(),
                    format_func=lambda x: f"{x} - {filtered_stocks[filtered_stocks['symbol']==x]['name'].iloc[0]}"
                )
                
                return selected_stock
            else:
                st.warning("No stocks found matching your search")
        
        return None
        
    except Exception as e:
        logger.error(f"Stock search failed: {e}")
        st.error(f"Stock search failed: {e}")
        return None


def show():
    """Show data management page - backward compatibility function"""
    main()


def main():
    """Main data management page"""
    st.title("📊 數據管理")
    st.markdown("*基礎版本 - 提供基本數據可視化功能*")
    
    # Initialize memory monitoring if available
    if MEMORY_OPTIMIZER_AVAILABLE and "memory_monitoring_started" not in st.session_state:
        try:
            start_memory_monitoring()
            st.session_state.memory_monitoring_started = True
        except Exception as e:
            logger.warning(f"Memory monitoring failed to start: {e}")
    
    # Stock search
    selected_symbol = show_stock_search()
    
    if selected_symbol:
        st.markdown(f"### 📈 {selected_symbol} Analysis")
        
        # Data period selection
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info(f"Displaying data for {selected_symbol}")
        
        with col2:
            days = st.selectbox(
                "Data Period",
                options=[30, 60, 90, 180, 365],
                index=3,
                help="Select number of days of historical data"
            )
        
        # Get and display data
        with st.spinner("Loading stock data..."):
            df = get_stock_data_from_db(selected_symbol, days)
        
        if not df.empty:
            # Display basic info
            latest_data = df.iloc[-1]
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Latest Close", f"${latest_data['close']:.2f}")
            
            with col2:
                change = latest_data['close'] - df.iloc[-2]['close'] if len(df) > 1 else 0
                st.metric("Daily Change", f"${change:.2f}", delta=f"{change:.2f}")
            
            with col3:
                st.metric("Volume", f"{latest_data.get('volume', 0):,.0f}")
            
            with col4:
                st.metric("Data Points", len(df))
            
            # Chart options
            show_volume = st.checkbox("Show Volume", value=True)
            
            # Display chart
            show_basic_chart(df, selected_symbol, show_volume)
            
            # Display technical indicators
            show_technical_indicators(df)
            
            # Risk disclaimer
            st.markdown("#### ⚠️ Risk Disclaimer")
            st.warning("""
            **Important Notice:**
            - This analysis is for reference only and does not constitute investment advice
            - Technical indicators have limitations and may lag behind market movements
            - Please conduct thorough research and risk management before making investment decisions
            - Consider setting stop-loss levels to control investment risks
            """)
            
        else:
            st.error(f"No data available for {selected_symbol}")
    
    else:
        st.info("👆 Please search and select a stock to view its analysis")


if __name__ == "__main__":
    main()
