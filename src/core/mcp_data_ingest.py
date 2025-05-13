import pandas as pd
from src.data_sources.mcp_crawler import crawl_stock_news


def fetch_market_news(query, days=7, fulltext=False):
    """
    獲取市場新聞

    Args:
        query (str): 查詢關鍵字
        days (int): 往前查詢的天數
        fulltext (bool): 是否獲取全文

    Returns:
        pandas.DataFrame: 新聞資料框
    """
    news = crawl_stock_news(query, days=days, fulltext=fulltext)
    return pd.DataFrame(news)


def analyze_market_sentiment(news_df):
    """
    分析市場情緒

    Args:
        news_df (pandas.DataFrame): 新聞資料框

    Returns:
        dict: 情緒分析結果，包含以下欄位：
            - sentiment (str): 情緒，'positive', 'negative', 或 'neutral'
            - score (float): 情緒分數，範圍為 [-1, 1]
            - count (int): 新聞數量
            - positive_count (int): 正面新聞數量
            - negative_count (int): 負面新聞數量
    """
    if news_df.empty:
        return {"sentiment": "neutral", "score": 0, "count": 0, "positive_count": 0, "negative_count": 0}

    # 檢查是否有情緒欄位
    if "sentiment" not in news_df.columns:
        # 如果沒有情緒欄位，嘗試使用標題和內容進行簡單的情緒分析
        positive_words = ["漲", "上升", "增長", "獲利", "成長", "突破", "利多", "看好", "樂觀"]
        negative_words = ["跌", "下降", "虧損", "衰退", "破產", "危機", "利空", "看壞", "悲觀"]

        # 計算正面和負面詞彙出現的次數
        pos = 0
        neg = 0

        # 檢查標題
        if "title" in news_df.columns:
            for word in positive_words:
                pos += news_df["title"].str.count(word).sum()
            for word in negative_words:
                neg += news_df["title"].str.count(word).sum()

        # 檢查內容
        if "content" in news_df.columns:
            for word in positive_words:
                pos += news_df["content"].str.count(word).sum()
            for word in negative_words:
                neg += news_df["content"].str.count(word).sum()
    else:
        # 如果有情緒欄位，直接使用
        pos = news_df["sentiment"].str.count("positive").sum()
        neg = news_df["sentiment"].str.count("negative").sum()

    total = pos + neg
    score = (pos - neg) / (total if total else 1)  # 避免除以零

    # 根據分數判斷情緒
    sentiment = "positive" if score > 0.2 else "negative" if score < -0.2 else "neutral"

    return {
        "sentiment": sentiment,
        "score": score,
        "count": len(news_df),
        "positive_count": pos,
        "negative_count": neg,
    }
