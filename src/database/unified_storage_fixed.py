#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統一數據存儲接口 - 修復版
=======================

修復SQL語法錯誤，提供穩定的數據存儲機制。
"""

import pandas as pd
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from sqlalchemy import create_engine, text
import os

logger = logging.getLogger(__name__)

class UnifiedStorageFixed:
    """統一數據存儲管理器 - 修復版"""
    
    def __init__(self, db_url: str = "sqlite:///unified_stock_database_fixed.db"):
        """初始化存儲管理器"""
        self.db_url = db_url
        self.engine = create_engine(db_url, echo=False)
        
        # 簡化的表格結構定義 - 統一使用 real_stock_data 表結構
        self.table_schemas = {
            'real_stock_data': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS real_stock_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume BIGINT,
                    source TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date, source)
                )
                ''',
                'unique_cols': ['symbol', 'date', 'source']
            },
            'stock_daily_prices': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS stock_daily_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume BIGINT,
                    adjusted_close REAL,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'date', 'data_source']
            },
            'market_indicators': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS market_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    index_name TEXT NOT NULL,
                    index_value REAL,
                    change_points REAL,
                    change_percent REAL,
                    special_note TEXT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, index_name, data_source)
                )
                ''',
                'unique_cols': ['date', 'index_name', 'data_source']
            },
            'institutional_trading': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS institutional_trading (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    foreign_buy BIGINT,
                    foreign_sell BIGINT,
                    investment_trust_buy BIGINT,
                    investment_trust_sell BIGINT,
                    dealer_buy BIGINT,
                    dealer_sell BIGINT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'date', 'data_source']
            },
            'foreign_holdings': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS foreign_holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    foreign_holding_shares BIGINT,
                    foreign_holding_ratio REAL,
                    upper_limit_ratio REAL,
                    available_shares BIGINT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'date', 'data_source']
            },
            'financial_statements': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS financial_statements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    period TEXT NOT NULL,
                    revenue BIGINT,
                    net_income BIGINT,
                    eps REAL,
                    roe REAL,
                    roa REAL,
                    debt_ratio REAL,
                    current_ratio REAL,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, period, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'period', 'data_source']
            },
            'dividend_announcements': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS dividend_announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    announcement_date DATE NOT NULL,
                    dividend_type TEXT,
                    dividend_amount REAL,
                    ex_dividend_date DATE,
                    payment_date DATE,
                    record_date DATE,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, announcement_date, dividend_type, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'announcement_date', 'dividend_type', 'data_source']
            },
            'attention_stocks': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS attention_stocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    attention_type TEXT,
                    reason TEXT,
                    start_date DATE,
                    end_date DATE,
                    status TEXT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date, attention_type, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'date', 'attention_type', 'data_source']
            },
            'zero_share_trading': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS zero_share_trading (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    trading_session TEXT,
                    price REAL,
                    volume BIGINT,
                    turnover BIGINT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date, trading_session, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'date', 'trading_session', 'data_source']
            },
            'company_info': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS company_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    company_name TEXT,
                    industry TEXT,
                    capital BIGINT,
                    listing_date DATE,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'data_source']
            },
            'economic_indicators': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS economic_indicators (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    indicator_name TEXT NOT NULL,
                    period TEXT NOT NULL,
                    value REAL,
                    unit TEXT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(indicator_name, period, data_source)
                )
                ''',
                'unique_cols': ['indicator_name', 'period', 'data_source']
            },

            # 籌碼面數據表格 (補強)
            'broker_trading_details': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS broker_trading_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    broker_id TEXT NOT NULL,
                    broker_name TEXT,
                    buy_volume BIGINT,
                    sell_volume BIGINT,
                    buy_amount BIGINT,
                    sell_amount BIGINT,
                    net_volume BIGINT,
                    net_amount BIGINT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date, broker_id, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'date', 'broker_id', 'data_source']
            },
            'margin_trading': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS margin_trading (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    margin_purchase BIGINT,
                    margin_sale BIGINT,
                    margin_redemption BIGINT,
                    margin_balance BIGINT,
                    short_sale BIGINT,
                    short_cover BIGINT,
                    short_balance BIGINT,
                    offset BIGINT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'date', 'data_source']
            },
            'securities_lending': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS securities_lending (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    lending_balance BIGINT,
                    lending_fee_rate REAL,
                    lending_utilization_rate REAL,
                    available_for_lending BIGINT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'date', 'data_source']
            },

            # 總經面數據表格 (補強)
            'world_indices': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS world_indices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    index_symbol TEXT NOT NULL,
                    index_name TEXT NOT NULL,
                    date DATE NOT NULL,
                    current_price REAL,
                    previous_close REAL,
                    change_value REAL,
                    change_percent REAL,
                    volume BIGINT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(index_symbol, date, data_source)
                )
                ''',
                'unique_cols': ['index_symbol', 'date', 'data_source']
            },
            'pmi_data': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS pmi_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pmi_type TEXT NOT NULL,
                    period TEXT NOT NULL,
                    pmi_value REAL,
                    sub_index_production REAL,
                    sub_index_new_orders REAL,
                    sub_index_employment REAL,
                    sub_index_supplier_deliveries REAL,
                    sub_index_inventories REAL,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(pmi_type, period, data_source)
                )
                ''',
                'unique_cols': ['pmi_type', 'period', 'data_source']
            },
            'money_supply_data': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS money_supply_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period TEXT NOT NULL,
                    m1a BIGINT,
                    m1b BIGINT,
                    m2 BIGINT,
                    m1a_growth_rate REAL,
                    m1b_growth_rate REAL,
                    m2_growth_rate REAL,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(period, data_source)
                )
                ''',
                'unique_cols': ['period', 'data_source']
            },

            # 基本面數據表格 (補強)
            'monthly_revenue': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS monthly_revenue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    year_month TEXT NOT NULL,
                    monthly_revenue BIGINT,
                    monthly_revenue_last_year BIGINT,
                    monthly_revenue_growth_rate REAL,
                    cumulative_revenue BIGINT,
                    cumulative_revenue_last_year BIGINT,
                    cumulative_revenue_growth_rate REAL,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, year_month, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'year_month', 'data_source']
            },
            'capital_changes': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS capital_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    announcement_date DATE NOT NULL,
                    change_type TEXT NOT NULL,
                    original_capital BIGINT,
                    new_capital BIGINT,
                    change_ratio REAL,
                    effective_date DATE,
                    reason TEXT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, announcement_date, change_type, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'announcement_date', 'change_type', 'data_source']
            },
            'business_info': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS business_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    business_scope TEXT,
                    main_products TEXT,
                    main_markets TEXT,
                    competitive_advantages TEXT,
                    update_date DATE,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'data_source']
            },

            # 事件面數據表格 (補強)
            'stock_announcements': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS stock_announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    announcement_date DATE NOT NULL,
                    announcement_type TEXT,
                    title TEXT,
                    content TEXT,
                    url TEXT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, announcement_date, title, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'announcement_date', 'title', 'data_source']
            },
            'investor_conferences': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS investor_conferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    conference_date DATE NOT NULL,
                    conference_time TEXT,
                    conference_type TEXT,
                    location TEXT,
                    contact_info TEXT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, conference_date, conference_type, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'conference_date', 'conference_type', 'data_source']
            },
            'shareholder_meetings': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS shareholder_meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    meeting_date DATE NOT NULL,
                    meeting_time TEXT,
                    meeting_type TEXT,
                    location TEXT,
                    agenda TEXT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, meeting_date, meeting_type, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'meeting_date', 'meeting_type', 'data_source']
            },
            'treasury_stock': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS treasury_stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    announcement_date DATE NOT NULL,
                    action_type TEXT NOT NULL,
                    planned_shares BIGINT,
                    planned_amount BIGINT,
                    execution_period_start DATE,
                    execution_period_end DATE,
                    purpose TEXT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, announcement_date, action_type, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'announcement_date', 'action_type', 'data_source']
            },

            # 技術面數據表格 (補強)
            'tpex_mainboard_quotes': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS tpex_mainboard_quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    date DATE NOT NULL,
                    company_name TEXT,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume BIGINT,
                    turnover BIGINT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date, data_source)
                )
                ''',
                'unique_cols': ['symbol', 'date', 'data_source']
            },
            'futures_daily_trading': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS futures_daily_trading (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_code TEXT NOT NULL,
                    date DATE NOT NULL,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    settlement_price REAL,
                    volume BIGINT,
                    open_interest BIGINT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(contract_code, date, data_source)
                )
                ''',
                'unique_cols': ['contract_code', 'date', 'data_source']
            },
            'convertible_bonds': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS convertible_bonds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bond_code TEXT NOT NULL,
                    date DATE NOT NULL,
                    bond_name TEXT,
                    close_price REAL,
                    volume BIGINT,
                    conversion_price REAL,
                    conversion_ratio REAL,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(bond_code, date, data_source)
                )
                ''',
                'unique_cols': ['bond_code', 'date', 'data_source']
            },
            'stock_news': {
                'create_sql': '''
                CREATE TABLE IF NOT EXISTS stock_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    news_id TEXT,
                    publish_date DATE NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    source TEXT,
                    url TEXT,
                    related_symbols TEXT,
                    data_source TEXT NOT NULL,
                    data_type TEXT DEFAULT 'REAL_DATA',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(news_id, data_source)
                )
                ''',
                'unique_cols': ['news_id', 'data_source']
            }
        }
        
        logger.info(f"✅ 統一存儲管理器(修復版)初始化完成: {db_url}")
    
    def create_table_if_not_exists(self, table_name: str) -> bool:
        """創建表格（如果不存在）"""
        try:
            if table_name not in self.table_schemas:
                logger.error(f"❌ 未定義的表格結構: {table_name}")
                return False
            
            create_sql = self.table_schemas[table_name]['create_sql']
            
            with self.engine.connect() as conn:
                conn.execute(text(create_sql))
                conn.commit()
            
            logger.info(f"✅ 表格創建/檢查成功: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 創建表格失敗 {table_name}: {e}")
            return False
    
    def save_to_database(self, df: pd.DataFrame, table_name: str, 
                         data_source: str, data_type: str = 'REAL_DATA',
                         max_retries: int = 3) -> Dict[str, Any]:
        """統一的數據存儲方法 - 修復版"""
        result = {
            'success': False,
            'table_name': table_name,
            'records_processed': 0,
            'records_inserted': 0,
            'records_updated': 0,
            'errors': []
        }
        
        if df.empty:
            result['errors'].append("DataFrame為空")
            return result
        
        # 創建表格（如果不存在）
        if not self.create_table_if_not_exists(table_name):
            result['errors'].append(f"無法創建表格: {table_name}")
            return result
        
        # 準備數據
        df_prepared = self._prepare_dataframe(df, data_source, data_type)
        result['records_processed'] = len(df_prepared)
        
        # 執行存儲（帶重試機制）
        for attempt in range(max_retries):
            try:
                # 使用簡化的插入操作
                inserted = self._simple_insert(df_prepared, table_name)
                
                result['success'] = True
                result['records_inserted'] = inserted
                
                logger.info(f"✅ 數據存儲成功 {table_name}: 新增{inserted}筆")
                break
                
            except Exception as e:
                error_msg = f"存儲失敗 (嘗試 {attempt + 1}/{max_retries}): {e}"
                result['errors'].append(error_msg)
                logger.warning(error_msg)
                
                if attempt == max_retries - 1:
                    logger.error(f"❌ 數據存儲最終失敗 {table_name}")
        
        return result
    
    def _prepare_dataframe(self, df: pd.DataFrame, data_source: str,
                           data_type: str) -> pd.DataFrame:
        """準備DataFrame用於存儲"""
        df_copy = df.copy()

        # 添加標準欄位
        df_copy['data_source'] = data_source
        df_copy['data_type'] = data_type
        df_copy['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df_copy['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 處理日期格式 - 修復SQL語法錯誤
        for col in df_copy.columns:
            if 'date' in col.lower():
                try:
                    # 確保日期格式為字符串
                    if df_copy[col].dtype == 'object':
                        df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce').dt.strftime('%Y-%m-%d')
                    else:
                        df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce').dt.strftime('%Y-%m-%d')
                except Exception:
                    # 如果轉換失敗，使用當前日期
                    df_copy[col] = datetime.now().strftime('%Y-%m-%d')

        # 處理數值格式
        for col in df_copy.columns:
            if any(keyword in col.lower() for keyword in ['price', 'value', 'amount', 'ratio']):
                try:
                    df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
                except Exception:
                    pass

        # 移除包含中文的欄位名稱，避免SQL語法錯誤
        chinese_columns = []
        for col in df_copy.columns:
            if any('\u4e00' <= char <= '\u9fff' for char in col):
                chinese_columns.append(col)

        if chinese_columns:
            print(f"⚠️ 移除中文欄位名稱以避免SQL錯誤: {chinese_columns}")
            df_copy = df_copy.drop(columns=chinese_columns)

        return df_copy
    
    def _simple_insert(self, df: pd.DataFrame, table_name: str) -> int:
        """簡化的插入操作，避免複雜的UPSERT"""
        try:
            # 清理DataFrame，確保沒有SQL語法問題
            df_clean = self._clean_dataframe_for_sql(df)

            # 直接使用pandas的to_sql方法
            df_clean.to_sql(table_name, self.engine, if_exists='append', index=False, method='multi')
            return len(df_clean)
        except Exception as e:
            # 如果批量插入失敗，嘗試逐行插入
            logger.warning(f"批量插入失敗，嘗試逐行插入: {e}")
            inserted_count = 0

            df_clean = self._clean_dataframe_for_sql(df)

            with self.engine.connect() as conn:
                for _, row in df_clean.iterrows():
                    try:
                        # 準備行數據字典
                        row_dict = {}
                        for col, val in row.items():
                            if pd.notna(val):
                                row_dict[col] = val

                        if not row_dict:
                            continue

                        # 構建參數化插入SQL
                        cols = list(row_dict.keys())
                        placeholders = ', '.join([f':{col}' for col in cols])

                        insert_sql = f"INSERT INTO {table_name} ({', '.join(cols)}) VALUES ({placeholders})"

                        # 使用參數化查詢
                        conn.execute(text(insert_sql), row_dict)
                        inserted_count += 1

                    except Exception as row_error:
                        logger.warning(f"跳過問題記錄: {row_error}")
                        continue

                conn.commit()

            return inserted_count

    def _clean_dataframe_for_sql(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理DataFrame以避免SQL語法錯誤"""
        df_clean = df.copy()

        # 移除包含中文的欄位名稱
        chinese_columns = []
        for col in df_clean.columns:
            if any('\u4e00' <= char <= '\u9fff' for char in col):
                chinese_columns.append(col)

        if chinese_columns:
            logger.warning(f"移除中文欄位名稱: {chinese_columns}")
            df_clean = df_clean.drop(columns=chinese_columns)

        # 確保日期時間格式正確
        for col in df_clean.columns:
            if 'date' in col.lower() or 'time' in col.lower():
                try:
                    # 轉換為字符串格式
                    df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce').dt.strftime('%Y-%m-%d')
                except Exception:
                    # 如果轉換失敗，使用當前日期
                    df_clean[col] = datetime.now().strftime('%Y-%m-%d')

        # 處理時間戳欄位
        for col in ['created_at', 'updated_at']:
            if col in df_clean.columns:
                try:
                    # 確保時間戳為字符串格式
                    df_clean[col] = df_clean[col].astype(str)
                except Exception:
                    df_clean[col] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return df_clean
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """獲取存儲統計資訊"""
        stats = {
            'total_tables': 0,
            'total_records': 0,
            'tables_info': {},
            'database_size_kb': 0
        }
        
        try:
            with self.engine.connect() as conn:
                # 獲取所有表格
                result = conn.execute(text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """))
                tables = [row[0] for row in result.fetchall()]
                
                stats['total_tables'] = len(tables)
                
                # 獲取每個表格的統計
                for table in tables:
                    try:
                        count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = count_result.scalar()
                        
                        stats['tables_info'][table] = {
                            'records': count,
                            'exists_in_schema': table in self.table_schemas
                        }
                        stats['total_records'] += count
                        
                    except Exception as e:
                        logger.warning(f"無法獲取表格 {table} 的統計: {e}")
            
            # 獲取資料庫文件大小
            db_path = self.db_url.replace('sqlite:///', '')
            if os.path.exists(db_path):
                stats['database_size_kb'] = os.path.getsize(db_path) / 1024
        
        except Exception as e:
            logger.error(f"獲取存儲統計失敗: {e}")
        
        return stats
