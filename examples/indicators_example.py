"""
交易指標示例腳本

此腳本展示如何使用 indicators.py 模組中的各種交易指標。
包括技術指標、基本面指標和情緒指標的計算、標準化和比較。
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 導入指標模組
from src.core.indicators import (
    TechnicalIndicators,
    FundamentalIndicators,
    SentimentIndicators,
)
from src.core.indicators import evaluate_indicator_efficacy, generate_trading_signals


def generate_sample_price_data(days=100):
    """
    生成示例價格資料

    Args:
        days (int): 天數

    Returns:
        pd.DataFrame: 示例價格資料
    """
    # 生成日期範圍
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    date_range = pd.date_range(start=start_date, end=end_date, freq="B")

    # 生成價格資料
    np.random.seed(42)  # 設置隨機種子以獲得可重複的結果

    # 生成隨機價格走勢
    close = 100 + np.cumsum(np.random.normal(0.001, 0.02, len(date_range)))

    # 生成其他 OHLCV 資料
    high = close * (1 + np.random.uniform(0, 0.03, len(date_range)))
    low = close * (1 - np.random.uniform(0, 0.03, len(date_range)))
    open_price = low + np.random.uniform(0, 1, len(date_range)) * (high - low)
    volume = np.random.uniform(1000, 10000, len(date_range))

    # 創建 DataFrame
    price_data = pd.DataFrame(
        {
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=date_range,
    )

    return price_data


def generate_sample_financial_data(price_data):
    """
    生成示例財務資料

    Args:
        price_data (pd.DataFrame): 價格資料

    Returns:
        dict: 示例財務資料字典
    """
    # 生成季度日期範圍
    quarterly_dates = pd.date_range(
        start=price_data.index[0], end=price_data.index[-1], freq="Q"
    )

    # 生成 EPS 資料
    np.random.seed(42)
    eps = np.random.uniform(0.5, 2.0, len(quarterly_dates))
    eps = np.cumsum(np.random.normal(0.05, 0.1, len(quarterly_dates)))
    eps = np.abs(eps) + 0.5  # 確保 EPS 為正

    # 創建損益表
    income_statement = pd.DataFrame(
        {"EPS": eps, "Revenue": eps * 1000000, "Net Income": eps * 100000},
        index=quarterly_dates,
    )

    # 創建資產負債表
    balance_sheet = pd.DataFrame(
        {
            "Total Assets": np.random.uniform(1000000, 2000000, len(quarterly_dates)),
            "Total Liabilities": np.random.uniform(
                500000, 1000000, len(quarterly_dates)
            ),
            "Total Equity": np.random.uniform(500000, 1000000, len(quarterly_dates)),
            "Common Stock": np.ones(len(quarterly_dates)) * 100000,
            "BPS": np.random.uniform(10, 20, len(quarterly_dates)),
        },
        index=quarterly_dates,
    )

    return {
        "income_statement": income_statement,
        "balance_sheet": balance_sheet,
        "price": price_data,
    }


def generate_sample_sentiment_data(price_data):
    """
    生成示例情緒資料

    Args:
        price_data (pd.DataFrame): 價格資料

    Returns:
        dict: 示例情緒資料字典
    """
    # 生成日期範圍
    date_range = price_data.index

    # 生成新聞情緒資料
    np.random.seed(42)
    news_sentiment = np.random.normal(0.1, 0.3, len(date_range))

    # 添加一些趨勢
    for i in range(1, len(news_sentiment)):
        news_sentiment[i] = news_sentiment[i - 1] * 0.7 + news_sentiment[i] * 0.3

    # 創建新聞情緒 DataFrame
    news_df = pd.DataFrame(
        {
            "sentiment_score": news_sentiment,
            "topic": np.random.choice(
                ["economy", "company", "industry", "market"], len(date_range)
            ),
        },
        index=date_range,
    )

    # 生成社交媒體情緒資料
    social_sentiment = np.random.normal(0, 0.5, len(date_range))

    # 添加一些趨勢
    for i in range(1, len(social_sentiment)):
        social_sentiment[i] = social_sentiment[i - 1] * 0.5 + social_sentiment[i] * 0.5

    # 創建社交媒體情緒 DataFrame
    social_df = pd.DataFrame(
        {
            "sentiment_score": social_sentiment,
            "platform": np.random.choice(
                ["twitter", "reddit", "stocktwits"], len(date_range)
            ),
        },
        index=date_range,
    )

    return {"news": news_df, "social": social_df}


def main():
    """
    主函數
    """
    print("生成示例資料...")
    price_data = generate_sample_price_data(days=252)  # 約一年的交易日
    financial_data = generate_sample_financial_data(price_data)
    sentiment_data = generate_sample_sentiment_data(price_data)

    print("\n計算技術指標...")
    tech_indicators = TechnicalIndicators(price_data)

    # 計算各種技術指標
    sma_20 = tech_indicators.calculate_sma(period=20)
    ema_20 = tech_indicators.calculate_ema(period=20)
    rsi_14 = tech_indicators.calculate_rsi(period=14)
    upper, middle, lower = tech_indicators.calculate_bollinger_bands(
        period=20, std_dev=2.0
    )
    macd, signal, hist = tech_indicators.calculate_macd()
    obv = tech_indicators.calculate_obv()
    atr = tech_indicators.calculate_atr()

    print("技術指標計算完成。")

    # 標準化指標
    print("\n標準化指標...")
    standardized = tech_indicators.standardize_indicators(method="zscore")
    print("標準化完成。")

    # 比較指標
    print("\n比較不同指標的表現...")
    comparison = tech_indicators.compare_indicators(price_data["close"])
    print("指標比較結果:")
    print(comparison)

    print("\n計算基本面指標...")
    fund_indicators = FundamentalIndicators(financial_data)

    # 計算各種基本面指標
    eps_growth = fund_indicators.calculate_eps_growth()
    pe_ratio = fund_indicators.calculate_pe_ratio()
    pb_ratio = fund_indicators.calculate_pb_ratio()

    print("基本面指標計算完成。")

    print("\n計算情緒指標...")
    sent_indicators = SentimentIndicators(sentiment_data)

    # 計算各種情緒指標
    news_sentiment = sent_indicators.calculate_news_sentiment()
    social_sentiment = sent_indicators.calculate_social_sentiment()
    topic_sentiment = sent_indicators.calculate_topic_sentiment()

    print("情緒指標計算完成。")

    # 評估指標有效性
    print("\n評估指標有效性...")

    # 合併所有指標
    all_indicators = pd.DataFrame(
        {
            "SMA_20": sma_20,
            "EMA_20": ema_20,
            "RSI_14": rsi_14,
            "BBANDS_width": (upper - lower) / middle,
            "MACD": macd,
            "OBV": obv,
            "ATR_14": atr,
            "PE_ratio": pe_ratio,
            "PB_ratio": pb_ratio,
            "News_sentiment": news_sentiment,
            "Social_sentiment": social_sentiment,
        }
    )

    efficacy = evaluate_indicator_efficacy(price_data, all_indicators)
    print("指標有效性評估結果:")
    print(efficacy)

    # 生成交易訊號
    print("\n生成交易訊號...")
    signal_rules = {
        "RSI_14": {"type": "threshold", "buy_threshold": 30, "sell_threshold": 70},
        "SMA_20": {"type": "crossover", "reference": "EMA", "period": 50},
        "MACD": {"type": "momentum", "period": 1},
    }

    signals = generate_trading_signals(price_data, all_indicators, signal_rules)
    print("交易訊號生成完成。")

    # 繪製圖表
    print("\n繪製圖表...")
    plt.figure(figsize=(12, 8))

    # 繪製價格和移動平均線
    plt.subplot(3, 1, 1)
    plt.plot(price_data.index, price_data["close"], label="Close")
    plt.plot(price_data.index, sma_20, label="SMA(20)")
    plt.plot(price_data.index, ema_20, label="EMA(20)")
    plt.fill_between(price_data.index, lower, upper, alpha=0.2, label="Bollinger Bands")
    plt.title("Price and Moving Averages")
    plt.legend()

    # 繪製 RSI
    plt.subplot(3, 1, 2)
    plt.plot(price_data.index, rsi_14, label="RSI(14)")
    plt.axhline(y=70, color="r", linestyle="-", alpha=0.3)
    plt.axhline(y=30, color="g", linestyle="-", alpha=0.3)
    plt.title("RSI")
    plt.legend()

    # 繪製 MACD
    plt.subplot(3, 1, 3)
    plt.plot(price_data.index, macd, label="MACD")
    plt.plot(price_data.index, signal, label="Signal")
    plt.bar(price_data.index, hist, label="Histogram", alpha=0.3)
    plt.title("MACD")
    plt.legend()

    plt.tight_layout()
    plt.savefig("indicators_example.png")
    print("圖表已保存為 'indicators_example.png'")

    print("\n示例完成。")


if __name__ == "__main__":
    main()
