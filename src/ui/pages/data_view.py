#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據檢視頁面
===========

提供股票數據檢視功能，支援智能搜尋、技術指標選擇和圖表顯示。
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import logging
from typing import List, Optional, Dict, Any
import sqlite3

# 設定日誌
logger = logging.getLogger(__name__)

# 全局緩存變量，避免重複初始化
_stock_manager_cache = None

def get_stock_manager():
    """獲取股票管理器實例，使用全局緩存避免重複初始化"""
    global _stock_manager_cache

    if _stock_manager_cache is None:
        try:
            from src.data_sources.taiwan_stock_list_manager import TaiwanStockListManager
            _stock_manager_cache = TaiwanStockListManager()
            logger.info("股票管理器初始化完成")
        except Exception as e:
            logger.error(f"股票管理器初始化失敗: {e}")
            _stock_manager_cache = None

    return _stock_manager_cache

def show_data_view_page():
    """顯示數據檢視頁面"""
    st.title("📊 股票數據檢視")

    # 股票代號搜尋區域
    st.subheader("🔍 股票搜尋")

    # 實時搜尋輸入
    search_input = st.text_input(
        "輸入股票代號前綴",
        placeholder="例如：2、23、233、2330",
        help="輸入數字前綴來搜尋相關股票",
        key="stock_search_input"
    )

    # 初始化session state
    if 'selected_symbol' not in st.session_state:
        st.session_state.selected_symbol = None

    selected_symbol = None

    # 實時顯示搜尋結果
    if search_input:
        filtered_stocks = search_stocks_by_prefix(search_input)

        if filtered_stocks:
            st.subheader(f"📋 搜尋結果 ({len(filtered_stocks)} 檔股票)")

            # 直接顯示股票列表，支持點擊選擇
            st.write("點擊下方股票進行檢視：")

            # 使用columns來顯示股票，每行顯示2個（因為現在顯示名稱會比較長）
            cols_per_row = 2
            for i in range(0, len(filtered_stocks), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, stock_info in enumerate(filtered_stocks[i:i+cols_per_row]):
                    with cols[j]:
                        # 使用股票代碼和名稱作為按鈕文字
                        if st.button(stock_info['display'], key=f"stock_btn_{stock_info['symbol']}", use_container_width=True):
                            st.session_state.selected_symbol = stock_info['symbol']
                            selected_symbol = stock_info['symbol']

            # 如果有之前選擇的股票，保持選擇狀態
            current_symbols = [stock['symbol'] for stock in filtered_stocks]
            if st.session_state.selected_symbol in current_symbols:
                selected_symbol = st.session_state.selected_symbol
                # 找到對應的股票名稱
                selected_stock_info = next((stock for stock in filtered_stocks if stock['symbol'] == selected_symbol), None)
                if selected_stock_info:
                    st.success(f"✅ 已選擇股票：{selected_stock_info['display']}")
        else:
            st.warning(f"⚠️ 未找到以 '{search_input}' 開頭的股票")
    else:
        # 清除選擇狀態
        st.session_state.selected_symbol = None

    # 技術指標和日期範圍設置
    if selected_symbol:
        st.markdown("---")
        st.subheader("📈 分析設置")

        col1, col2 = st.columns([1, 1])

        with col1:
            # 技術指標多選
            technical_indicators = st.multiselect(
                "選擇技術指標",
                options=[
                    "RSI", "MACD", "SMA", "EMA",
                    "BBANDS", "KD", "CCI", "ATR"
                ],
                default=[],
                help="選擇要顯示的技術指標"
            )

        with col2:
            # 日期範圍選擇
            date_range = st.selectbox(
                "顯示期間",
                options=["1個月", "3個月", "6個月", "1年", "自訂"],
                index=2,
                help="選擇圖表顯示的時間範圍"
            )

            # 自訂日期範圍
            if date_range == "自訂":
                custom_start = st.date_input(
                    "開始日期",
                    value=date.today() - timedelta(days=180)
                )
                custom_end = st.date_input(
                    "結束日期",
                    value=date.today()
                )

        st.markdown("---")

        # 顯示圖表按鈕
        if st.button("📊 顯示圖表", type="primary", use_container_width=True):
            show_stock_charts_separated(selected_symbol, technical_indicators, date_range)

        # 顯示數據按鈕
        if st.button("📋 顯示數據", use_container_width=True):
            show_stock_data_table(selected_symbol, date_range)


def get_available_stocks() -> List[str]:
    """獲取可用的股票列表"""
    try:
        conn = sqlite3.connect('data/enhanced_stock_database.db')
        cursor = conn.cursor()

        # 從 real_stock_data 表獲取股票列表
        cursor.execute("SELECT DISTINCT symbol FROM real_stock_data ORDER BY symbol")
        stocks = [row[0] for row in cursor.fetchall()]

        conn.close()
        return stocks

    except Exception as e:
        logger.error(f"獲取股票列表失敗: {e}")
        st.error(f"❌ 獲取股票列表失敗: {e}")
        return []


@st.cache_data(ttl=1800)  # 緩存30分鐘
def search_stocks_by_prefix(prefix: str) -> List[Dict[str, str]]:
    """根據前綴搜尋股票，返回股票代碼和名稱"""
    try:
        conn = sqlite3.connect('data/enhanced_stock_database.db')
        cursor = conn.cursor()

        # 搜尋以指定前綴開頭的股票
        query = "SELECT DISTINCT symbol FROM real_stock_data WHERE symbol LIKE ? ORDER BY symbol"
        cursor.execute(query, [f"{prefix}%"])
        symbols = [row[0] for row in cursor.fetchall()]

        conn.close()

        # 獲取股票名稱
        stocks_with_names = []
        for symbol in symbols:
            name = get_stock_name(symbol)
            stocks_with_names.append({
                'symbol': symbol,
                'name': name,
                'display': f"{symbol} - {name}"
            })

        return stocks_with_names

    except Exception as e:
        logger.error(f"搜尋股票失敗: {e}")
        st.error(f"❌ 搜尋股票失敗: {e}")
        return []


@st.cache_data(ttl=3600)  # 緩存1小時
def get_stock_name(symbol: str) -> str:
    """獲取股票名稱"""
    try:
        # 使用全局緩存的股票管理器
        stock_manager = get_stock_manager()

        if stock_manager is not None:
            all_stocks = stock_manager.get_all_stocks()

            for stock in all_stocks:
                if stock.symbol == symbol:
                    return stock.name

        # 如果找不到，使用預設映射表
        name_mapping = {
            "2330.TW": "台積電",
            "2317.TW": "鴻海",
            "2454.TW": "聯發科",
            "2308.TW": "台達電",
            "2303.TW": "聯電",
            "1303.TW": "南亞",
            "1301.TW": "台塑",
            "2002.TW": "中鋼",
            "2412.TW": "中華電",
            "2882.TW": "國泰金",
            "2891.TW": "中信金",
            "2886.TW": "兆豐金",
            "2884.TW": "玉山金",
            "2885.TW": "元大金",
            "2892.TW": "第一金",
            "2881.TW": "富邦金",
            "2883.TW": "開發金",
            "2887.TW": "台新金",
            "2890.TW": "永豐金",
            "2888.TW": "新光金",
            "2880.TW": "華南金",
            "2889.TW": "國票金",
            "2395.TW": "研華",
            "3008.TW": "大立光",
            "2327.TW": "國巨",
            "2382.TW": "廣達",
            "2357.TW": "華碩",
            "2356.TW": "英業達",
            "2409.TW": "友達",
            "3034.TW": "聯詠",
            "2474.TW": "可成",
            "2379.TW": "瑞昱",
            "3045.TW": "台灣大",
            "4938.TW": "和碩",
            "6505.TW": "台塑化",
            "1216.TW": "統一",
            "1101.TW": "台泥",
            "2207.TW": "和泰車",
            "2105.TW": "正新",
            "9910.TW": "豐泰",
            "2912.TW": "統一超",
            "2801.TW": "彰銀",
            "2809.TW": "京城銀",
            "2812.TW": "台中銀",
            "2834.TW": "臺企銀",
            "2845.TW": "遠東銀",
            "2849.TW": "安泰銀",
            "2850.TW": "新產",
            "2851.TW": "中再保",
            "2852.TW": "第一保",
            "2855.TW": "統一證",
            "2867.TW": "三商壽",
            "2880.TW": "華南金",
            "2888.TW": "新光金",
            "2890.TW": "永豐金",
            "2891.TW": "中信金",
            "2892.TW": "第一金",
            "5880.TW": "合庫金",
            "6005.TW": "群益證",
            "6024.TW": "群益期",
            "6239.TW": "力成",
            "8046.TW": "南電",
            "8454.TW": "富邦媒"
        }

        return name_mapping.get(symbol, symbol.replace('.TW', ''))

    except Exception as e:
        logger.warning(f"獲取股票名稱失敗: {e}")
        return symbol.replace('.TW', '')


@st.cache_data(ttl=600)  # 緩存10分鐘
def get_stock_data(symbol: str, days: int = 180) -> pd.DataFrame:
    """獲取股票數據"""
    try:
        conn = sqlite3.connect('data/enhanced_stock_database.db')

        # 計算開始日期
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # 查詢數據
        query = """
        SELECT date, open, high, low, close, volume
        FROM real_stock_data
        WHERE symbol = ? AND date >= ? AND date <= ?
        ORDER BY date
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=[symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
        )

        conn.close()

        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')

        return df

    except Exception as e:
        logger.error(f"獲取股票數據失敗: {e}")
        st.error(f"❌ 獲取股票數據失敗: {e}")
        return pd.DataFrame()


def calculate_technical_indicators(df: pd.DataFrame, indicators: List[str]) -> Dict[str, pd.Series]:
    """計算技術指標"""
    results = {}
    
    if df.empty:
        return results
    
    try:
        # RSI
        if "RSI" in indicators:
            results["RSI"] = calculate_rsi(df['close'])
        
        # MACD
        if "MACD" in indicators:
            macd_line, signal_line, histogram = calculate_macd(df['close'])
            results["MACD"] = macd_line
            results["MACD_Signal"] = signal_line
            results["MACD_Histogram"] = histogram
        
        # SMA
        if "SMA" in indicators:
            results["SMA_20"] = df['close'].rolling(window=20).mean()
            results["SMA_50"] = df['close'].rolling(window=50).mean()
        
        # EMA
        if "EMA" in indicators:
            results["EMA_12"] = df['close'].ewm(span=12).mean()
            results["EMA_26"] = df['close'].ewm(span=26).mean()

        # BBANDS (布林帶)
        if "BBANDS" in indicators:
            bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(df['close'])
            results["BB_Upper"] = bb_upper
            results["BB_Middle"] = bb_middle
            results["BB_Lower"] = bb_lower

        # KD指標
        if "KD" in indicators:
            k_values, d_values = calculate_kd(df)
            results["K"] = k_values
            results["D"] = d_values

        # CCI指標
        if "CCI" in indicators:
            results["CCI"] = calculate_cci(df)

        # ATR指標
        if "ATR" in indicators:
            results["ATR"] = calculate_atr(df)
        
    except Exception as e:
        logger.error(f"計算技術指標失敗: {e}")
        st.error(f"❌ 計算技術指標失敗: {e}")
    
    return results


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """計算RSI指標"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """計算MACD指標"""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0):
    """計算布林帶指標"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, sma, lower_band


def calculate_kd(df: pd.DataFrame, k_period: int = 9, d_period: int = 3):
    """計算KD指標"""
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()

    rsv = 100 * (df['close'] - low_min) / (high_max - low_min)
    k_values = rsv.ewm(alpha=1/3).mean()
    d_values = k_values.ewm(alpha=1/3).mean()

    return k_values, d_values


def calculate_cci(df: pd.DataFrame, period: int = 20):
    """計算CCI指標"""
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    sma_tp = typical_price.rolling(window=period).mean()
    mad = typical_price.rolling(window=period).apply(lambda x: abs(x - x.mean()).mean())
    cci = (typical_price - sma_tp) / (0.015 * mad)
    return cci


def calculate_atr(df: pd.DataFrame, period: int = 14):
    """計算ATR指標"""
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr


def show_stock_charts_separated(symbol: str, indicators: List[str], date_range: str):
    """顯示分離的股票圖表"""
    # 根據日期範圍計算天數
    days_map = {
        "1個月": 30,
        "3個月": 90,
        "6個月": 180,
        "1年": 365
    }
    days = days_map.get(date_range, 180)

    # 獲取股票數據
    df = get_stock_data(symbol, days)

    if df.empty:
        st.warning(f"⚠️ 未找到 {symbol} 的數據")
        return

    # 計算技術指標
    tech_indicators = calculate_technical_indicators(df, indicators)

    st.subheader(f"📈 {symbol} 股票分析")

    # 1. K線圖
    st.markdown("#### 📊 K線圖")
    candlestick_fig = go.Figure()

    candlestick_fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name="K線"
        )
    )

    # 添加移動平均線到K線圖
    if "SMA" in indicators and "SMA_20" in tech_indicators:
        candlestick_fig.add_trace(
            go.Scatter(
                x=df.index,
                y=tech_indicators["SMA_20"],
                name="SMA 20",
                line=dict(color="orange")
            )
        )

    if "EMA" in indicators and "EMA_12" in tech_indicators:
        candlestick_fig.add_trace(
            go.Scatter(
                x=df.index,
                y=tech_indicators["EMA_12"],
                name="EMA 12",
                line=dict(color="blue")
            )
        )

    # 添加布林帶到K線圖
    if "BBANDS" in indicators and "BB_Upper" in tech_indicators:
        candlestick_fig.add_trace(
            go.Scatter(
                x=df.index,
                y=tech_indicators["BB_Upper"],
                name="布林帶上軌",
                line=dict(color="red", dash="dash")
            )
        )
        candlestick_fig.add_trace(
            go.Scatter(
                x=df.index,
                y=tech_indicators["BB_Lower"],
                name="布林帶下軌",
                line=dict(color="red", dash="dash")
            )
        )

    candlestick_fig.update_layout(
        title=f"{symbol} K線圖",
        xaxis_rangeslider_visible=False,
        height=500,
        showlegend=True
    )

    st.plotly_chart(candlestick_fig, use_container_width=True)

    # 2. 成交量圖
    st.markdown("#### 📊 成交量")
    volume_fig = go.Figure()

    volume_fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name="成交量",
            marker_color='lightblue'
        )
    )

    volume_fig.update_layout(
        title=f"{symbol} 成交量",
        height=300,
        showlegend=True
    )

    st.plotly_chart(volume_fig, use_container_width=True)

    # 3. 技術指標圖表
    if indicators:
        for indicator in indicators:
            if indicator == "RSI" and "RSI" in tech_indicators:
                st.markdown("#### 📊 RSI 指標")
                rsi_fig = go.Figure()

                rsi_fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=tech_indicators["RSI"],
                        name="RSI",
                        line=dict(color="purple")
                    )
                )

                # 添加超買超賣線
                rsi_fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="超買線(70)")
                rsi_fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="超賣線(30)")

                rsi_fig.update_layout(
                    title=f"{symbol} RSI 指標",
                    height=300,
                    yaxis=dict(range=[0, 100])
                )

                st.plotly_chart(rsi_fig, use_container_width=True)

            elif indicator == "MACD" and "MACD" in tech_indicators:
                st.markdown("#### 📊 MACD 指標")
                macd_fig = go.Figure()

                macd_fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=tech_indicators["MACD"],
                        name="MACD",
                        line=dict(color="blue")
                    )
                )

                macd_fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=tech_indicators["MACD_Signal"],
                        name="Signal",
                        line=dict(color="red")
                    )
                )

                if "MACD_Histogram" in tech_indicators:
                    macd_fig.add_trace(
                        go.Bar(
                            x=df.index,
                            y=tech_indicators["MACD_Histogram"],
                            name="Histogram",
                            marker_color='gray',
                            opacity=0.6
                        )
                    )

                macd_fig.update_layout(
                    title=f"{symbol} MACD 指標",
                    height=300
                )

                st.plotly_chart(macd_fig, use_container_width=True)

            elif indicator == "KD" and "K" in tech_indicators:
                st.markdown("#### 📊 KD 指標")
                kd_fig = go.Figure()

                kd_fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=tech_indicators["K"],
                        name="K值",
                        line=dict(color="blue")
                    )
                )

                kd_fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=tech_indicators["D"],
                        name="D值",
                        line=dict(color="red")
                    )
                )

                # 添加超買超賣線
                kd_fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="超買線(80)")
                kd_fig.add_hline(y=20, line_dash="dash", line_color="green", annotation_text="超賣線(20)")

                kd_fig.update_layout(
                    title=f"{symbol} KD 指標",
                    height=300,
                    yaxis=dict(range=[0, 100])
                )

                st.plotly_chart(kd_fig, use_container_width=True)

            elif indicator == "CCI" and "CCI" in tech_indicators:
                st.markdown("#### 📊 CCI 指標")
                cci_fig = go.Figure()

                cci_fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=tech_indicators["CCI"],
                        name="CCI",
                        line=dict(color="purple")
                    )
                )

                # 添加超買超賣線
                cci_fig.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="超買線(100)")
                cci_fig.add_hline(y=-100, line_dash="dash", line_color="green", annotation_text="超賣線(-100)")

                cci_fig.update_layout(
                    title=f"{symbol} CCI 指標",
                    height=300
                )

                st.plotly_chart(cci_fig, use_container_width=True)

            elif indicator == "ATR" and "ATR" in tech_indicators:
                st.markdown("#### 📊 ATR 指標")
                atr_fig = go.Figure()

                atr_fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=tech_indicators["ATR"],
                        name="ATR",
                        line=dict(color="orange")
                    )
                )

                atr_fig.update_layout(
                    title=f"{symbol} ATR 指標",
                    height=300
                )

                st.plotly_chart(atr_fig, use_container_width=True)

    # 顯示基本統計信息
    st.markdown("#### 📊 基本統計")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("最新收盤價", f"{df['close'].iloc[-1]:.2f}")
    with col2:
        change = df['close'].iloc[-1] - df['close'].iloc[-2] if len(df) > 1 else 0
        st.metric("日漲跌", f"{change:.2f}")
    with col3:
        st.metric("最高價", f"{df['high'].max():.2f}")
    with col4:
        st.metric("最低價", f"{df['low'].min():.2f}")


def show_stock_data_table(symbol: str, date_range: str):
    """顯示股票數據表格"""
    days_map = {
        "1個月": 30,
        "3個月": 90,
        "6個月": 180,
        "1年": 365
    }
    days = days_map.get(date_range, 180)
    
    df = get_stock_data(symbol, days)
    
    if df.empty:
        st.warning(f"⚠️ 未找到 {symbol} 的數據")
        return
    
    st.subheader(f"📋 {symbol} 數據表格")
    st.dataframe(df.round(2), use_container_width=True)


if __name__ == "__main__":
    show_data_view_page()
