#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統一數據存儲接口
==============

提供統一的數據存儲機制，確保所有爬蟲數據都能自動存儲到資料庫。
支援自動表格創建、數據驗證、UPSERT操作和錯誤處理。
"""

import pandas as pd
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Float, DateTime, BigInteger, Date
from sqlalchemy.dialects.sqlite import insert
import os

logger = logging.getLogger(__name__)

class UnifiedStorage:
    """統一數據存儲管理器"""
    
    def __init__(self, db_url: str = "sqlite:///unified_stock_database.db"):
        """初始化存儲管理器
        
        Args:
            db_url: 資料庫連接URL
        """
        self.db_url = db_url
        self.engine = create_engine(db_url, echo=False)
        self.metadata = MetaData()
        
        # 標準化表格結構定義
        self.standard_schemas = self._define_standard_schemas()
        
        logger.info(f"✅ 統一存儲管理器初始化完成: {db_url}")
    
    def _define_standard_schemas(self) -> Dict[str, Dict[str, Any]]:
        """定義標準化表格結構"""
        return {
            # 技術面數據表格
            'stock_daily_prices': {
                'columns': {
                    'id': {'type': Integer, 'primary_key': True},
                    'symbol': {'type': String(20), 'nullable': False},
                    'date': {'type': Date, 'nullable': False},
                    'open_price': {'type': Float, 'nullable': True},
                    'high_price': {'type': Float, 'nullable': True},
                    'low_price': {'type': Float, 'nullable': True},
                    'close_price': {'type': Float, 'nullable': True},
                    'volume': {'type': BigInteger, 'nullable': True},
                    'adjusted_close': {'type': Float, 'nullable': True},
                    'data_source': {'type': String(50), 'nullable': False},
                    'data_type': {'type': String(20), 'default': 'REAL_DATA'},
                    'created_at': {'type': DateTime, 'default': datetime.now},
                    'updated_at': {'type': DateTime, 'default': datetime.now}
                },
                'unique_constraints': [('symbol', 'date', 'data_source')]
            },
            'market_indicators': {
                'columns': {
                    'id': {'type': Integer, 'primary_key': True},
                    'date': {'type': Date, 'nullable': False},
                    'index_name': {'type': String(100), 'nullable': False},
                    'index_value': {'type': Float, 'nullable': True},
                    'change_points': {'type': Float, 'nullable': True},
                    'change_percent': {'type': Float, 'nullable': True},
                    'special_note': {'type': String(200), 'nullable': True},
                    'data_source': {'type': String(50), 'nullable': False},
                    'data_type': {'type': String(20), 'default': 'REAL_DATA'},
                    'created_at': {'type': DateTime, 'default': datetime.now},
                    'updated_at': {'type': DateTime, 'default': datetime.now}
                },
                'unique_constraints': [('date', 'index_name', 'data_source')]
            },
            'zero_share_trading': {
                'columns': {
                    'id': {'type': Integer, 'primary_key': True},
                    'symbol': {'type': String(20), 'nullable': False},
                    'date': {'type': Date, 'nullable': False},
                    'trading_session': {'type': String(20), 'nullable': True},  # 盤中/盤後
                    'price': {'type': Float, 'nullable': True},
                    'volume': {'type': BigInteger, 'nullable': True},
                    'data_source': {'type': String(50), 'nullable': False},
                    'data_type': {'type': String(20), 'default': 'REAL_DATA'},
                    'created_at': {'type': DateTime, 'default': datetime.now},
                    'updated_at': {'type': DateTime, 'default': datetime.now}
                },
                'unique_constraints': [('symbol', 'date', 'trading_session', 'data_source')]
            },
            
            # 基本面數據表格
            'financial_statements': {
                'columns': {
                    'id': {'type': Integer, 'primary_key': True},
                    'symbol': {'type': String(20), 'nullable': False},
                    'period': {'type': String(20), 'nullable': False},  # 2025Q1, 2025
                    'revenue': {'type': BigInteger, 'nullable': True},
                    'net_income': {'type': BigInteger, 'nullable': True},
                    'eps': {'type': Float, 'nullable': True},
                    'roe': {'type': Float, 'nullable': True},
                    'debt_ratio': {'type': Float, 'nullable': True},
                    'data_source': {'type': String(50), 'nullable': False},
                    'data_type': {'type': String(20), 'default': 'REAL_DATA'},
                    'created_at': {'type': DateTime, 'default': datetime.now},
                    'updated_at': {'type': DateTime, 'default': datetime.now}
                },
                'unique_constraints': [('symbol', 'period', 'data_source')]
            },
            'company_info': {
                'columns': {
                    'id': {'type': Integer, 'primary_key': True},
                    'symbol': {'type': String(20), 'nullable': False},
                    'company_name': {'type': String(200), 'nullable': True},
                    'industry': {'type': String(100), 'nullable': True},
                    'capital': {'type': BigInteger, 'nullable': True},
                    'listing_date': {'type': Date, 'nullable': True},
                    'data_source': {'type': String(50), 'nullable': False},
                    'data_type': {'type': String(20), 'default': 'REAL_DATA'},
                    'created_at': {'type': DateTime, 'default': datetime.now},
                    'updated_at': {'type': DateTime, 'default': datetime.now}
                },
                'unique_constraints': [('symbol', 'data_source')]
            },
            'dividend_announcements': {
                'columns': {
                    'id': {'type': Integer, 'primary_key': True},
                    'symbol': {'type': String(20), 'nullable': False},
                    'announcement_date': {'type': Date, 'nullable': False},
                    'dividend_type': {'type': String(50), 'nullable': True},  # 現金股利/股票股利
                    'dividend_amount': {'type': Float, 'nullable': True},
                    'ex_dividend_date': {'type': Date, 'nullable': True},
                    'payment_date': {'type': Date, 'nullable': True},
                    'data_source': {'type': String(50), 'nullable': False},
                    'data_type': {'type': String(20), 'default': 'REAL_DATA'},
                    'created_at': {'type': DateTime, 'default': datetime.now},
                    'updated_at': {'type': DateTime, 'default': datetime.now}
                },
                'unique_constraints': [('symbol', 'announcement_date', 'dividend_type', 'data_source')]
            },
            
            # 籌碼面數據表格
            'institutional_trading': {
                'columns': {
                    'id': {'type': Integer, 'primary_key': True},
                    'symbol': {'type': String(20), 'nullable': False},
                    'date': {'type': Date, 'nullable': False},
                    'foreign_buy': {'type': BigInteger, 'nullable': True},
                    'foreign_sell': {'type': BigInteger, 'nullable': True},
                    'investment_trust_buy': {'type': BigInteger, 'nullable': True},
                    'investment_trust_sell': {'type': BigInteger, 'nullable': True},
                    'dealer_buy': {'type': BigInteger, 'nullable': True},
                    'dealer_sell': {'type': BigInteger, 'nullable': True},
                    'data_source': {'type': String(50), 'nullable': False},
                    'data_type': {'type': String(20), 'default': 'REAL_DATA'},
                    'created_at': {'type': DateTime, 'default': datetime.now},
                    'updated_at': {'type': DateTime, 'default': datetime.now}
                },
                'unique_constraints': [('symbol', 'date', 'data_source')]
            },
            'foreign_holdings': {
                'columns': {
                    'id': {'type': Integer, 'primary_key': True},
                    'symbol': {'type': String(20), 'nullable': False},
                    'date': {'type': Date, 'nullable': False},
                    'foreign_holding_shares': {'type': BigInteger, 'nullable': True},
                    'foreign_holding_ratio': {'type': Float, 'nullable': True},
                    'upper_limit_ratio': {'type': Float, 'nullable': True},
                    'data_source': {'type': String(50), 'nullable': False},
                    'data_type': {'type': String(20), 'default': 'REAL_DATA'},
                    'created_at': {'type': DateTime, 'default': datetime.now},
                    'updated_at': {'type': DateTime, 'default': datetime.now}
                },
                'unique_constraints': [('symbol', 'date', 'data_source')]
            },
            
            # 事件面數據表格
            'stock_announcements': {
                'columns': {
                    'id': {'type': Integer, 'primary_key': True},
                    'symbol': {'type': String(20), 'nullable': False},
                    'announcement_date': {'type': Date, 'nullable': False},
                    'announcement_type': {'type': String(100), 'nullable': True},
                    'title': {'type': String(500), 'nullable': True},
                    'content': {'type': String(2000), 'nullable': True},
                    'data_source': {'type': String(50), 'nullable': False},
                    'data_type': {'type': String(20), 'default': 'REAL_DATA'},
                    'created_at': {'type': DateTime, 'default': datetime.now},
                    'updated_at': {'type': DateTime, 'default': datetime.now}
                },
                'unique_constraints': [('symbol', 'announcement_date', 'title', 'data_source')]
            },
            'attention_stocks': {
                'columns': {
                    'id': {'type': Integer, 'primary_key': True},
                    'symbol': {'type': String(20), 'nullable': False},
                    'date': {'type': Date, 'nullable': False},
                    'attention_type': {'type': String(50), 'nullable': True},  # 注意/處置
                    'reason': {'type': String(200), 'nullable': True},
                    'start_date': {'type': Date, 'nullable': True},
                    'end_date': {'type': Date, 'nullable': True},
                    'data_source': {'type': String(50), 'nullable': False},
                    'data_type': {'type': String(20), 'default': 'REAL_DATA'},
                    'created_at': {'type': DateTime, 'default': datetime.now},
                    'updated_at': {'type': DateTime, 'default': datetime.now}
                },
                'unique_constraints': [('symbol', 'date', 'attention_type', 'data_source')]
            },
            
            # 總經面數據表格
            'economic_indicators': {
                'columns': {
                    'id': {'type': Integer, 'primary_key': True},
                    'indicator_name': {'type': String(100), 'nullable': False},
                    'period': {'type': String(20), 'nullable': False},  # 2025-01
                    'value': {'type': Float, 'nullable': True},
                    'unit': {'type': String(50), 'nullable': True},
                    'data_source': {'type': String(50), 'nullable': False},
                    'data_type': {'type': String(20), 'default': 'REAL_DATA'},
                    'created_at': {'type': DateTime, 'default': datetime.now},
                    'updated_at': {'type': DateTime, 'default': datetime.now}
                },
                'unique_constraints': [('indicator_name', 'period', 'data_source')]
            },
            'world_indices': {
                'columns': {
                    'id': {'type': Integer, 'primary_key': True},
                    'index_symbol': {'type': String(20), 'nullable': False},
                    'index_name': {'type': String(100), 'nullable': False},
                    'date': {'type': Date, 'nullable': False},
                    'current_price': {'type': Float, 'nullable': True},
                    'previous_close': {'type': Float, 'nullable': True},
                    'change': {'type': Float, 'nullable': True},
                    'change_percent': {'type': Float, 'nullable': True},
                    'data_source': {'type': String(50), 'nullable': False},
                    'data_type': {'type': String(20), 'default': 'REAL_DATA'},
                    'created_at': {'type': DateTime, 'default': datetime.now},
                    'updated_at': {'type': DateTime, 'default': datetime.now}
                },
                'unique_constraints': [('index_symbol', 'date', 'data_source')]
            }
        }
    
    def create_table_if_not_exists(self, table_name: str) -> bool:
        """創建表格（如果不存在）
        
        Args:
            table_name: 表格名稱
            
        Returns:
            bool: 創建是否成功
        """
        try:
            if table_name not in self.standard_schemas:
                logger.error(f"❌ 未定義的表格結構: {table_name}")
                return False
            
            schema = self.standard_schemas[table_name]
            
            # 檢查表格是否已存在
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='{table_name}'
                """))
                
                if result.fetchone():
                    logger.info(f"✅ 表格已存在: {table_name}")
                    return True
            
            # 創建表格
            columns = []
            for col_name, col_config in schema['columns'].items():
                col_type = col_config['type']
                
                # 處理特殊屬性
                if col_config.get('primary_key'):
                    columns.append(Column(col_name, col_type, primary_key=True))
                elif col_config.get('nullable') is False:
                    columns.append(Column(col_name, col_type, nullable=False))
                else:
                    columns.append(Column(col_name, col_type))
            
            table = Table(table_name, self.metadata, *columns)
            table.create(self.engine, checkfirst=True)
            
            logger.info(f"✅ 表格創建成功: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 創建表格失敗 {table_name}: {e}")
            return False

    def save_to_database(self, df: pd.DataFrame, table_name: str,
                         data_source: str, data_type: str = 'REAL_DATA',
                         max_retries: int = 3) -> Dict[str, Any]:
        """統一的數據存儲方法

        Args:
            df: 要存儲的DataFrame
            table_name: 目標表格名稱
            data_source: 數據來源標識
            data_type: 數據類型 (REAL_DATA/MOCK_DATA)
            max_retries: 最大重試次數

        Returns:
            Dict: 存儲結果統計
        """
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
                # 使用UPSERT操作
                inserted, updated = self._upsert_data(df_prepared, table_name)

                result['success'] = True
                result['records_inserted'] = inserted
                result['records_updated'] = updated

                logger.info(f"✅ 數據存儲成功 {table_name}: "
                           f"新增{inserted}筆, 更新{updated}筆")
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
        df_copy['created_at'] = datetime.now()
        df_copy['updated_at'] = datetime.now()

        # 處理日期格式
        for col in df_copy.columns:
            if 'date' in col.lower() and df_copy[col].dtype == 'object':
                try:
                    df_copy[col] = pd.to_datetime(df_copy[col]).dt.date
                except Exception:
                    pass

        # 處理數值格式
        for col in df_copy.columns:
            if any(keyword in col.lower() for keyword in ['price', 'value', 'amount', 'ratio']):
                try:
                    df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
                except Exception:
                    pass

        return df_copy

    def _upsert_data(self, df: pd.DataFrame, table_name: str) -> tuple:
        """執行UPSERT操作

        Returns:
            tuple: (inserted_count, updated_count)
        """
        inserted_count = 0
        updated_count = 0

        # 獲取唯一約束欄位
        unique_cols = self.standard_schemas[table_name].get('unique_constraints', [])

        if not unique_cols:
            # 沒有唯一約束，直接插入
            df.to_sql(table_name, self.engine, if_exists='append', index=False)
            inserted_count = len(df)
        else:
            # 有唯一約束，執行UPSERT
            with self.engine.connect() as conn:
                for _, row in df.iterrows():
                    # 構建WHERE條件
                    where_conditions = []
                    for unique_col_group in unique_cols:
                        group_conditions = []
                        for col in unique_col_group:
                            if col in row and pd.notna(row[col]):
                                if isinstance(row[col], str):
                                    group_conditions.append(f"{col} = '{row[col]}'")
                                else:
                                    group_conditions.append(f"{col} = {row[col]}")
                        if group_conditions:
                            where_conditions.append(" AND ".join(group_conditions))

                    if where_conditions:
                        where_clause = " OR ".join([f"({cond})" for cond in where_conditions])

                        # 檢查記錄是否存在
                        check_sql = f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}"
                        result = conn.execute(text(check_sql))
                        exists = result.scalar() > 0

                        if exists:
                            # 更新現有記錄
                            set_clauses = []
                            for col, val in row.items():
                                if col != 'id' and pd.notna(val):
                                    if isinstance(val, str):
                                        set_clauses.append(f"{col} = '{val}'")
                                    else:
                                        set_clauses.append(f"{col} = {val}")

                            if set_clauses:
                                update_sql = f"""
                                    UPDATE {table_name}
                                    SET {', '.join(set_clauses)}
                                    WHERE {where_clause}
                                """
                                conn.execute(text(update_sql))
                                updated_count += 1
                        else:
                            # 插入新記錄
                            cols = [col for col in row.index if pd.notna(row[col])]
                            vals = [f"'{row[col]}'" if isinstance(row[col], str) else str(row[col])
                                    for col in cols]

                            insert_sql = f"""
                                INSERT INTO {table_name} ({', '.join(cols)})
                                VALUES ({', '.join(vals)})
                            """
                            conn.execute(text(insert_sql))
                            inserted_count += 1

                conn.commit()

        return inserted_count, updated_count

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
                            'exists_in_schema': table in self.standard_schemas
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
