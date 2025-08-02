# -*- coding: utf-8 -*-
"""數據品質管理器

此模組提供統一的數據品質檢查、清理和標準化功能，包括：
- 數據完整性檢查
- 異常值檢測和處理
- 數據一致性驗證
- 數據標準化和格式化
- 品質評分和報告

主要功能：
- 多維度數據品質評估
- 智能異常值檢測
- 自動數據清理和修復
- 品質監控和報告
- 數據標準化處理

Example:
    >>> manager = DataQualityManager()
    >>> quality_report = manager.check_data_quality(df)
    >>> cleaned_data = manager.clean_data(df)
    >>> score = manager.calculate_quality_score(df)
"""

import logging
import warnings
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# 設定日誌
logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """數據品質等級"""
    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"           # 80-89%
    FAIR = "fair"           # 70-79%
    POOR = "poor"           # 60-69%
    CRITICAL = "critical"   # <60%


@dataclass
class QualityMetrics:
    """數據品質指標"""
    completeness: float = 0.0      # 完整性
    consistency: float = 0.0       # 一致性
    accuracy: float = 0.0          # 準確性
    validity: float = 0.0          # 有效性
    timeliness: float = 0.0        # 時效性
    overall_score: float = 0.0     # 總體評分
    
    @property
    def quality_level(self) -> QualityLevel:
        """品質等級"""
        if self.overall_score >= 0.9:
            return QualityLevel.EXCELLENT
        elif self.overall_score >= 0.8:
            return QualityLevel.GOOD
        elif self.overall_score >= 0.7:
            return QualityLevel.FAIR
        elif self.overall_score >= 0.6:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL


@dataclass
class QualityIssue:
    """數據品質問題"""
    issue_type: str
    severity: str  # 'critical', 'major', 'minor'
    description: str
    affected_rows: int
    affected_columns: List[str]
    suggested_action: str


