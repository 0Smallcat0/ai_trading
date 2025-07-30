#!/usr/bin/env python3
"""
台股清單管理器
動態獲取TWSE和TPEX的完整股票清單，支援緩存和標準化
"""

import requests
import pandas as pd
import sqlite3
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time
import os

logger = logging.getLogger(__name__)

@dataclass
class StockInfo:
    """股票資訊數據類"""
    symbol: str
    name: str
    market: str  # '上市' or '上櫃'
    industry: str
    last_update: str

class TaiwanStockListManager:
    """台股清單管理器"""
    
    def __init__(self, db_path: str = 'data/enhanced_stock_database.db'):
        """
        初始化台股清單管理器
        
        Args:
            db_path: 資料庫路徑
        """
        self.db_path = db_path.replace('sqlite:///', '')
        self.cache_duration = timedelta(days=1)  # 緩存1天
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 確保資料庫目錄存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # 初始化資料庫表
        self._init_database()
        
        self.logger.info("台股清單管理器初始化完成")
    
    def _init_database(self):
        """初始化資料庫表結構"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 創建股票清單表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS stock_list (
                        symbol TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        market TEXT NOT NULL,
                        industry TEXT,
                        last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # 創建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_list_market ON stock_list(market)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_list_industry ON stock_list(industry)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_list_name ON stock_list(name)')
                
                conn.commit()
                self.logger.info("✅ 股票清單資料庫表初始化完成")
                
        except Exception as e:
            self.logger.error(f"❌ 資料庫初始化失敗: {e}")
            raise
    
    def _fetch_twse_stock_list(self) -> List[StockInfo]:
        """
        從TWSE API獲取上市股票清單
        
        Returns:
            List[StockInfo]: 上市股票清單
        """
        try:
            self.logger.info("🔄 正在獲取TWSE上市股票清單...")
            
            # TWSE股票清單API
            url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' not in data:
                raise Exception("TWSE API回應格式錯誤")
            
            stocks = []
            today = date.today().strftime('%Y-%m-%d')
            
            for row in data['data']:
                if len(row) >= 2:
                    symbol = row[0].strip()
                    name = row[1].strip()
                    
                    # 標準化股票代碼
                    if not symbol.endswith('.TW'):
                        symbol = f"{symbol}.TW"
                    
                    # 簡單的產業分類（基於股票代碼）
                    industry = self._classify_industry_by_code(symbol)
                    
                    stocks.append(StockInfo(
                        symbol=symbol,
                        name=name,
                        market='上市',
                        industry=industry,
                        last_update=today
                    ))
            
            self.logger.info(f"✅ TWSE獲取成功: {len(stocks)} 個上市股票")
            return stocks
            
        except Exception as e:
            self.logger.error(f"❌ TWSE股票清單獲取失敗: {e}")
            return []
    
    def _fetch_tpex_stock_list(self) -> List[StockInfo]:
        """
        從TPEX API獲取上櫃股票清單

        Returns:
            List[StockInfo]: 上櫃股票清單
        """
        try:
            self.logger.info("🔄 正在獲取TPEX上櫃股票清單...")

            # 嘗試多個TPEX API端點
            today = date.today()

            # 方法1: 使用股票代碼清單API
            try:
                url = "https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_wn1430_result.php?l=zh-tw&se=EW"

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Referer': 'https://www.tpex.org.tw/'
                }

                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()

                data = response.json()

                if 'aaData' in data and data['aaData']:
                    stocks = []
                    today_str = today.strftime('%Y-%m-%d')

                    for row in data['aaData']:
                        if len(row) >= 2:
                            symbol = row[0].strip()
                            name = row[1].strip()

                            # 標準化股票代碼 - 上櫃使用.TWO
                            if not symbol.endswith('.TWO'):
                                symbol = f"{symbol}.TWO"

                            # 簡單的產業分類
                            industry = self._classify_industry_by_code(symbol)

                            stocks.append(StockInfo(
                                symbol=symbol,
                                name=name,
                                market='上櫃',
                                industry=industry,
                                last_update=today_str
                            ))

                    self.logger.info(f"✅ TPEX獲取成功: {len(stocks)} 個上櫃股票")
                    return stocks

            except Exception as e1:
                self.logger.warning(f"⚠️ TPEX方法1失敗: {e1}")

            # 方法2: 使用備用API
            try:
                # 使用昨日日期（避免當日數據未更新）
                yesterday = today - timedelta(days=1)
                date_str = yesterday.strftime('%Y/%m/%d')

                url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php?l=zh-tw&d={date_str}"

                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()

                data = response.json()

                if 'aaData' in data and data['aaData']:
                    stocks = []
                    today_str = today.strftime('%Y-%m-%d')

                    for row in data['aaData']:
                        if len(row) >= 2:
                            symbol = row[0].strip()
                            name = row[1].strip()

                            # 標準化股票代碼
                            if not symbol.endswith('.TWO'):
                                symbol = f"{symbol}.TWO"

                            industry = self._classify_industry_by_code(symbol)

                            stocks.append(StockInfo(
                                symbol=symbol,
                                name=name,
                                market='上櫃',
                                industry=industry,
                                last_update=today_str
                            ))

                    self.logger.info(f"✅ TPEX獲取成功: {len(stocks)} 個上櫃股票")
                    return stocks

            except Exception as e2:
                self.logger.warning(f"⚠️ TPEX方法2失敗: {e2}")

            # 如果所有方法都失敗，返回空清單
            self.logger.warning("⚠️ 所有TPEX API方法都失敗，返回空清單")
            return []

        except Exception as e:
            self.logger.error(f"❌ TPEX股票清單獲取失敗: {e}")
            return []
    
    def _get_special_stock_mapping(self) -> Dict[str, str]:
        """
        獲取特殊股票的產業分類映射表

        Returns:
            Dict[str, str]: 股票代碼到產業分類的映射
        """
        return {
            # 知名半導體公司
            '2330': '半導體',  # 台積電
            '2454': '半導體',  # 聯發科
            '3034': '半導體',  # 聯詠
            '2379': '半導體',  # 瑞昱
            '2408': '半導體',  # 南亞科
            '3443': '半導體',  # 創意
            '3711': '半導體',  # 日月光投控

            # 知名電子公司
            '2317': '電子製造',  # 鴻海
            '2382': '電子製造',  # 廣達
            '2357': '電子製造',  # 華碩
            '2353': '電子製造',  # 宏碁
            '2412': '通信網路',  # 中華電
            '3008': '半導體',  # 大立光

            # 金融股
            '2880': '金融-銀行',  # 華南金
            '2881': '金融-銀行',  # 富邦金
            '2882': '金融-銀行',  # 國泰金
            '2883': '金融-銀行',  # 開發金
            '2884': '金融-銀行',  # 玉山金
            '2885': '金融-銀行',  # 元大金
            '2886': '金融-銀行',  # 兆豐金
            '2887': '金融-銀行',  # 台新金
            '2888': '金融-銀行',  # 新光金
            '2889': '金融-保險',  # 國票金
            '2890': '金融-其他',  # 永豐金
            '2891': '金融-銀行',  # 中信金
            '2892': '金融-銀行',  # 第一金

            # 傳統產業
            '1301': '塑膠工業',  # 台塑
            '1303': '塑膠工業',  # 南亞
            '1326': '化學工業',  # 台化
            '2002': '食品工業',  # 中鋼
            '2105': '紡織纖維',  # 正新

            # ETF
            '0050': 'ETF',  # 元大台灣50
            '0056': 'ETF',  # 元大高股息
            '006208': 'ETF',  # 富邦台50
            '00878': 'ETF',  # 國泰永續高股息
            '00881': 'ETF',  # 國泰台灣5G+
        }

    def _classify_industry_by_code(self, symbol: str) -> str:
        """
        根據股票代碼進行詳細產業分類

        Args:
            symbol: 股票代碼

        Returns:
            str: 產業分類
        """
        code = symbol.split('.')[0]

        # 首先檢查特殊股票映射表
        special_mapping = self._get_special_stock_mapping()
        if code in special_mapping:
            return special_mapping[code]

        # 處理特殊商品
        if not code.isdigit():
            if code.startswith('00'):
                return 'ETF'
            elif code.startswith('01'):
                return 'REITs'
            elif code.startswith('02'):
                return '期貨ETF'
            elif code.startswith('03'):
                return '債券ETF'
            else:
                return '其他金融商品'

        code_num = int(code)

        # 詳細的產業分類對應表
        if 1000 <= code_num <= 1099:
            return '水泥工業'
        elif 1100 <= code_num <= 1199:
            return '食品工業'
        elif 1200 <= code_num <= 1299:
            return '塑膠工業'
        elif 1300 <= code_num <= 1399:
            return '紡織纖維'
        elif 1400 <= code_num <= 1499:
            return '電機機械'
        elif 1500 <= code_num <= 1599:
            return '電器電纜'
        elif 1600 <= code_num <= 1699:
            return '化學工業'
        elif 1700 <= code_num <= 1799:
            return '生技醫療'
        elif 1800 <= code_num <= 1899:
            return '玻璃陶瓷'
        elif 1900 <= code_num <= 1999:
            return '造紙工業'

        # 2000系列 - 主要上市公司
        elif 2000 <= code_num <= 2099:
            return '食品工業'
        elif 2100 <= code_num <= 2199:
            return '塑膠工業'
        elif 2200 <= code_num <= 2299:
            return '紡織纖維'
        elif 2300 <= code_num <= 2329:
            return '半導體'  # 台積電等半導體公司
        elif 2330 <= code_num <= 2399:
            return '半導體'  # 繼續半導體分類
        elif 2400 <= code_num <= 2449:
            return '光電'  # 光電相關
        elif 2450 <= code_num <= 2499:
            return '電子零組件'
        elif 2500 <= code_num <= 2549:
            return '化學工業'
        elif 2550 <= code_num <= 2599:
            return '生技醫療'
        elif 2600 <= code_num <= 2699:
            return '玻璃陶瓷'
        elif 2700 <= code_num <= 2799:
            return '造紙工業'
        elif 2800 <= code_num <= 2849:
            return '鋼鐵工業'
        elif 2850 <= code_num <= 2899:
            return '金融-銀行'
        elif 2880 <= code_num <= 2889:
            return '金融-保險'
        elif 2890 <= code_num <= 2899:
            return '金融-其他'
        elif 2900 <= code_num <= 2999:
            return '橡膠工業'

        # 3000系列 - 科技類
        elif 3000 <= code_num <= 3099:
            return '光電'
        elif 3100 <= code_num <= 3199:
            return '半導體'
        elif 3200 <= code_num <= 3299:
            return '通信網路'
        elif 3300 <= code_num <= 3399:
            return '航運業'
        elif 3400 <= code_num <= 3449:
            return '電腦週邊'
        elif 3450 <= code_num <= 3499:
            return '觀光事業'
        elif 3500 <= code_num <= 3549:
            return '軟體'
        elif 3550 <= code_num <= 3599:
            return '貿易百貨'
        elif 3600 <= code_num <= 3699:
            return '綜合'
        elif 3700 <= code_num <= 3799:
            return '汽車工業'

        # 4000系列 - 金融類
        elif 4000 <= code_num <= 4999:
            return '金融保險'

        # 5000系列 - 存託憑證
        elif 5000 <= code_num <= 5999:
            return '存託憑證'

        # 6000系列 - 其他
        elif 6000 <= code_num <= 6099:
            return '電子商務'
        elif 6100 <= code_num <= 6199:
            return '生技醫療'
        elif 6200 <= code_num <= 6299:
            return '文創'
        elif 6300 <= code_num <= 6399:
            return '綠能'
        elif 6400 <= code_num <= 6499:
            return '環保'
        elif 6500 <= code_num <= 6599:
            return '雲端服務'
        elif 6600 <= code_num <= 6699:
            return '生技醫療'
        elif 6700 <= code_num <= 6799:
            return '物聯網'
        elif 6800 <= code_num <= 6899:
            return '其他電子'
        elif 6900 <= code_num <= 6999:
            return '新興科技'

        # 7000系列 - 新興產業
        elif 7000 <= code_num <= 7099:
            return '電動車'
        elif 7100 <= code_num <= 7199:
            return '5G通訊'
        elif 7200 <= code_num <= 7299:
            return 'AI人工智慧'
        elif 7300 <= code_num <= 7399:
            return '區塊鏈'
        elif 7400 <= code_num <= 7499:
            return '元宇宙'
        elif 7500 <= code_num <= 7999:
            return '新興科技'

        # 8000系列 - 管理股票
        elif 8000 <= code_num <= 8999:
            return '管理股票'

        # 9000系列 - 其他
        elif 9000 <= code_num <= 9199:
            return '其他製造業'
        elif 9200 <= code_num <= 9399:
            return '其他服務業'
        elif 9400 <= code_num <= 9599:
            return '其他金融業'
        elif 9600 <= code_num <= 9799:
            return '其他科技業'
        elif 9800 <= code_num <= 9999:
            return '其他'

        # 10000以上 - 特殊商品
        elif code_num >= 10000:
            return '特殊金融商品'

        else:
            # 進一步細分剩餘的未分類股票
            if 1000 <= code_num <= 9999:
                # 根據千位數進行基本分類
                thousand_digit = code_num // 1000
                if thousand_digit == 1:
                    return '傳統工業'
                elif thousand_digit == 2:
                    return '主要上市'
                elif thousand_digit == 3:
                    return '科技產業'
                elif thousand_digit == 4:
                    return '金融服務'
                elif thousand_digit == 5:
                    return '國際投資'
                elif thousand_digit == 6:
                    return '新興產業'
                elif thousand_digit == 7:
                    return '未來科技'
                elif thousand_digit == 8:
                    return '特殊股票'
                elif thousand_digit == 9:
                    return '其他類別'

            return '未分類'
    
    def _save_stocks_to_database(self, stocks: List[StockInfo]):
        """
        保存股票清單到資料庫
        
        Args:
            stocks: 股票清單
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 使用UPSERT語法更新或插入
                for stock in stocks:
                    cursor.execute('''
                        INSERT OR REPLACE INTO stock_list 
                        (symbol, name, market, industry, last_update)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (stock.symbol, stock.name, stock.market, stock.industry, stock.last_update))
                
                conn.commit()
                self.logger.info(f"✅ 已保存 {len(stocks)} 個股票到資料庫")
                
        except Exception as e:
            self.logger.error(f"❌ 保存股票清單失敗: {e}")
            raise
    
    def update_stock_list(self, force_update: bool = False) -> Dict[str, int]:
        """
        更新股票清單
        
        Args:
            force_update: 是否強制更新（忽略緩存）
            
        Returns:
            Dict[str, int]: 更新結果統計
        """
        try:
            # 檢查是否需要更新
            if not force_update and self._is_cache_valid():
                self.logger.info("📋 股票清單緩存仍有效，跳過更新")
                return self.get_stock_list_summary()
            
            self.logger.info("🚀 開始更新台股清單...")
            
            # 獲取上市股票
            twse_stocks = self._fetch_twse_stock_list()
            time.sleep(2)  # 避免請求過於頻繁
            
            # 獲取上櫃股票
            tpex_stocks = self._fetch_tpex_stock_list()
            
            # 合併股票清單
            all_stocks = twse_stocks + tpex_stocks
            
            if all_stocks:
                # 保存到資料庫
                self._save_stocks_to_database(all_stocks)
                
                result = {
                    'total_stocks': len(all_stocks),
                    'twse_stocks': len(twse_stocks),
                    'tpex_stocks': len(tpex_stocks),
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                self.logger.info(f"✅ 股票清單更新完成: 總計 {len(all_stocks)} 個股票")
                return result
            else:
                raise Exception("未能獲取任何股票數據")
                
        except Exception as e:
            self.logger.error(f"❌ 股票清單更新失敗: {e}")
            raise
    
    def _is_cache_valid(self) -> bool:
        """檢查緩存是否有效"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(last_update) FROM stock_list")
                result = cursor.fetchone()
                
                if result and result[0]:
                    last_update = datetime.strptime(result[0], '%Y-%m-%d')
                    return datetime.now().date() - last_update.date() < self.cache_duration
                
                return False
                
        except Exception:
            return False
    
    def get_all_stocks(self) -> List[StockInfo]:
        """
        獲取所有股票清單
        
        Returns:
            List[StockInfo]: 股票清單
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT symbol, name, market, industry, last_update 
                    FROM stock_list 
                    ORDER BY symbol
                ''')
                
                stocks = []
                for row in cursor.fetchall():
                    stocks.append(StockInfo(
                        symbol=row[0],
                        name=row[1],
                        market=row[2],
                        industry=row[3] or '未分類',
                        last_update=row[4]
                    ))
                
                return stocks
                
        except Exception as e:
            self.logger.error(f"❌ 獲取股票清單失敗: {e}")
            return []
    
    def get_stock_list_summary(self) -> Dict[str, int]:
        """
        獲取股票清單摘要統計
        
        Returns:
            Dict[str, int]: 統計資訊
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 總股票數
                cursor.execute("SELECT COUNT(*) FROM stock_list")
                total = cursor.fetchone()[0]
                
                # 上市股票數
                cursor.execute("SELECT COUNT(*) FROM stock_list WHERE market = '上市'")
                twse = cursor.fetchone()[0]
                
                # 上櫃股票數
                cursor.execute("SELECT COUNT(*) FROM stock_list WHERE market = '上櫃'")
                tpex = cursor.fetchone()[0]
                
                # 最後更新時間
                cursor.execute("SELECT MAX(last_update) FROM stock_list")
                last_update = cursor.fetchone()[0]
                
                return {
                    'total_stocks': total,
                    'twse_stocks': twse,
                    'tpex_stocks': tpex,
                    'last_update': last_update or 'N/A'
                }
                
        except Exception as e:
            self.logger.error(f"❌ 獲取股票清單摘要失敗: {e}")
            return {
                'total_stocks': 0,
                'twse_stocks': 0,
                'tpex_stocks': 0,
                'last_update': 'N/A'
            }

def main():
    """測試函數"""
    logging.basicConfig(level=logging.INFO)
    
    manager = TaiwanStockListManager()
    
    # 更新股票清單
    result = manager.update_stock_list(force_update=True)
    print(f"更新結果: {result}")
    
    # 獲取摘要
    summary = manager.get_stock_list_summary()
    print(f"股票清單摘要: {summary}")

if __name__ == "__main__":
    main()
