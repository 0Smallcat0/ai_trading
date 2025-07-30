#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台股免費數據來源配置文件
======================

包含所有免費台股數據來源的URL、參數和配置信息。
按照技術面、基本面、籌碼面、事件面、總經面分類組織。

Author: AI Trading System
Date: 2025-01-28
Version: 1.0
"""

from typing import Dict, List, Any
from datetime import datetime

# ============================================================================
# 技術面數據來源配置
# ============================================================================

TECHNICAL_DATA_SOURCES = {
    "twse_zero_share": {
        "name": "上市櫃盤後零股成交資訊",
        "url": "https://www.twse.com.tw/exchangeReport/TWTASU",
        "method": "GET",
        "params": {
            "response": "csv",
            "date": "{date}"  # 格式: YYYYMMDD
        },
        "description": "每日零股交易數據",
        "update_frequency": "每日",
        "data_format": "CSV"
    },
    
    "twse_backtest_index": {
        "name": "回測基準指數",
        "url": "https://openapi.twse.com.tw/v1/indicesReport/MI_5MINS_HIST",
        "method": "GET",
        "params": {},
        "description": "加權指數歷史資料",
        "update_frequency": "每5分鐘",
        "data_format": "JSON"
    },
    
    "tpex_cb_trading": {
        "name": "可轉換公司債成交資訊",
        "url": "https://www.tpex.org.tw/web/regular_emerging/corporateInfo/regular_bond_trading.php",
        "method": "GET",
        "params": {},
        "description": "轉換債交易表格",
        "update_frequency": "每日",
        "data_format": "HTML"
    },
    
    "twse_trading_change": {
        "name": "上市櫃變更交易",
        "url": "https://www.twse.com.tw/zh/trading/twt85u.html",
        "method": "GET",
        "params": {},
        "description": "變更交易清單",
        "update_frequency": "即時",
        "data_format": "HTML"
    },
    
    "yahoo_adjusted_price": {
        "name": "還原權值股價",
        "url": "Yahoo Finance API",
        "method": "yfinance",
        "params": {
            "symbol": "{symbol}",
            "start": "{start_date}",
            "end": "{end_date}",
            "auto_adjust": True
        },
        "description": "調整股價歷史數據",
        "update_frequency": "每日",
        "data_format": "DataFrame"
    },
    
    "tpex_disposal_stocks": {
        "name": "排除處置股",
        "url": "https://www.tpex.org.tw/zh-tw/announce/market/disposal.html",
        "method": "GET",
        "params": {},
        "description": "處置股清單",
        "update_frequency": "即時",
        "data_format": "HTML"
    },
    
    "twse_market_indicators": {
        "name": "大盤市況指標",
        "url": "https://openapi.twse.com.tw/v1/indicesReport/MI_INDEX",
        "method": "GET",
        "params": {},
        "description": "大盤指標數據",
        "update_frequency": "即時",
        "data_format": "JSON"
    },
    
    "twse_attention_stocks": {
        "name": "排除注意股",
        "url": "https://www.twse.com.tw/zh/page/trading/attention.html",
        "method": "GET",
        "params": {},
        "description": "注意股清單",
        "update_frequency": "即時",
        "data_format": "HTML"
    },
    
    "taifex_futures": {
        "name": "期貨日成交資訊",
        "url": "https://www.taifex.com.tw/cht/3/dailyFutures",
        "method": "GET",
        "params": {},
        "description": "期貨交易數據",
        "update_frequency": "每日",
        "data_format": "CSV"
    },
    
    "twse_intraday_zero": {
        "name": "上市櫃盤中零股成交資訊",
        "url": "https://www.twse.com.tw/zh/page/trading/exchange/TWTASU_INTRADAY.html",
        "method": "GET",
        "params": {},
        "description": "盤中零股數據",
        "update_frequency": "即時",
        "data_format": "HTML"
    }
}

# ============================================================================
# 基本面數據來源配置
# ============================================================================

FUNDAMENTAL_DATA_SOURCES = {
    "twse_dividend": {
        "name": "董事會決擬議分配股利公告",
        "url": "https://www.twse.com.tw/zh/page/announcement/dividend.html",
        "method": "GET",
        "params": {},
        "description": "股利分配公告",
        "update_frequency": "即時",
        "data_format": "HTML"
    },
    
    "tpex_capital_reduction": {
        "name": "上櫃減資",
        "url": "https://www.tpex.org.tw/web/regular_emerging/corporateInfo/regular_capital.php",
        "method": "GET",
        "params": {},
        "description": "減資公告",
        "update_frequency": "即時",
        "data_format": "HTML"
    },
    
    "twse_capital_reduction": {
        "name": "上市減資",
        "url": "https://www.twse.com.tw/zh/page/announcement/capital_reduction.html",
        "method": "GET",
        "params": {},
        "description": "減資公告",
        "update_frequency": "即時",
        "data_format": "HTML"
    },
    
    "gov_company_info": {
        "name": "企業基本資訊",
        "url": "https://data.gov.tw/dataset/18419",
        "method": "GET",
        "params": {},
        "description": "政府開放平台企業資料",
        "update_frequency": "定期",
        "data_format": "JSON"
    },
    
    "twse_company_profile": {
        "name": "企業主要經營業務",
        "url": "https://www.twse.com.tw/zh/page/company/profile.html",
        "method": "GET",
        "params": {
            "symbol": "{symbol}"
        },
        "description": "公司簡介和業務",
        "update_frequency": "定期",
        "data_format": "HTML"
    },
    
    "twse_monthly_revenue": {
        "name": "上市櫃月營收",
        "url": "https://www.twse.com.tw/zh/page/announcement/monthly_revenue.html",
        "method": "GET",
        "params": {},
        "description": "月營收報告",
        "update_frequency": "每月",
        "data_format": "HTML"
    },
    
    "finmind_financial_data": {
        "name": "財務指標",
        "url": "https://finmind.github.io/",
        "method": "API",
        "params": {
            "dataset": "TaiwanStockFinancialStatements",
            "data_id": "{symbol}",
            "start_date": "{start_date}",
            "end_date": "{end_date}"
        },
        "description": "FinMind財務指標API",
        "update_frequency": "季度",
        "data_format": "JSON"
    }
}

# ============================================================================
# 籌碼面數據來源配置
# ============================================================================

CHIP_DATA_SOURCES = {
    "twse_broker_list": {
        "name": "券商分點名稱對照表",
        "url": "https://www.twse.com.tw/zh/page/broker/broker_list.html",
        "method": "GET",
        "params": {},
        "description": "券商分點清單",
        "update_frequency": "定期",
        "data_format": "HTML"
    },
    
    "twse_broker_trading": {
        "name": "券商分點買賣超前15大券商明細",
        "url": "https://www.twse.com.tw/zh/page/trading/exchange/BROKER_SITE.html",
        "method": "GET",
        "params": {},
        "description": "券商買賣超明細",
        "update_frequency": "每日",
        "data_format": "HTML"
    },
    
    "twse_foreign_holding": {
        "name": "外資持股比率",
        "url": "https://www.twse.com.tw/zh/page/fund/BFI82U.html",
        "method": "GET",
        "params": {},
        "description": "外資持股統計",
        "update_frequency": "每日",
        "data_format": "HTML"
    },
    
    "taifex_institutional": {
        "name": "期貨三大法人盤後資訊",
        "url": "https://www.taifex.com.tw/cht/3/largeTraderFutDailyReport",
        "method": "GET",
        "params": {},
        "description": "三大法人期貨部位",
        "update_frequency": "每日",
        "data_format": "CSV"
    },
    
    "twse_margin_trading": {
        "name": "融資融券",
        "url": "https://www.twse.com.tw/zh/page/trading/margin.html",
        "method": "GET",
        "params": {},
        "description": "融資券統計",
        "update_frequency": "每日",
        "data_format": "HTML"
    },
    
    "twse_securities_lending": {
        "name": "借券",
        "url": "https://www.twse.com.tw/zh/page/trading/securities_lending.html",
        "method": "GET",
        "params": {},
        "description": "借券統計",
        "update_frequency": "每日",
        "data_format": "HTML"
    }
}

# ============================================================================
# 事件面數據來源配置
# ============================================================================

EVENT_DATA_SOURCES = {
    "twse_material_news": {
        "name": "重訊公告",
        "url": "https://www.twse.com.tw/zh/page/announcement/material_news.html",
        "method": "GET",
        "params": {},
        "description": "重大訊息公告",
        "update_frequency": "即時",
        "data_format": "HTML"
    },
    
    "twse_investor_conference": {
        "name": "法說會期程",
        "url": "https://www.twse.com.tw/zh/page/announcement/investor_conference.html",
        "method": "GET",
        "params": {},
        "description": "法人說明會時程",
        "update_frequency": "即時",
        "data_format": "HTML"
    },
    
    "twse_shareholder_meeting": {
        "name": "股東會期程",
        "url": "https://www.twse.com.tw/zh/page/announcement/shareholder_meeting.html",
        "method": "GET",
        "params": {},
        "description": "股東會時程公告",
        "update_frequency": "即時",
        "data_format": "HTML"
    },
    
    "twse_treasury_stock": {
        "name": "庫藏股",
        "url": "https://www.twse.com.tw/zh/page/announcement/treasury_stock.html",
        "method": "GET",
        "params": {},
        "description": "庫藏股買回公告",
        "update_frequency": "即時",
        "data_format": "HTML"
    },
    
    "cnyes_news": {
        "name": "台股新聞",
        "url": "https://news.cnyes.com/news/cat/tw_stock_news",
        "method": "RSS",
        "params": {},
        "description": "鉅亨網台股新聞",
        "update_frequency": "即時",
        "data_format": "RSS/XML"
    }
}

# ============================================================================
# 總經面數據來源配置
# ============================================================================

MACRO_DATA_SOURCES = {
    "gov_economic_indicators": {
        "name": "台灣景氣指標",
        "url": "https://data.gov.tw/dataset/14701",
        "method": "GET",
        "params": {},
        "description": "政府開放平台景氣指標",
        "update_frequency": "每月",
        "data_format": "JSON"
    },
    
    "gov_pmi_manufacturing": {
        "name": "台灣製造業採購經理人指數",
        "url": "https://data.gov.tw/dataset/14707",
        "method": "GET",
        "params": {},
        "description": "製造業PMI指標",
        "update_frequency": "每月",
        "data_format": "JSON"
    },
    
    "gov_pmi_services": {
        "name": "台灣非製造業採購經理人指數",
        "url": "https://data.gov.tw/dataset/14706",
        "method": "GET",
        "params": {},
        "description": "服務業PMI指標",
        "update_frequency": "每月",
        "data_format": "JSON"
    },
    
    "gov_money_supply": {
        "name": "貨幣總計數年增率",
        "url": "https://data.gov.tw/dataset/14705",
        "method": "GET",
        "params": {},
        "description": "貨幣供給量統計",
        "update_frequency": "每月",
        "data_format": "JSON"
    },
    
    "yahoo_world_indices": {
        "name": "世界指數",
        "url": "https://finance.yahoo.com/world-indices",
        "method": "yfinance",
        "params": {
            "symbols": ["^TWII", "^GSPC", "^IXIC", "^DJI", "^N225"]
        },
        "description": "全球主要指數",
        "update_frequency": "即時",
        "data_format": "DataFrame"
    }
}

# ============================================================================
# 數據源優先級和備援配置
# ============================================================================

DATA_SOURCE_PRIORITIES = {
    "stock_price": ["yahoo_adjusted_price", "twse_backtest_index"],
    "market_index": ["twse_market_indicators", "yahoo_world_indices"],
    "company_fundamentals": ["finmind_financial_data", "twse_company_profile"],
    "trading_info": ["twse_zero_share", "twse_intraday_zero"],
    "news_events": ["cnyes_news", "twse_material_news"]
}

# ============================================================================
# 請求配置和限制
# ============================================================================

REQUEST_CONFIG = {
    "default_timeout": 30,
    "retry_attempts": 3,
    "retry_delay": 2.0,
    "request_interval": 2.0,  # 避免被封鎖的請求間隔
    "max_concurrent_requests": 3,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# ============================================================================
# 數據驗證規則
# ============================================================================

DATA_VALIDATION_RULES = {
    "stock_price": {
        "required_columns": ["Date", "Open", "High", "Low", "Close", "Volume"],
        "price_range": {"min": 0.01, "max": 10000},
        "volume_range": {"min": 0, "max": 1000000000}
    },
    "financial_data": {
        "required_columns": ["symbol", "date", "revenue", "profit"],
        "revenue_range": {"min": 0, "max": 1000000000000}
    },
    "news_data": {
        "required_columns": ["title", "date", "content"],
        "max_age_days": 30
    }
}

# ============================================================================
# 輔助函數
# ============================================================================

def get_all_data_sources() -> Dict[str, Dict]:
    """獲取所有數據源配置"""
    return {
        "technical": TECHNICAL_DATA_SOURCES,
        "fundamental": FUNDAMENTAL_DATA_SOURCES,
        "chip": CHIP_DATA_SOURCES,
        "event": EVENT_DATA_SOURCES,
        "macro": MACRO_DATA_SOURCES
    }

def get_data_source_by_name(source_name: str) -> Dict[str, Any]:
    """根據名稱獲取特定數據源配置"""
    all_sources = get_all_data_sources()
    
    for category, sources in all_sources.items():
        if source_name in sources:
            return sources[source_name]
    
    return {}

def get_priority_sources(data_type: str) -> List[str]:
    """獲取指定數據類型的優先級數據源列表"""
    return DATA_SOURCE_PRIORITIES.get(data_type, [])

if __name__ == "__main__":
    # 測試配置文件
    print("📊 台股免費數據來源配置")
    print("=" * 50)
    
    all_sources = get_all_data_sources()
    
    for category, sources in all_sources.items():
        print(f"\n📋 {category.upper()} ({len(sources)} 個數據源):")
        for source_name, config in sources.items():
            print(f"   • {config['name']}")
            print(f"     URL: {config['url']}")
            print(f"     更新頻率: {config['update_frequency']}")
    
    print(f"\n🎯 總計: {sum(len(sources) for sources in all_sources.values())} 個免費數據源")
    print("✅ 配置文件載入完成")