class DataQualityManager:
    """數據品質管理器
    
    提供全面的數據品質檢查、清理和標準化功能。
    
    Attributes:
        quality_rules: 品質規則配置
        cleaning_strategies: 清理策略配置
        
    Example:
        >>> manager = DataQualityManager()
        >>> report = manager.assess_data_quality(df)
        >>> cleaned_df = manager.clean_data(df)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化數據品質管理器
        
        Args:
            config: 配置參數
        """
        self.config = config or {}
        
        # 品質檢查規則
        self.quality_rules = self._initialize_quality_rules()
        
        # 清理策略
        self.cleaning_strategies = self._initialize_cleaning_strategies()
        
        # 標準化配置
        self.standardization_config = self._initialize_standardization_config()
        
        logger.info("數據品質管理器初始化完成")
    
    def _initialize_quality_rules(self) -> Dict[str, Any]:
        """初始化品質檢查規則"""
        return {
            'completeness': {
                'max_missing_ratio': 0.1,  # 最大缺失比例
                'required_columns': ['symbol', 'date', 'close']
            },
            'consistency': {
                'price_logic_check': True,  # 價格邏輯檢查
                'date_sequence_check': True,  # 日期序列檢查
                'volume_positive_check': True  # 成交量正數檢查
            },
            'accuracy': {
                'outlier_detection': True,  # 異常值檢測
                'outlier_threshold': 3.0,   # 異常值閾值（標準差倍數）
                'price_change_limit': 0.2   # 價格變動限制（20%）
            },
            'validity': {
                'data_type_check': True,    # 數據類型檢查
                'range_check': True,        # 數值範圍檢查
                'format_check': True        # 格式檢查
            },
            'timeliness': {
                'max_delay_days': 1,        # 最大延遲天數
                'check_update_frequency': True
            }
        }
    
    def _initialize_cleaning_strategies(self) -> Dict[str, Any]:
        """初始化清理策略"""
        return {
            'missing_values': {
                'forward_fill': ['close', 'volume'],  # 前向填充
                'interpolate': ['open', 'high', 'low'],  # 插值
                'drop_rows': ['symbol', 'date']  # 刪除行
            },
            'outliers': {
                'cap_values': ['close', 'volume'],  # 限制極值
                'remove_rows': [],  # 刪除行
                'replace_median': ['amount']  # 用中位數替換
            },
            'duplicates': {
                'keep': 'last',  # 保留最後一個
                'subset': ['symbol', 'date']  # 去重依據
            }
        }
    
    def _initialize_standardization_config(self) -> Dict[str, Any]:
        """初始化標準化配置"""
        return {
            'column_names': {
                'symbol': ['code', 'ts_code', 'stock_code'],
                'date': ['trade_date', 'trading_date', 'datetime'],
                'open': ['open_price'],
                'high': ['high_price'],
                'low': ['low_price'],
                'close': ['close_price'],
                'volume': ['vol', 'trade_volume'],
                'amount': ['trade_amount', 'turnover']
            },
            'data_types': {
                'symbol': 'string',
                'date': 'datetime64[ns]',
                'open': 'float64',
                'high': 'float64',
                'low': 'float64',
                'close': 'float64',
                'volume': 'int64',
                'amount': 'float64'
            },
            'date_formats': ['%Y%m%d', '%Y-%m-%d', '%Y/%m/%d']
        }
    
    def assess_data_quality(self, df: pd.DataFrame, source: str = "unknown") -> Dict[str, Any]:
        """評估數據品質
        
        Args:
            df: 數據框架
            source: 數據源名稱
            
        Returns:
            品質評估報告
        """
        if df.empty:
            return {
                'metrics': QualityMetrics(),
                'issues': [QualityIssue(
                    issue_type="empty_data",
                    severity="critical",
                    description="數據框架為空",
                    affected_rows=0,
                    affected_columns=[],
                    suggested_action="檢查數據源"
                )],
                'source': source,
                'timestamp': datetime.now()
            }
        
        # 計算各項品質指標
        completeness = self._check_completeness(df)
        consistency = self._check_consistency(df)
        accuracy = self._check_accuracy(df)
        validity = self._check_validity(df)
        timeliness = self._check_timeliness(df)
        
        # 計算總體評分
        weights = self.config.get('quality_weights', {
            'completeness': 0.25,
            'consistency': 0.25,
            'accuracy': 0.20,
            'validity': 0.20,
            'timeliness': 0.10
        })
        
        overall_score = (
            completeness * weights['completeness'] +
            consistency * weights['consistency'] +
            accuracy * weights['accuracy'] +
            validity * weights['validity'] +
            timeliness * weights['timeliness']
        )
        
        metrics = QualityMetrics(
            completeness=completeness,
            consistency=consistency,
            accuracy=accuracy,
            validity=validity,
            timeliness=timeliness,
            overall_score=overall_score
        )
        
        # 檢測品質問題
        issues = self._detect_quality_issues(df)
        
        return {
            'metrics': metrics,
            'issues': issues,
            'source': source,
            'timestamp': datetime.now(),
            'row_count': len(df),
            'column_count': len(df.columns)
        }
    
    def _check_completeness(self, df: pd.DataFrame) -> float:
        """檢查數據完整性"""
        if df.empty:
            return 0.0
        
        # 計算缺失值比例
        total_cells = df.shape[0] * df.shape[1]
        missing_cells = df.isnull().sum().sum()
        completeness = 1 - (missing_cells / total_cells)
        
        # 檢查必需欄位
        required_columns = self.quality_rules['completeness']['required_columns']
        required_completeness = 1.0
        
        for col in required_columns:
            if col in df.columns:
                col_completeness = 1 - (df[col].isnull().sum() / len(df))
                required_completeness = min(required_completeness, col_completeness)
        
        # 綜合評分
        return (completeness * 0.7 + required_completeness * 0.3)
    
    def _check_consistency(self, df: pd.DataFrame) -> float:
        """檢查數據一致性"""
        if df.empty:
            return 0.0
        
        consistency_score = 1.0
        
        # 價格邏輯檢查
        if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            invalid_ohlc = (
                (df['high'] < df['low']) |
                (df['open'] > df['high']) | (df['open'] < df['low']) |
                (df['close'] > df['high']) | (df['close'] < df['low'])
            ).sum()
            consistency_score -= (invalid_ohlc / len(df)) * 0.4
        
        # 日期序列檢查
        if 'date' in df.columns and len(df) > 1:
            df_sorted = df.sort_values('date')
            date_gaps = (df_sorted['date'].diff().dt.days > 7).sum()
            consistency_score -= (date_gaps / len(df)) * 0.3
        
        # 成交量正數檢查
        if 'volume' in df.columns:
            negative_volume = (df['volume'] < 0).sum()
            consistency_score -= (negative_volume / len(df)) * 0.3
        
        return max(0.0, consistency_score)
    
    def _check_accuracy(self, df: pd.DataFrame) -> float:
        """檢查數據準確性"""
        if df.empty:
            return 0.0
        
        accuracy_score = 1.0
        
        # 異常值檢測
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        outlier_ratio = 0.0
        
        for col in numeric_columns:
            if col in ['open', 'high', 'low', 'close', 'volume']:
                z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                outliers = (z_scores > self.quality_rules['accuracy']['outlier_threshold']).sum()
                outlier_ratio += outliers / len(df)
        
        if len(numeric_columns) > 0:
            outlier_ratio /= len(numeric_columns)
            accuracy_score -= outlier_ratio * 0.5
        
        # 價格變動檢查
        if 'close' in df.columns and len(df) > 1:
            price_changes = df['close'].pct_change().abs()
            extreme_changes = (price_changes > self.quality_rules['accuracy']['price_change_limit']).sum()
            accuracy_score -= (extreme_changes / len(df)) * 0.3
        
        return max(0.0, accuracy_score)
    
    def _check_validity(self, df: pd.DataFrame) -> float:
        """檢查數據有效性"""
        if df.empty:
            return 0.0
        
        validity_score = 1.0
        
        # 數據類型檢查
        expected_types = self.standardization_config['data_types']
        type_errors = 0
        
        for col, expected_type in expected_types.items():
            if col in df.columns:
                if expected_type == 'datetime64[ns]' and not pd.api.types.is_datetime64_any_dtype(df[col]):
                    type_errors += 1
                elif expected_type in ['float64', 'int64'] and not pd.api.types.is_numeric_dtype(df[col]):
                    type_errors += 1
        
        if len(expected_types) > 0:
            validity_score -= (type_errors / len(expected_types)) * 0.4
        
        # 數值範圍檢查
        if 'close' in df.columns:
            invalid_prices = ((df['close'] <= 0) | (df['close'] > 10000)).sum()
            validity_score -= (invalid_prices / len(df)) * 0.3
        
        if 'volume' in df.columns:
            invalid_volumes = (df['volume'] < 0).sum()
            validity_score -= (invalid_volumes / len(df)) * 0.3
        
        return max(0.0, validity_score)
    
    def _check_timeliness(self, df: pd.DataFrame) -> float:
        """檢查數據時效性"""
        if df.empty or 'date' not in df.columns:
            return 1.0  # 無法檢查時默認為滿分
        
        try:
            latest_date = df['date'].max()
            if pd.isna(latest_date):
                return 0.0
            
            # 轉換為 datetime
            if not isinstance(latest_date, pd.Timestamp):
                latest_date = pd.to_datetime(latest_date)
            
            current_date = pd.Timestamp.now()
            delay_days = (current_date - latest_date).days
            
            max_delay = self.quality_rules['timeliness']['max_delay_days']
            
            if delay_days <= max_delay:
                return 1.0
            else:
                # 延遲超過限制，按比例扣分
                return max(0.0, 1.0 - (delay_days - max_delay) / 30)
                
        except Exception as e:
            logger.warning(f"時效性檢查失敗: {e}")
            return 0.5
    
    def _detect_quality_issues(self, df: pd.DataFrame) -> List[QualityIssue]:
        """檢測品質問題"""
        issues = []
        
        # 檢測缺失值問題
        missing_data = df.isnull().sum()
        for col, missing_count in missing_data.items():
            if missing_count > 0:
                missing_ratio = missing_count / len(df)
                severity = "critical" if missing_ratio > 0.5 else "major" if missing_ratio > 0.1 else "minor"
                
                issues.append(QualityIssue(
                    issue_type="missing_values",
                    severity=severity,
                    description=f"欄位 {col} 有 {missing_count} 個缺失值 ({missing_ratio:.1%})",
                    affected_rows=missing_count,
                    affected_columns=[col],
                    suggested_action="使用插值或前向填充處理缺失值"
                ))
        
        # 檢測重複數據
        if 'symbol' in df.columns and 'date' in df.columns:
            duplicates = df.duplicated(subset=['symbol', 'date']).sum()
            if duplicates > 0:
                issues.append(QualityIssue(
                    issue_type="duplicate_data",
                    severity="major",
                    description=f"發現 {duplicates} 條重複記錄",
                    affected_rows=duplicates,
                    affected_columns=['symbol', 'date'],
                    suggested_action="刪除重複記錄，保留最新數據"
                ))
        
        # 檢測異常值
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col in ['open', 'high', 'low', 'close', 'volume']:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                outliers = ((df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 * IQR)).sum()
                
                if outliers > 0:
                    outlier_ratio = outliers / len(df)
                    severity = "major" if outlier_ratio > 0.05 else "minor"
                    
                    issues.append(QualityIssue(
                        issue_type="outliers",
                        severity=severity,
                        description=f"欄位 {col} 有 {outliers} 個異常值 ({outlier_ratio:.1%})",
                        affected_rows=outliers,
                        affected_columns=[col],
                        suggested_action="檢查異常值並考慮限制或替換"
                    ))
        
        return issues
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理數據
        
        Args:
            df: 原始數據
            
        Returns:
            清理後的數據
        """
        if df.empty:
            return df
        
        cleaned_df = df.copy()
        
        # 1. 處理重複數據
        if 'symbol' in cleaned_df.columns and 'date' in cleaned_df.columns:
            before_count = len(cleaned_df)
            cleaned_df = cleaned_df.drop_duplicates(
                subset=self.cleaning_strategies['duplicates']['subset'],
                keep=self.cleaning_strategies['duplicates']['keep']
            )
            removed_duplicates = before_count - len(cleaned_df)
            if removed_duplicates > 0:
                logger.info(f"移除了 {removed_duplicates} 條重複記錄")
        
        # 2. 處理缺失值
        cleaned_df = self._handle_missing_values(cleaned_df)
        
        # 3. 處理異常值
        cleaned_df = self._handle_outliers(cleaned_df)
        
        # 4. 數據標準化
        cleaned_df = self._standardize_data(cleaned_df)
        
        logger.info(f"數據清理完成，從 {len(df)} 行處理為 {len(cleaned_df)} 行")
        return cleaned_df
    
    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """處理缺失值"""
        strategies = self.cleaning_strategies['missing_values']
        
        # 前向填充
        for col in strategies['forward_fill']:
            if col in df.columns:
                df[col] = df[col].fillna(method='ffill')
        
        # 插值
        for col in strategies['interpolate']:
            if col in df.columns:
                df[col] = df[col].interpolate()
        
        # 刪除關鍵欄位缺失的行
        for col in strategies['drop_rows']:
            if col in df.columns:
                before_count = len(df)
                df = df.dropna(subset=[col])
                removed_count = before_count - len(df)
                if removed_count > 0:
                    logger.info(f"因 {col} 缺失移除了 {removed_count} 行")
        
        return df
    
    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """處理異常值"""
        strategies = self.cleaning_strategies['outliers']
        
        # 限制極值
        for col in strategies['cap_values']:
            if col in df.columns:
                Q1 = df[col].quantile(0.01)
                Q99 = df[col].quantile(0.99)
                df[col] = df[col].clip(lower=Q1, upper=Q99)
        
        # 用中位數替換
        for col in strategies['replace_median']:
            if col in df.columns:
                median_val = df[col].median()
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                outlier_mask = (df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 * IQR)
                df.loc[outlier_mask, col] = median_val
        
        return df
    
    def _standardize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """標準化數據"""
        # 標準化欄位名稱
        column_mapping = {}
        for standard_name, aliases in self.standardization_config['column_names'].items():
            for alias in aliases:
                if alias in df.columns:
                    column_mapping[alias] = standard_name
                    break
        
        if column_mapping:
            df = df.rename(columns=column_mapping)
            logger.debug(f"標準化欄位名稱: {column_mapping}")
        
        # 標準化數據類型
        expected_types = self.standardization_config['data_types']
        for col, expected_type in expected_types.items():
            if col in df.columns:
                try:
                    if expected_type == 'datetime64[ns]':
                        df[col] = pd.to_datetime(df[col])
                    elif expected_type == 'float64':
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    elif expected_type == 'int64':
                        df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                except Exception as e:
                    logger.warning(f"無法轉換 {col} 為 {expected_type}: {e}")
        
        return df
    
    def calculate_quality_score(self, df: pd.DataFrame) -> float:
        """計算品質評分
        
        Args:
            df: 數據框架
            
        Returns:
            品質評分 (0-1)
        """
        assessment = self.assess_data_quality(df)
        return assessment['metrics'].overall_score
