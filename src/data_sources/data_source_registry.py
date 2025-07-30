#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
數據源註冊表
==========

統一管理所有台股免費數據源的註冊表，包括已驗證可用和待實現的數據源。
提供統一的接口來訪問所有數據源功能。
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataSourceRegistry:
    """數據源註冊表"""
    
    def __init__(self):
        self.verified_crawler = None
        self.comprehensive_crawler = None
        self._initialize_crawlers()
    
    def _initialize_crawlers(self):
        """初始化爬蟲實例"""
        try:
            from .verified_crawler import VerifiedCrawler
            self.verified_crawler = VerifiedCrawler()
            logger.info("✅ 已驗證爬蟲初始化成功")
        except Exception as e:
            logger.error(f"❌ 已驗證爬蟲初始化失敗: {e}")
        
        try:
            from .comprehensive_crawler import ComprehensiveCrawler
            self.comprehensive_crawler = ComprehensiveCrawler()
            logger.info("✅ 綜合爬蟲初始化成功")
        except Exception as e:
            logger.error(f"❌ 綜合爬蟲初始化失敗: {e}")
    
    def get_all_data_sources(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """獲取所有數據源的完整註冊表"""
        return {
            'technical': {
                # 已驗證可用 ✅
                'twse_backtest_index': {
                    'name': '回測基準指數',
                    'source': 'TWSE OpenAPI JSON',
                    'status': 'verified',
                    'crawler': 'verified',
                    'method': 'crawl_twse_backtest_index',
                    'description': '台股回測基準指數數據'
                },
                'yahoo_adjusted_price': {
                    'name': '還原權值股價',
                    'source': 'Yahoo Finance API',
                    'status': 'verified',
                    'crawler': 'verified',
                    'method': 'crawl_yahoo_adjusted_price',
                    'description': '股票還原權值價格數據'
                },
                'twse_market_indicators': {
                    'name': '大盤市況指標',
                    'source': 'TWSE OpenAPI JSON',
                    'status': 'verified',
                    'crawler': 'verified',
                    'method': 'crawl_twse_market_indicators',
                    'description': '台股大盤即時指標數據'
                },
                'tpex_mainboard_quotes': {
                    'name': 'TPEX上櫃股票',
                    'source': 'TPEX OpenAPI JSON',
                    'status': 'verified',
                    'crawler': 'verified',
                    'method': 'crawl_tpex_mainboard_quotes',
                    'description': '上櫃股票即時報價數據'
                },
                # 待實現 🔄
                'twse_zero_share': {
                    'name': '上市櫃盤後零股成交資訊',
                    'source': 'TWSE CSV',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_zero_share',
                    'description': '零股交易成交資訊'
                },
                'tpex_cb_trading': {
                    'name': '可轉換公司債成交資訊',
                    'source': 'TPEX HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_tpex_cb_trading',
                    'description': '可轉債交易資訊'
                },
                'twse_trading_change': {
                    'name': '上市櫃變更交易',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_trading_change',
                    'description': '股票交易變更資訊'
                },
                'tpex_disposal_stocks': {
                    'name': '排除處置股',
                    'source': 'TPEX HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_tpex_disposal_stocks',
                    'description': '處置股票清單'
                },
                'twse_attention_stocks': {
                    'name': '排除注意股',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_attention_stocks',
                    'description': '注意股票清單'
                },
                'taifex_futures_daily': {
                    'name': '期貨日成交資訊',
                    'source': 'TAIFEX CSV',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_taifex_futures_daily',
                    'description': '期貨市場日成交數據'
                }
            },
            'fundamental': {
                # 已驗證可用 ✅
                'gov_company_info': {
                    'name': '企業基本資訊',
                    'source': '政府開放平台 JSON',
                    'status': 'verified',
                    'crawler': 'verified',
                    'method': 'crawl_gov_company_info',
                    'description': '企業基本資料和資本額'
                },
                'finmind_financial_data': {
                    'name': '財務指標',
                    'source': 'FinMind API JSON',
                    'status': 'verified',
                    'crawler': 'verified',
                    'method': 'crawl_finmind_financial_data',
                    'description': '公司財務報表和指標'
                },
                # 待實現 🔄
                'twse_dividend_announcement': {
                    'name': '董事會決擬議分配股利公告',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_dividend_announcement',
                    'description': '股利分配公告資訊'
                },
                'tpex_capital_reduction': {
                    'name': '上櫃減資',
                    'source': 'TPEX HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_tpex_capital_reduction',
                    'description': '上櫃公司減資資訊'
                },
                'twse_capital_reduction': {
                    'name': '上市減資',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_capital_reduction',
                    'description': '上市公司減資資訊'
                },
                'twse_business_info': {
                    'name': '企業主要經營業務',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_business_info',
                    'description': '公司主要業務範圍'
                },
                'twse_monthly_revenue': {
                    'name': '上市櫃月營收',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_monthly_revenue',
                    'description': '公司月營收數據'
                }
            },
            'chip': {
                # 已驗證可用 ✅
                'twse_broker_trading': {
                    'name': '券商分點買賣超前15大券商明細',
                    'source': 'TWSE HTML',
                    'status': 'verified',
                    'crawler': 'verified',
                    'method': 'crawl_twse_broker_trading',
                    'description': '券商買賣超明細數據'
                },
                'twse_foreign_holding': {
                    'name': '外資持股比率',
                    'source': 'TWSE HTML',
                    'status': 'verified',
                    'crawler': 'verified',
                    'method': 'crawl_twse_foreign_holding',
                    'description': '外資持股比例數據'
                },
                # 待實現 🔄
                'twse_broker_mapping': {
                    'name': '券商分點名稱對照表',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_broker_mapping',
                    'description': '券商分點代碼對照'
                },
                'taifex_institutional_trading': {
                    'name': '期貨三大法人盤後資訊',
                    'source': 'TAIFEX CSV',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_taifex_institutional_trading',
                    'description': '期貨三大法人交易數據'
                },
                'twse_margin_trading': {
                    'name': '融資融券',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_margin_trading',
                    'description': '融資融券餘額數據'
                },
                'twse_securities_lending': {
                    'name': '借券',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_securities_lending',
                    'description': '證券借貸數據'
                }
            },
            'event': {
                # 待實現 🔄
                'twse_announcements': {
                    'name': '重訊公告',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_announcements',
                    'description': '重大訊息公告'
                },
                'twse_investor_conference': {
                    'name': '法說會期程',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_investor_conference',
                    'description': '法人說明會時程'
                },
                'twse_shareholder_meeting': {
                    'name': '股東會期程',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_shareholder_meeting',
                    'description': '股東會召開時程'
                },
                'twse_treasury_stock': {
                    'name': '庫藏股',
                    'source': 'TWSE HTML',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_twse_treasury_stock',
                    'description': '庫藏股買回資訊'
                },
                'cnyes_news': {
                    'name': '台股新聞',
                    'source': 'cnyes RSS',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_cnyes_news',
                    'description': '台股相關新聞資訊'
                }
            },
            'macro': {
                # 已驗證可用 ✅
                'gov_economic_indicators': {
                    'name': '台灣景氣指標',
                    'source': '政府開放平台 JSON',
                    'status': 'verified',
                    'crawler': 'verified',
                    'method': 'crawl_gov_economic_indicators',
                    'description': '台灣總體經濟景氣指標'
                },
                'yahoo_world_indices': {
                    'name': '世界指數',
                    'source': 'Yahoo Finance API',
                    'status': 'verified',
                    'crawler': 'verified',
                    'method': 'crawl_yahoo_world_indices',
                    'description': '全球主要股市指數'
                },
                # 待實現 🔄
                'gov_manufacturing_pmi': {
                    'name': '台灣製造業採購經理人指數',
                    'source': '政府開放平台 JSON',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_gov_manufacturing_pmi',
                    'description': '製造業PMI指標'
                },
                'gov_service_pmi': {
                    'name': '台灣非製造業採購經理人指數',
                    'source': '政府開放平台 JSON',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_gov_service_pmi',
                    'description': '服務業PMI指標'
                },
                'gov_money_supply': {
                    'name': '貨幣總計數年增率',
                    'source': '政府開放平台 JSON',
                    'status': 'implemented',
                    'crawler': 'comprehensive',
                    'method': 'crawl_gov_money_supply',
                    'description': '貨幣供給成長率'
                }
            }
        }
    
    def get_verified_sources(self) -> Dict[str, List[str]]:
        """獲取已驗證可用的數據源"""
        all_sources = self.get_all_data_sources()
        verified_sources = {}
        
        for category, sources in all_sources.items():
            verified_list = []
            for source_id, source_info in sources.items():
                if source_info['status'] == 'verified':
                    verified_list.append(source_id)
            if verified_list:
                verified_sources[category] = verified_list
        
        return verified_sources
    
    def get_implemented_sources(self) -> Dict[str, List[str]]:
        """獲取已實現的數據源（包括已驗證和待測試）"""
        all_sources = self.get_all_data_sources()
        implemented_sources = {}
        
        for category, sources in all_sources.items():
            implemented_list = []
            for source_id, source_info in sources.items():
                if source_info['status'] in ['verified', 'implemented']:
                    implemented_list.append(source_id)
            if implemented_list:
                implemented_sources[category] = implemented_list
        
        return implemented_sources
    
    def crawl_data_source(self, source_id: str, category: str, **kwargs) -> pd.DataFrame:
        """爬取指定的數據源"""
        all_sources = self.get_all_data_sources()
        
        if category not in all_sources or source_id not in all_sources[category]:
            logger.error(f"未知的數據源: {category}.{source_id}")
            return pd.DataFrame()
        
        source_info = all_sources[category][source_id]
        crawler_type = source_info['crawler']
        method_name = source_info['method']
        
        try:
            # 選擇對應的爬蟲
            if crawler_type == 'verified' and self.verified_crawler:
                crawler = self.verified_crawler
            elif crawler_type == 'comprehensive' and self.comprehensive_crawler:
                crawler = self.comprehensive_crawler
            else:
                logger.error(f"爬蟲 {crawler_type} 不可用")
                return pd.DataFrame()
            
            # 獲取方法
            method = getattr(crawler, method_name, None)
            if not method:
                logger.error(f"方法 {method_name} 不存在")
                return pd.DataFrame()
            
            # 調用方法
            if method_name in ['crawl_yahoo_adjusted_price']:
                if 'symbol' in kwargs and 'start_date' in kwargs and 'end_date' in kwargs:
                    return method(kwargs['symbol'], kwargs['start_date'], kwargs['end_date'])
                else:
                    return method('2330.TW', '2025-07-20', '2025-07-25')
            elif method_name in ['crawl_gov_company_info', 'crawl_gov_economic_indicators']:
                return method(kwargs.get('api_key'))
            elif method_name == 'crawl_finmind_financial_data':
                return method(kwargs.get('symbol', '2330'))
            else:
                return method()
                
        except Exception as e:
            logger.error(f"爬取數據源 {source_id} 失敗: {e}")
            return pd.DataFrame()
    
    def get_source_statistics(self) -> Dict[str, Any]:
        """獲取數據源統計資訊"""
        all_sources = self.get_all_data_sources()
        
        stats = {
            'total_sources': 0,
            'verified_sources': 0,
            'implemented_sources': 0,
            'by_category': {},
            'by_status': {'verified': 0, 'implemented': 0}
        }
        
        for category, sources in all_sources.items():
            category_stats = {
                'total': len(sources),
                'verified': 0,
                'implemented': 0
            }
            
            for source_info in sources.values():
                stats['total_sources'] += 1
                
                if source_info['status'] == 'verified':
                    stats['verified_sources'] += 1
                    stats['by_status']['verified'] += 1
                    category_stats['verified'] += 1
                elif source_info['status'] == 'implemented':
                    stats['implemented_sources'] += 1
                    stats['by_status']['implemented'] += 1
                    category_stats['implemented'] += 1
            
            stats['by_category'][category] = category_stats
        
        return stats
