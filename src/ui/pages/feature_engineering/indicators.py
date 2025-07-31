"""
指標定義和樣本數據生成模組

此模組包含：
- 情緒指標定義
- 樣本特徵數據生成
- 指標數據處理工具
"""

import numpy as np
import pandas as pd
from datetime import date


def get_available_sentiment_indicators():
    """獲取可用的情緒指標"""
    # 實際應用中，這裡應該從系統中獲取真實的情緒指標列表
    # 這裡使用模擬數據進行演示

    sentiment_indicators = [
        {
            "name": "NEWS_SENT",
            "full_name": "新聞情緒指標 (News Sentiment)",
            "category": "媒體情緒",
            "description": "基於新聞報導的情緒分析，用於評估市場對特定股票或行業的情緒。",
            "calculation": "使用 NLP 模型分析新聞文本，計算情緒分數。",
            "value_range": "-1 到 1",
            "interpretation": "值越接近 1 表示正面情緒越強，越接近 -1 表示負面情緒越強。",
            "data_source": "新聞 API",
            "update_frequency": "每日",
            "example_code": "calculator.calculate_sentiment_indicators(indicators=['NEWS_SENT'])",
        },
        {
            "name": "SOCIAL_SENT",
            "full_name": "社交媒體情緒指標 (Social Media Sentiment)",
            "category": "社交媒體情緒",
            "description": "基於社交媒體的情緒分析，用於評估散戶投資者對特定股票的情緒。",
            "calculation": "使用 NLP 模型分析社交媒體文本，計算情緒分數。",
            "value_range": "-1 到 1",
            "interpretation": "值越接近 1 表示正面情緒越強，越接近 -1 表示負面情緒越強。",
            "data_source": "社交媒體 API",
            "update_frequency": "每小時",
            "example_code": "calculator.calculate_sentiment_indicators(indicators=['SOCIAL_SENT'])",
        },
        {
            "name": "SENT_VOL",
            "full_name": "情緒波動指標 (Sentiment Volatility)",
            "category": "情緒波動",
            "description": "測量情緒分數的波動性，用於評估市場情緒的穩定性。",
            "calculation": "情緒分數的標準差",
            "value_range": "非負數",
            "interpretation": "值越高表示情緒波動越大，市場不確定性越高。",
            "data_source": "新聞和社交媒體 API",
            "update_frequency": "每日",
            "example_code": "calculator.calculate_sentiment_indicators(indicators=['SENT_VOL'])",
        },
        {
            "name": "SENT_DIFF",
            "full_name": "情緒差異指標 (Sentiment Differential)",
            "category": "情緒差異",
            "description": "測量不同來源情緒分數的差異，用於評估市場情緒的一致性。",
            "calculation": "新聞情緒分數 - 社交媒體情緒分數",
            "value_range": "-2 到 2",
            "interpretation": "值接近 0 表示不同來源的情緒一致，絕對值越大表示差異越大。",
            "data_source": "新聞和社交媒體 API",
            "update_frequency": "每日",
            "example_code": "calculator.calculate_sentiment_indicators(indicators=['SENT_DIFF'])",
        },
        {
            "name": "TOPIC_SENT",
            "full_name": "主題情緒指標 (Topic Sentiment)",
            "category": "主題情緒",
            "description": "針對特定主題的情緒分析，如產品發布、財報、管理層變動等。",
            "calculation": "使用 NLP 模型分析特定主題的文本，計算情緒分數。",
            "value_range": "-1 到 1",
            "interpretation": "值越接近 1 表示對特定主題的正面情緒越強。",
            "data_source": "新聞和社交媒體 API",
            "update_frequency": "事件驅動",
            "example_code": "calculator.calculate_sentiment_indicators(indicators=['TOPIC_SENT'], topics=['earnings'])",
        },
    ]

    return sentiment_indicators


def generate_sample_feature_data(
    feature_type: str, symbols: list, start_date: date, end_date: date
) -> pd.DataFrame:
    """生成樣本特徵數據"""
    # 導入需要的函數
    try:
        from .utils import get_available_technical_indicators, get_available_fundamental_indicators
    except ImportError:
        try:
            from src.ui.pages.feature_engineering.utils import get_available_technical_indicators, get_available_fundamental_indicators
        except ImportError:
            # 提供佔位符函數
            def get_available_technical_indicators():
                return []
            def get_available_fundamental_indicators():
                return []
    
    # 生成日期範圍
    date_range = pd.date_range(start=start_date, end=end_date, freq="D")
    
    # 創建基礎數據框
    data = pd.DataFrame({"日期": date_range})
    
    # 根據特徵類型生成不同的特徵
    if feature_type == "技術指標":
        # 獲取技術指標列表
        tech_indicators = get_available_technical_indicators()
        tech_indicator_names = [ind["name"] for ind in tech_indicators]
        
        # 為每個股票生成技術指標
        for symbol in symbols:
            # 使用股票代碼作為隨機種子，確保同一股票每次生成相同數據
            np.random.seed(hash(symbol) % 10000)
            
            # 為每個技術指標生成數據
            for ind_name in tech_indicator_names[:5]:  # 只使用前 5 個指標
                # 生成隨機數據
                if ind_name in ["RSI", "STOCH", "CCI", "ADX"]:  # 有範圍限制的指標
                    values = np.random.uniform(0, 100, len(date_range))
                else:  # 無範圍限制的指標
                    base_value = 100 + hash(symbol + ind_name) % 900
                    values = np.random.normal(
                        base_value, base_value * 0.1, len(date_range)
                    )
                
                # 添加到數據框
                data[f"{symbol}_{ind_name}"] = values
    
    elif feature_type == "基本面指標":
        # 獲取基本面指標列表
        fund_indicators = get_available_fundamental_indicators()
        fund_indicator_names = [ind["name"] for ind in fund_indicators]
        
        # 為每個股票生成基本面指標
        for symbol in symbols:
            np.random.seed(hash(symbol) % 10000)
            
            for ind_name in fund_indicator_names[:5]:  # 只使用前 5 個指標
                if ind_name == "PE":
                    values = np.random.uniform(5, 50, len(date_range))
                elif ind_name == "PB":
                    values = np.random.uniform(0.5, 5, len(date_range))
                elif ind_name in ["ROE", "ROA"]:
                    values = np.random.uniform(0, 30, len(date_range))
                elif ind_name == "DY":
                    values = np.random.uniform(0, 10, len(date_range))
                else:
                    base_value = 1 + hash(symbol + ind_name) % 10
                    values = np.random.normal(
                        base_value, base_value * 0.2, len(date_range)
                    )
                
                data[f"{symbol}_{ind_name}"] = values
    
    elif feature_type == "情緒指標":
        # 獲取情緒指標列表
        sent_indicators = get_available_sentiment_indicators()
        sent_indicator_names = [ind["name"] for ind in sent_indicators]
        
        # 為每個股票生成情緒指標
        for symbol in symbols:
            np.random.seed(hash(symbol) % 10000)
            
            for ind_name in sent_indicator_names[:3]:  # 只使用前 3 個指標
                if ind_name in ["NEWS_SENT", "SOCIAL_SENT", "TOPIC_SENT"]:
                    values = np.random.uniform(-1, 1, len(date_range))
                elif ind_name == "SENT_VOL":
                    values = np.random.uniform(0, 1, len(date_range))
                elif ind_name == "SENT_DIFF":
                    values = np.random.uniform(-2, 2, len(date_range))
                else:
                    values = np.random.normal(0, 0.5, len(date_range))
                
                data[f"{symbol}_{ind_name}"] = values
    
    return data
