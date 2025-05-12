import datetime
import pandas as pd
from data_sources.mcp_client import MCPClient


def fetch_market_news(query, days=7, server_url="http://localhost:3000"):
    client = MCPClient(server_url)
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime(
        "%Y-%m-%d"
    )
    news = client.crawl_perplexity(query, start_date, end_date)
    return pd.DataFrame(news)


def analyze_market_sentiment(news_df):
    if news_df.empty:
        return {"sentiment": "neutral", "score": 0, "count": 0}
    pos = news_df["sentiment"].str.count("positive").sum()
    neg = news_df["sentiment"].str.count("negative").sum()
    total = pos + neg
    score = (pos - neg) / total if total else 0
    sentiment = "positive" if score > 0.2 else "negative" if score < -0.2 else "neutral"
    return {
        "sentiment": sentiment,
        "score": score,
        "count": len(news_df),
        "positive_count": pos,
        "negative_count": neg,
    }
