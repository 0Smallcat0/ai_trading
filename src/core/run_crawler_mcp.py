import argparse
from mcp_data_ingest import fetch_market_news, analyze_market_sentiment

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, default="台積電")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--server-url", type=str, default="http://localhost:3000")
    args = parser.parse_args()

    news_df = fetch_market_news(args.query, args.days, args.server_url)
    print(news_df.head())
    sentiment = analyze_market_sentiment(news_df)
    print("情緒分析：", sentiment)
