# 股票市場數據來源研究 / Stock Market Data Source Research

本文檔提供了各種股票市場數據來源的詳細研究，包括股票市場 API、財務報表來源、新聞情緒數據等。
This document provides detailed research on various stock market data sources, including stock market APIs, financial statement sources, news sentiment data, etc.

## 目錄 / Table of Contents

1. [股票市場 API / Stock Market APIs](#stock-market-apis)
   - [Yahoo Finance](#yahoo-finance)
   - [Alpha Vantage](#alpha-vantage)
   - [Finnhub](#finnhub)
   - [券商 API / Broker APIs](#broker-apis)
   - [台灣證券交易所 / Taiwan Stock Exchange (TWSE)](#twse)
2. [財務報表來源 / Financial Statement Sources](#financial-statement-sources)
   - [台灣公開資訊觀測站 / Taiwan Market Observation Post System (MOPS)](#mops)
   - [Yahoo Finance](#yahoo-finance-financial)
   - [Alpha Vantage](#alpha-vantage-financial)
   - [Finnhub](#finnhub-financial)
3. [新聞情緒數據 / News Sentiment Data](#news-sentiment-data)
   - [Perplexity (via MCP)](#perplexity)
   - [Alpha Vantage News Sentiment](#alpha-vantage-news)
   - [Finnhub News Sentiment](#finnhub-news)
   - [台灣財經新聞網站 / Taiwan Financial News Websites](#taiwan-news)
4. [數據更新頻率與歷史覆蓋範圍 / Data Update Frequency and Historical Coverage](#data-update-frequency)

---

<a name="stock-market-apis"></a>
## 1. 股票市場 API / Stock Market APIs

<a name="yahoo-finance"></a>
### Yahoo Finance

**API 功能與限制 / API Capabilities and Limitations:**
- 提供歷史價格數據（日、週、月）
- 提供公司基本資料
- 提供財務報表數據
- 提供即時報價（延遲 15 分鐘）
- 非官方 API，可能隨時變更

**可用數據類型 / Available Data Types:**
- 歷史價格（開盤、最高、最低、收盤、成交量、調整收盤價）
- 公司基本資料（市值、行業、員工數等）
- 財務報表（資產負債表、損益表、現金流量表）
- 技術指標（移動平均線、RSI 等）

**更新頻率 / Update Frequency:**
- 歷史數據：每日更新
- 即時報價：延遲 15 分鐘

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 美股：1970 年代至今
- 台股：2000 年代至今
- 其他市場：視情況而定

**認證要求 / Authentication Requirements:**
- 無需 API 金鑰
- 使用 yfinance 等第三方庫即可訪問

**速率限制 / Rate Limits:**
- 無明確限制，但過度請求可能導致 IP 被封鎖
- 建議限制為每分鐘 60 次請求

**價格 / Pricing:**
- 免費

**優點 / Pros:**
- 完全免費
- 數據覆蓋範圍廣
- 易於使用
- 已有 yfinance 庫可直接使用

**缺點 / Cons:**
- 非官方 API，穩定性較差
- 數據可能不完整或有延遲
- 無法保證長期可用性
- 即時數據有 15 分鐘延遲

<a name="alpha-vantage"></a>
### Alpha Vantage

**API 功能與限制 / API Capabilities and Limitations:**
- 提供股票、外匯、加密貨幣等數據
- 提供技術指標計算
- 提供基本面數據
- 提供全球經濟指標

**可用數據類型 / Available Data Types:**
- 股票時間序列數據（分鐘、小時、日、週、月）
- 技術指標（50+ 種指標）
- 基本面數據（收益、資產負債表等）
- 外匯和加密貨幣數據
- 全球經濟指標

**更新頻率 / Update Frequency:**
- 股票數據：實時至每日（取決於訂閱計劃）
- 基本面數據：季度更新

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 股票：20+ 年
- 基本面數據：5+ 年

**認證要求 / Authentication Requirements:**
- 需要 API 金鑰
- 免費註冊即可獲取基本 API 金鑰

**速率限制 / Rate Limits:**
- 免費計劃：每分鐘 5 次請求，每日 500 次請求
- 付費計劃：每分鐘 75-600 次請求，無每日限制

**價格 / Pricing:**
- 免費計劃：有限制的 API 訪問
- 高級計劃：每月 $49.99 起
- 企業計劃：需聯繫銷售

**優點 / Pros:**
- 官方 API，穩定性高
- 提供豐富的技術指標
- 支持多種數據類型
- 有免費計劃可用

**缺點 / Cons:**
- 免費計劃限制較多
- 高級功能需付費
- 台股覆蓋可能不如 Yahoo Finance 完整

<a name="finnhub"></a>
### Finnhub

**API 功能與限制 / API Capabilities and Limitations:**
- 提供實時股票報價
- 提供歷史價格數據
- 提供公司財務數據
- 提供新聞和情緒分析
- 提供經濟數據和指標

**可用數據類型 / Available Data Types:**
- 實時報價和交易數據
- 歷史價格數據（分鐘、小時、日）
- 公司財務數據和估值
- 新聞和情緒分析
- 經濟數據和指標
- 分析師評級和目標價

**更新頻率 / Update Frequency:**
- 實時報價：實時
- 歷史數據：每日更新
- 財務數據：季度更新

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 股票：10+ 年
- 財務數據：5+ 年

**認證要求 / Authentication Requirements:**
- 需要 API 金鑰
- 免費註冊即可獲取基本 API 金鑰

**速率限制 / Rate Limits:**
- 免費計劃：每分鐘 60 次請求
- 付費計劃：每分鐘 150-900 次請求

**價格 / Pricing:**
- 免費計劃：有限制的 API 訪問
- 基本計劃：每月 $15
- 高級計劃：每月 $25
- 企業計劃：需聯繫銷售

**優點 / Pros:**
- 提供實時數據
- API 文檔完善
- 支持多種數據類型
- 有免費計劃可用

**缺點 / Cons:**
- 台股覆蓋可能有限
- 高級功能需付費
- 歷史數據可能不如其他來源豐富

<a name="broker-apis"></a>
### 券商 API / Broker APIs

**API 功能與限制 / API Capabilities and Limitations:**
- 提供實時報價
- 提供下單和撤單功能
- 提供帳戶和持倉資訊
- 提供歷史交易記錄

**可用數據類型 / Available Data Types:**
- 實時報價和市場深度
- 帳戶資金和持倉資訊
- 訂單狀態和成交記錄
- 歷史交易數據

**更新頻率 / Update Frequency:**
- 實時報價：實時
- 帳戶資訊：實時
- 交易記錄：實時

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 交易記錄：通常為開戶以來的所有記錄
- 市場數據：視券商而定，通常為 1-5 年

**認證要求 / Authentication Requirements:**
- 需要開立券商帳戶
- 需要 API 金鑰和密鑰
- 可能需要簽署 API 使用協議

**速率限制 / Rate Limits:**
- 視券商而定，通常為每分鐘 60-300 次請求

**價格 / Pricing:**
- 通常需支付月費或交易佣金
- 部分券商可能提供免費 API 訪問

**優點 / Pros:**
- 提供實時數據
- 支持實際交易
- 數據準確性高
- 提供完整的交易功能

**缺點 / Cons:**
- 需開立券商帳戶
- 可能需支付費用
- API 文檔可能不完善
- 不同券商的 API 差異較大

<a name="twse"></a>
### 台灣證券交易所 / Taiwan Stock Exchange (TWSE)

**API 功能與限制 / API Capabilities and Limitations:**
- 提供台股歷史價格數據
- 提供上市公司基本資料
- 提供市場統計數據
- 無官方 API，需爬取網站數據

**可用數據類型 / Available Data Types:**
- 歷史價格（開盤、最高、最低、收盤、成交量）
- 上市公司基本資料
- 市場統計數據
- 融資融券餘額

**更新頻率 / Update Frequency:**
- 歷史數據：每日更新
- 基本資料：不定期更新

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 台股：1990 年代至今

**認證要求 / Authentication Requirements:**
- 無需認證

**速率限制 / Rate Limits:**
- 無明確限制，但過度請求可能導致 IP 被封鎖
- 建議限制為每分鐘 20 次請求

**價格 / Pricing:**
- 免費

**優點 / Pros:**
- 台股數據最為完整
- 數據準確性高
- 完全免費

**缺點 / Cons:**
- 無官方 API，需自行爬取
- 數據格式可能不一致
- 爬取難度較高
- 可能有反爬蟲機制

---

<a name="financial-statement-sources"></a>
## 2. 財務報表來源 / Financial Statement Sources

<a name="mops"></a>
### 台灣公開資訊觀測站 / Taiwan Market Observation Post System (MOPS)

**數據類型與覆蓋範圍 / Data Types and Coverage:**
- 季度財務報表（資產負債表、損益表、現金流量表）
- 年度財務報表
- 月營收報告
- 股利分配資訊
- 重大訊息公告

**更新頻率 / Update Frequency:**
- 季度財務報表：季度更新
- 月營收報告：月更新
- 重大訊息：即時更新

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 財務報表：2000 年代至今
- 月營收：2000 年代至今
- 重大訊息：近 5 年

**數據獲取方式 / Data Acquisition Method:**
- 網站爬蟲
- 下載 Excel/CSV 文件

**優點 / Pros:**
- 台股財務數據最為完整
- 數據準確性高
- 完全免費
- 包含詳細的財務附註

**缺點 / Cons:**
- 無官方 API，需自行爬取
- 數據格式複雜，需處理
- 爬取難度較高
- 可能有反爬蟲機制

<a name="yahoo-finance-financial"></a>
### Yahoo Finance (財務數據 / Financial Data)

**數據類型與覆蓋範圍 / Data Types and Coverage:**
- 季度財務報表（簡化版）
- 年度財務報表（簡化版）
- 關鍵財務指標
- 分析師預測

**更新頻率 / Update Frequency:**
- 季度財務報表：季度更新
- 關鍵財務指標：不定期更新

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 財務報表：近 5 年
- 關鍵財務指標：近 5 年

**數據獲取方式 / Data Acquisition Method:**
- yfinance 庫
- 網站爬蟲

**優點 / Pros:**
- 免費使用
- 覆蓋全球市場
- 易於獲取
- 已有 yfinance 庫可直接使用

**缺點 / Cons:**
- 財務數據可能不完整
- 台股財務數據可能有限
- 非官方 API，穩定性較差
- 數據可能有延遲或錯誤

<a name="alpha-vantage-financial"></a>
### Alpha Vantage (財務數據 / Financial Data)

**數據類型與覆蓋範圍 / Data Types and Coverage:**
- 季度財務報表
- 年度財務報表
- 公司概況
- 每股收益

**更新頻率 / Update Frequency:**
- 季度財務報表：季度更新
- 年度財務報表：年度更新

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 財務報表：近 5 年

**數據獲取方式 / Data Acquisition Method:**
- 官方 API

**優點 / Pros:**
- 官方 API，穩定性高
- 數據格式統一
- 易於整合

**缺點 / Cons:**
- 免費計劃限制較多
- 台股財務數據可能有限
- 財務數據深度不如專業財務數據提供商

<a name="finnhub-financial"></a>
### Finnhub (財務數據 / Financial Data)

**數據類型與覆蓋範圍 / Data Types and Coverage:**
- 季度財務報表
- 年度財務報表
- 財務指標
- 估值指標
- 分析師評級

**更新頻率 / Update Frequency:**
- 季度財務報表：季度更新
- 分析師評級：實時更新

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 財務報表：近 5 年
- 分析師評級：近 2 年

**數據獲取方式 / Data Acquisition Method:**
- 官方 API

**優點 / Pros:**
- 官方 API，穩定性高
- 提供分析師評級
- 數據格式統一

**缺點 / Cons:**
- 免費計劃限制較多
- 台股財務數據可能有限
- 高級功能需付費

---

<a name="news-sentiment-data"></a>
## 3. 新聞情緒數據 / News Sentiment Data

<a name="perplexity"></a>
### Perplexity (via MCP)

**數據類型與覆蓋範圍 / Data Types and Coverage:**
- 新聞文章
- 研究報告摘要
- 市場分析

**更新頻率 / Update Frequency:**
- 實時更新

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 近期新聞（通常為近 1 個月）

**數據獲取方式 / Data Acquisition Method:**
- MCP 爬蟲

**優點 / Pros:**
- 覆蓋範圍廣
- 包含多種來源
- 可獲取全文
- 支持自定義查詢

**缺點 / Cons:**
- 需自行處理情緒分析
- 可能有使用限制
- 爬取可能不穩定

<a name="alpha-vantage-news"></a>
### Alpha Vantage News Sentiment

**數據類型與覆蓋範圍 / Data Types and Coverage:**
- 新聞文章
- 情緒分數
- 相關性分數

**更新頻率 / Update Frequency:**
- 實時更新

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 近期新聞（通常為近 1 週）

**數據獲取方式 / Data Acquisition Method:**
- 官方 API

**優點 / Pros:**
- 已包含情緒分析
- 官方 API，穩定性高
- 易於整合

**缺點 / Cons:**
- 免費計劃限制較多
- 台股新聞覆蓋可能有限
- 情緒分析準確性可能有限

<a name="finnhub-news"></a>
### Finnhub News Sentiment

**數據類型與覆蓋範圍 / Data Types and Coverage:**
- 新聞文章
- 情緒分數
- 公司特定新聞

**更新頻率 / Update Frequency:**
- 實時更新

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 近期新聞（通常為近 1 個月）

**數據獲取方式 / Data Acquisition Method:**
- 官方 API

**優點 / Pros:**
- 已包含情緒分析
- 官方 API，穩定性高
- 提供公司特定新聞

**缺點 / Cons:**
- 免費計劃限制較多
- 台股新聞覆蓋可能有限
- 高級功能需付費

<a name="taiwan-news"></a>
### 台灣財經新聞網站 / Taiwan Financial News Websites

**數據類型與覆蓋範圍 / Data Types and Coverage:**
- 新聞文章
- 市場分析
- 個股報導

**更新頻率 / Update Frequency:**
- 實時更新

**歷史數據覆蓋範圍 / Historical Data Coverage:**
- 視網站而定，通常為近 1-3 年

**數據獲取方式 / Data Acquisition Method:**
- 網站爬蟲

**優點 / Pros:**
- 台股新聞覆蓋最為完整
- 包含本地市場分析
- 新聞更新及時

**缺點 / Cons:**
- 需自行爬取
- 需自行處理情緒分析
- 不同網站格式差異大
- 可能有反爬蟲機制

---

<a name="data-update-frequency"></a>
## 4. 數據更新頻率與歷史覆蓋範圍 / Data Update Frequency and Historical Coverage

### 數據更新頻率比較 / Data Update Frequency Comparison

| 數據類型 / Data Type | Yahoo Finance | Alpha Vantage | Finnhub | 券商 API / Broker APIs | TWSE/MOPS |
|---------------------|---------------|---------------|---------|------------------------|-----------|
| 歷史價格 / Historical Prices | 每日 / Daily | 每日 / Daily | 每日 / Daily | 實時 / Real-time | 每日 / Daily |
| 即時報價 / Real-time Quotes | 15 分鐘延遲 / 15-min delay | 視訂閱計劃 / Depends on plan | 實時 / Real-time | 實時 / Real-time | 收盤後 / After market close |
| 財務報表 / Financial Statements | 季度 / Quarterly | 季度 / Quarterly | 季度 / Quarterly | 不適用 / N/A | 季度 / Quarterly |
| 新聞 / News | 實時 / Real-time | 實時 / Real-time | 實時 / Real-time | 不適用 / N/A | 實時 / Real-time |

### 歷史覆蓋範圍比較 / Historical Coverage Comparison

| 數據類型 / Data Type | Yahoo Finance | Alpha Vantage | Finnhub | 券商 API / Broker APIs | TWSE/MOPS |
|---------------------|---------------|---------------|---------|------------------------|-----------|
| 歷史價格 / Historical Prices | 20+ 年 / years | 20+ 年 / years | 10+ 年 / years | 1-5 年 / years | 20+ 年 / years |
| 財務報表 / Financial Statements | 5+ 年 / years | 5+ 年 / years | 5+ 年 / years | 不適用 / N/A | 20+ 年 / years |
| 新聞 / News | 近期 / Recent | 近期 / Recent | 近期 / Recent | 不適用 / N/A | 近 5 年 / 5 years |

### 結論與建議 / Conclusions and Recommendations

基於上述研究，我們建議採用以下數據來源組合：

1. **歷史價格數據 / Historical Price Data:**
   - 主要來源：Yahoo Finance（使用 yfinance 庫）
   - 備用來源：TWSE 網站爬蟲

2. **即時報價 / Real-time Quotes:**
   - 主要來源：券商 API
   - 備用來源：Finnhub（如有預算）

3. **財務報表數據 / Financial Statement Data:**
   - 主要來源：MOPS 網站爬蟲
   - 備用來源：Yahoo Finance

4. **新聞情緒數據 / News Sentiment Data:**
   - 主要來源：Perplexity（通過 MCP 爬蟲）
   - 備用來源：台灣財經新聞網站爬蟲

這種組合可以確保數據的完整性、準確性和及時性，同時控制成本。
