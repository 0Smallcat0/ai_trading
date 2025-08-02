"""
特徵工程頁面共用工具函數

此模組包含特徵工程頁面的共用工具函數，包括：
- 服務初始化
- 數據獲取
- 指標定義
- 樣本數據生成
"""

import os
import json
import time
import sqlite3
import numpy as np
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from pathlib import Path

# 導入特徵工程服務
from src.core.feature_engineering_service import FeatureEngineeringService


# 初始化服務
@st.cache_resource
def get_feature_service():
    """獲取特徵工程服務實例"""
    return FeatureEngineeringService()


def get_stock_list():
    """獲取股票列表"""
    # 實際應用中，這裡應該從數據庫或API獲取真實的股票列表
    # 這裡使用模擬數據進行演示
    stocks = [
        {"symbol": "2330", "name": "台積電", "market": "TSE"},
        {"symbol": "2317", "name": "鴻海", "market": "TSE"},
        {"symbol": "2454", "name": "聯發科", "market": "TSE"},
        {"symbol": "2881", "name": "富邦金", "market": "TSE"},
        {"symbol": "2882", "name": "國泰金", "market": "TSE"},
        {"symbol": "2412", "name": "中華電", "market": "TSE"},
        {"symbol": "2303", "name": "聯電", "market": "TSE"},
        {"symbol": "3008", "name": "大立光", "market": "TSE"},
        {"symbol": "2002", "name": "中鋼", "market": "TSE"},
        {"symbol": "1301", "name": "台塑", "market": "TSE"},
        {"symbol": "1303", "name": "南亞", "market": "TSE"},
        {"symbol": "2886", "name": "兆豐金", "market": "TSE"},
        {"symbol": "2891", "name": "中信金", "market": "TSE"},
        {"symbol": "2892", "name": "第一金", "market": "TSE"},
        {"symbol": "2884", "name": "玉山金", "market": "TSE"},
        {"symbol": "2885", "name": "元大金", "market": "TSE"},
        {"symbol": "2890", "name": "永豐金", "market": "TSE"},
        {"symbol": "2887", "name": "台新金", "market": "TSE"},
        {"symbol": "2888", "name": "新光金", "market": "TSE"},
        {"symbol": "2889", "name": "國票金", "market": "TSE"},
    ]
    return stocks


def get_available_technical_indicators():
    """獲取可用的技術指標"""
    # 實際應用中，這裡應該從系統中獲取真實的技術指標列表
    # 這裡使用模擬數據進行演示

    technical_indicators = [
        {
            "name": "RSI",
            "full_name": "相對強弱指標 (Relative Strength Index)",
            "category": "動量指標",
            "description": "測量價格變動的速度和幅度，用於判斷市場是否超買或超賣。",
            "parameters": {"window": 14},
            "value_range": "0-100",
            "interpretation": "RSI > 70 表示超買，RSI < 30 表示超賣。",
            "calculation_cost": "低",
            "data_requirements": ["close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['RSI'])",
        },
        {
            "name": "MACD",
            "full_name": "移動平均收斂散度 (Moving Average Convergence Divergence)",
            "category": "趨勢指標",
            "description": "通過比較兩條不同週期的指數移動平均線來判斷趨勢的強度和方向。",
            "parameters": {"fast_period": 12, "slow_period": 26, "signal_period": 9},
            "value_range": "無固定範圍",
            "interpretation": "MACD 線穿越信號線向上表示買入信號，向下表示賣出信號。",
            "calculation_cost": "中",
            "data_requirements": ["close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['MACD'])",
        },
        {
            "name": "SMA",
            "full_name": "簡單移動平均線 (Simple Moving Average)",
            "category": "趨勢指標",
            "description": "計算過去 N 個週期的價格平均值，用於平滑價格數據和識別趨勢。",
            "parameters": {"window": 20},
            "value_range": "與價格相同",
            "interpretation": "價格穿越 SMA 向上表示上升趨勢，向下表示下降趨勢。",
            "calculation_cost": "低",
            "data_requirements": ["close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['SMA'])",
        },
        {
            "name": "EMA",
            "full_name": "指數移動平均線 (Exponential Moving Average)",
            "category": "趨勢指標",
            "description": "與 SMA 類似，但給予最近的價格更高的權重，對價格變化反應更敏感。",
            "parameters": {"window": 20},
            "value_range": "與價格相同",
            "interpretation": "價格穿越 EMA 向上表示上升趨勢，向下表示下降趨勢。",
            "calculation_cost": "低",
            "data_requirements": ["close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['EMA'])",
        },
        {
            "name": "BBANDS",
            "full_name": "布林帶 (Bollinger Bands)",
            "category": "波動指標",
            "description": "由移動平均線加減標準差構成的上下通道，用於判斷價格波動性和可能的反轉點。",
            "parameters": {"window": 20, "std_dev": 2},
            "value_range": "與價格相同",
            "interpretation": "價格接近上軌表示可能超買，接近下軌表示可能超賣。",
            "calculation_cost": "中",
            "data_requirements": ["close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['BBANDS'])",
        },
        {
            "name": "STOCH",
            "full_name": "隨機指標 (Stochastic Oscillator)",
            "category": "動量指標",
            "description": "比較收盤價與特定時期內的價格範圍，用於判斷市場是否超買或超賣。",
            "parameters": {"fastk_period": 5, "slowk_period": 3, "slowd_period": 3},
            "value_range": "0-100",
            "interpretation": "K 線穿越 D 線向上表示買入信號，向下表示賣出信號。",
            "calculation_cost": "中",
            "data_requirements": ["high", "low", "close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['STOCH'])",
        },
        {
            "name": "CCI",
            "full_name": "商品通道指數 (Commodity Channel Index)",
            "category": "動量指標",
            "description": "測量當前價格相對於過去一段時間內平均價格的偏離程度。",
            "parameters": {"window": 20},
            "value_range": "通常在 -100 到 +100 之間",
            "interpretation": "CCI > 100 表示超買，CCI < -100 表示超賣。",
            "calculation_cost": "中",
            "data_requirements": ["high", "low", "close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['CCI'])",
        },
        {
            "name": "ATR",
            "full_name": "平均真實範圍 (Average True Range)",
            "category": "波動指標",
            "description": "測量市場波動性，不考慮價格方向。",
            "parameters": {"window": 14},
            "value_range": "非負數",
            "interpretation": "ATR 值越高表示波動性越大，可用於設置止損點。",
            "calculation_cost": "低",
            "data_requirements": ["high", "low", "close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['ATR'])",
        },
        {
            "name": "OBV",
            "full_name": "能量潮 (On-Balance Volume)",
            "category": "成交量指標",
            "description": "將成交量與價格變動結合，用於確認價格趨勢。",
            "parameters": {},
            "value_range": "無固定範圍",
            "interpretation": "OBV 與價格同向變動表示趨勢強勁，反向變動表示可能反轉。",
            "calculation_cost": "低",
            "data_requirements": ["close", "volume"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['OBV'])",
        },
        {
            "name": "ADX",
            "full_name": "平均趨向指數 (Average Directional Index)",
            "category": "趨勢指標",
            "description": "測量趨勢的強度，不考慮趨勢方向。",
            "parameters": {"window": 14},
            "value_range": "0-100",
            "interpretation": "ADX > 25 表示強趨勢，ADX < 20 表示弱趨勢。",
            "calculation_cost": "高",
            "data_requirements": ["high", "low", "close"],
            "example_code": "calculator.calculate_technical_indicators(indicators=['ADX'])",
        },
    ]

    return technical_indicators


def get_available_fundamental_indicators():
    """獲取可用的基本面指標"""
    # 實際應用中，這裡應該從系統中獲取真實的基本面指標列表
    # 這裡使用模擬數據進行演示

    fundamental_indicators = [
        {
            "name": "PE",
            "full_name": "本益比 (Price-to-Earnings Ratio)",
            "category": "估值指標",
            "description": "股價與每股盈餘的比率，用於評估股票的估值水平。",
            "calculation": "股價 / 每股盈餘",
            "interpretation": "PE 值越低表示估值越低，但需要與行業平均和歷史水平比較。",
            "data_source": "財務報表",
            "update_frequency": "季度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['PE'])",
        },
        {
            "name": "PB",
            "full_name": "股價淨值比 (Price-to-Book Ratio)",
            "category": "估值指標",
            "description": "股價與每股淨資產的比率，用於評估股票的估值水平。",
            "calculation": "股價 / 每股淨資產",
            "interpretation": "PB 值越低表示估值越低，適合評估資產密集型企業。",
            "data_source": "財務報表",
            "update_frequency": "季度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['PB'])",
        },
        {
            "name": "ROE",
            "full_name": "股東權益報酬率 (Return on Equity)",
            "category": "獲利能力指標",
            "description": "淨利潤與股東權益的比率，用於評估公司運用股東資金的效率。",
            "calculation": "淨利潤 / 股東權益",
            "interpretation": "ROE 越高表示公司運用股東資金的效率越高。",
            "data_source": "財務報表",
            "update_frequency": "季度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['ROE'])",
        },
        {
            "name": "ROA",
            "full_name": "資產報酬率 (Return on Assets)",
            "category": "獲利能力指標",
            "description": "淨利潤與總資產的比率，用於評估公司運用資產的效率。",
            "calculation": "淨利潤 / 總資產",
            "interpretation": "ROA 越高表示公司運用資產的效率越高。",
            "data_source": "財務報表",
            "update_frequency": "季度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['ROA'])",
        },
        {
            "name": "DY",
            "full_name": "股息殖利率 (Dividend Yield)",
            "category": "收益指標",
            "description": "年度股息與股價的比率，用於評估股票的收益水平。",
            "calculation": "年度股息 / 股價",
            "interpretation": "DY 越高表示股票的收益水平越高，適合收益型投資者。",
            "data_source": "財務報表",
            "update_frequency": "年度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['DY'])",
        },
        {
            "name": "DE",
            "full_name": "負債權益比 (Debt-to-Equity Ratio)",
            "category": "財務結構指標",
            "description": "總負債與股東權益的比率，用於評估公司的財務槓桿。",
            "calculation": "總負債 / 股東權益",
            "interpretation": "DE 越高表示公司的財務槓桿越高，風險也越高。",
            "data_source": "財務報表",
            "update_frequency": "季度",
            "example_code": "calculator.calculate_fundamental_indicators(indicators=['DE'])",
        },
        {
            "name": "CR",
            "full_name": "流動比率 (Current Ratio)",
            "category": "流動性指標",
            "description": "流動資產與流動負債的比率，用於評估公司的短期償債能力。",
            "calculation": "流動資產 / 流動負債",
            "interpretation": "CR > 1 表示公司有足夠的流動資產償還短期債務。",
        },
        {
            "name": "EPS_G",
            "full_name": "每股盈餘成長率 (EPS Growth Rate)",
            "category": "成長指標",
            "description": "每股盈餘的年度成長率，用於評估公司的盈利成長性。",
            "calculation": "(本期 EPS - 上期 EPS) / 上期 EPS",
            "interpretation": "EPS_G 越高表示公司的盈利成長性越好。",
            "data_source": "財務報表",
        },
    ]

    return fundamental_indicators

# 情緒指標和樣本數據生成功能已移至 indicators.py
# 延遲導入以避免循環依賴
def get_available_sentiment_indicators():
    try:
        from .indicators import get_available_sentiment_indicators as _get_indicators
        return _get_indicators()
    except ImportError:
        return []

def generate_sample_feature_data(*args, **kwargs):
    try:
        from .indicators import generate_sample_feature_data as _generate_data
        return _generate_data(*args, **kwargs)
    except ImportError:
        import pandas as pd
        return pd.DataFrame()
