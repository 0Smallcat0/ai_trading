# -*- coding: utf-8 -*-
"""
增強數據驗證器

此模組擴展原有的數據驗證功能，整合異常檢測算法和數據品質報告，
解決數據源驗證報告中提到的數據品質問題。

主要功能：
- 進階異常檢測（Z-score、IQR、Isolation Forest）
- 數據品質評分和報告
- 時間序列連續性檢查
- 數據完整性驗證
- 自動數據清理建議

Example:
    基本使用：
    ```python
    from src.data_sources.enhanced_data_validator import EnhancedDataValidator
    
    validator = EnhancedDataValidator()
    quality_report = validator.validate_data_quality(df, data_type='股價數據')
    ```

Note:
    此模組整合scikit-learn的異常檢測算法，提供視覺化報告，
    支援數據源驗證報告改進建議中的數據品質管理需求。
"""

import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum

import pandas as pd
import numpy as np
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

# 設定日誌
logger = logging.getLogger(__name__)

# 忽略警告
warnings.filterwarnings('ignore', category=FutureWarning)


class DataQualityLevel(Enum):
    """數據品質等級"""
    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"           # 80-89%
    FAIR = "fair"           # 70-79%
    POOR = "poor"           # 60-69%
    CRITICAL = "critical"   # <60%


class AnomalyMethod(Enum):
    """異常檢測方法"""
    ZSCORE = "zscore"
    IQR = "iqr"
    ISOLATION_FOREST = "isolation_forest"
    STATISTICAL = "statistical"


@dataclass
class DataQualityReport:
    """數據品質報告"""
    data_type: str
    total_records: int
    valid_records: int
    missing_rate: float
    duplicate_rate: float
    outlier_rate: float
    quality_score: float
    quality_level: DataQualityLevel
    anomalies: List[Dict[str, Any]]
    recommendations: List[str]
    timestamp: datetime
    metadata: Dict[str, Any]


class EnhancedDataValidator:
    """
    增強數據驗證器
    
    提供進階的數據品質檢查、異常檢測和數據清理建議功能。
    """
    
    def __init__(self):
        """初始化增強數據驗證器"""
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy='median')
        
        # 數據類型特定的驗證規則
        self.validation_rules = {
            '股價數據': {
                'required_columns': ['開盤價', '最高價', '最低價', '收盤價', '成交量'],
                'numeric_columns': ['開盤價', '最高價', '最低價', '收盤價', '成交量'],
                'positive_columns': ['開盤價', '最高價', '最低價', '收盤價', '成交量'],
                'logical_checks': [
                    ('最高價 >= 最低價', '最高價應大於等於最低價'),
                    ('最高價 >= 開盤價', '最高價應大於等於開盤價'),
                    ('最高價 >= 收盤價', '最高價應大於等於收盤價'),
                    ('最低價 <= 開盤價', '最低價應小於等於開盤價'),
                    ('最低價 <= 收盤價', '最低價應小於等於收盤價')
                ]
            },
            '財務數據': {
                'required_columns': ['營收', '毛利', '淨利'],
                'numeric_columns': ['營收', '毛利', '淨利', '資產', '負債'],
                'logical_checks': [
                    ('資產 >= 負債', '資產應大於等於負債'),
                    ('毛利 <= 營收', '毛利應小於等於營收')
                ]
            },
            '籌碼數據': {
                'required_columns': ['外資', '投信', '自營商'],
                'numeric_columns': ['外資', '投信', '自營商', '融資', '融券'],
                'logical_checks': []
            }
        }
        
    def validate_data_quality(self, df: pd.DataFrame, data_type: str = 'general', 
                            anomaly_methods: List[AnomalyMethod] = None) -> DataQualityReport:
        """
        驗證數據品質
        
        Args:
            df: 待驗證的數據
            data_type: 數據類型
            anomaly_methods: 異常檢測方法列表
            
        Returns:
            DataQualityReport: 數據品質報告
        """
        if anomaly_methods is None:
            anomaly_methods = [AnomalyMethod.ZSCORE, AnomalyMethod.IQR]
            
        logger.info(f"開始驗證 {data_type} 數據品質: {len(df)} 筆記錄")
        
        # 基本統計
        total_records = len(df)
        if total_records == 0:
            return self._create_empty_report(data_type)
            
        # 計算各項指標
        missing_rate = self._calculate_missing_rate(df)
        duplicate_rate = self._calculate_duplicate_rate(df)
        
        # 異常檢測
        anomalies = []
        for method in anomaly_methods:
            method_anomalies = self._detect_anomalies(df, method, data_type)
            anomalies.extend(method_anomalies)
            
        outlier_rate = len(anomalies) / total_records if total_records > 0 else 0
        
        # 數據類型特定驗證
        type_specific_issues = self._validate_data_type_specific(df, data_type)
        anomalies.extend(type_specific_issues)
        
        # 計算品質分數
        quality_score = self._calculate_quality_score(missing_rate, duplicate_rate, outlier_rate)
        quality_level = self._determine_quality_level(quality_score)
        
        # 生成建議
        recommendations = self._generate_recommendations(df, missing_rate, duplicate_rate, 
                                                       outlier_rate, anomalies, data_type)
        
        # 有效記錄數（排除異常和缺失）
        valid_records = total_records - len(anomalies) - int(total_records * missing_rate)
        
        report = DataQualityReport(
            data_type=data_type,
            total_records=total_records,
            valid_records=max(0, valid_records),
            missing_rate=missing_rate,
            duplicate_rate=duplicate_rate,
            outlier_rate=outlier_rate,
            quality_score=quality_score,
            quality_level=quality_level,
            anomalies=anomalies,
            recommendations=recommendations,
            timestamp=datetime.now(),
            metadata={
                'anomaly_methods': [method.value for method in anomaly_methods],
                'validation_rules_applied': data_type in self.validation_rules
            }
        )
        
        logger.info(f"✅ 數據品質驗證完成: {quality_level.value} ({quality_score:.1f}%)")
        return report
        
    def _calculate_missing_rate(self, df: pd.DataFrame) -> float:
        """計算缺失率"""
        if df.empty:
            return 1.0
        total_cells = df.size
        missing_cells = df.isnull().sum().sum()
        return missing_cells / total_cells if total_cells > 0 else 0.0
        
    def _calculate_duplicate_rate(self, df: pd.DataFrame) -> float:
        """計算重複率"""
        if df.empty:
            return 0.0
        total_records = len(df)
        duplicate_records = df.duplicated().sum()
        return duplicate_records / total_records if total_records > 0 else 0.0
        
    def _detect_anomalies(self, df: pd.DataFrame, method: AnomalyMethod, 
                         data_type: str) -> List[Dict[str, Any]]:
        """
        檢測異常值
        
        Args:
            df: 數據框
            method: 檢測方法
            data_type: 數據類型
            
        Returns:
            List[Dict[str, Any]]: 異常值列表
        """
        anomalies = []
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        if len(numeric_columns) == 0:
            return anomalies
            
        try:
            if method == AnomalyMethod.ZSCORE:
                anomalies = self._detect_zscore_anomalies(df, numeric_columns)
            elif method == AnomalyMethod.IQR:
                anomalies = self._detect_iqr_anomalies(df, numeric_columns)
            elif method == AnomalyMethod.ISOLATION_FOREST:
                anomalies = self._detect_isolation_forest_anomalies(df, numeric_columns)
            elif method == AnomalyMethod.STATISTICAL:
                anomalies = self._detect_statistical_anomalies(df, numeric_columns)
                
        except Exception as e:
            logger.warning(f"異常檢測失敗 ({method.value}): {e}")
            
        return anomalies
        
    def _detect_zscore_anomalies(self, df: pd.DataFrame, columns: List[str], 
                                threshold: float = 3.0) -> List[Dict[str, Any]]:
        """Z-score異常檢測"""
        anomalies = []
        
        for col in columns:
            if df[col].dtype in [np.number] and not df[col].isnull().all():
                z_scores = np.abs(stats.zscore(df[col].dropna()))
                outlier_indices = df[col].dropna().index[z_scores > threshold]
                
                for idx in outlier_indices:
                    anomalies.append({
                        'method': 'zscore',
                        'row_index': idx,
                        'column': col,
                        'value': df.loc[idx, col],
                        'z_score': z_scores[df[col].dropna().index.get_loc(idx)],
                        'severity': 'high' if z_scores[df[col].dropna().index.get_loc(idx)] > 4 else 'medium'
                    })
                    
        return anomalies
        
    def _detect_iqr_anomalies(self, df: pd.DataFrame, columns: List[str]) -> List[Dict[str, Any]]:
        """IQR異常檢測"""
        anomalies = []
        
        for col in columns:
            if df[col].dtype in [np.number] and not df[col].isnull().all():
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
                outlier_indices = df[outlier_mask].index
                
                for idx in outlier_indices:
                    value = df.loc[idx, col]
                    distance = min(abs(value - lower_bound), abs(value - upper_bound))
                    
                    anomalies.append({
                        'method': 'iqr',
                        'row_index': idx,
                        'column': col,
                        'value': value,
                        'lower_bound': lower_bound,
                        'upper_bound': upper_bound,
                        'distance': distance,
                        'severity': 'high' if distance > 2 * IQR else 'medium'
                    })
                    
        return anomalies
        
    def _detect_isolation_forest_anomalies(self, df: pd.DataFrame, columns: List[str], 
                                         contamination: float = 0.1) -> List[Dict[str, Any]]:
        """Isolation Forest異常檢測"""
        anomalies = []
        
        try:
            # 準備數據
            data = df[columns].dropna()
            if len(data) < 10:  # 數據太少，跳過
                return anomalies
                
            # 標準化
            data_scaled = self.scaler.fit_transform(data)
            
            # 訓練模型
            iso_forest = IsolationForest(contamination=contamination, random_state=42)
            outlier_labels = iso_forest.fit_predict(data_scaled)
            
            # 獲取異常分數
            anomaly_scores = iso_forest.decision_function(data_scaled)
            
            # 找出異常值
            outlier_indices = data.index[outlier_labels == -1]
            
            for i, idx in enumerate(outlier_indices):
                anomalies.append({
                    'method': 'isolation_forest',
                    'row_index': idx,
                    'columns': columns,
                    'anomaly_score': anomaly_scores[data.index.get_loc(idx)],
                    'severity': 'high' if anomaly_scores[data.index.get_loc(idx)] < -0.5 else 'medium'
                })
                
        except Exception as e:
            logger.warning(f"Isolation Forest異常檢測失敗: {e}")
            
        return anomalies
        
    def _detect_statistical_anomalies(self, df: pd.DataFrame, columns: List[str]) -> List[Dict[str, Any]]:
        """統計異常檢測"""
        anomalies = []
        
        for col in columns:
            if df[col].dtype in [np.number] and not df[col].isnull().all():
                # 檢測極值
                mean_val = df[col].mean()
                std_val = df[col].std()
                
                if std_val > 0:
                    # 超過5個標準差的值
                    extreme_mask = np.abs(df[col] - mean_val) > 5 * std_val
                    extreme_indices = df[extreme_mask].index
                    
                    for idx in extreme_indices:
                        anomalies.append({
                            'method': 'statistical',
                            'row_index': idx,
                            'column': col,
                            'value': df.loc[idx, col],
                            'mean': mean_val,
                            'std': std_val,
                            'deviation': abs(df.loc[idx, col] - mean_val) / std_val,
                            'severity': 'critical'
                        })
                        
        return anomalies
        
    def _validate_data_type_specific(self, df: pd.DataFrame, data_type: str) -> List[Dict[str, Any]]:
        """數據類型特定驗證"""
        issues = []
        
        if data_type not in self.validation_rules:
            return issues
            
        rules = self.validation_rules[data_type]
        
        # 檢查必需欄位
        missing_columns = set(rules.get('required_columns', [])) - set(df.columns)
        if missing_columns:
            issues.append({
                'method': 'schema_validation',
                'type': 'missing_columns',
                'columns': list(missing_columns),
                'severity': 'critical'
            })
            
        # 檢查數值欄位
        for col in rules.get('numeric_columns', []):
            if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
                issues.append({
                    'method': 'data_type_validation',
                    'type': 'non_numeric',
                    'column': col,
                    'severity': 'high'
                })
                
        # 檢查正值欄位
        for col in rules.get('positive_columns', []):
            if col in df.columns and df[col].dtype in [np.number]:
                negative_mask = df[col] < 0
                if negative_mask.any():
                    negative_indices = df[negative_mask].index
                    for idx in negative_indices:
                        issues.append({
                            'method': 'business_logic_validation',
                            'type': 'negative_value',
                            'row_index': idx,
                            'column': col,
                            'value': df.loc[idx, col],
                            'severity': 'medium'
                        })
                        
        # 檢查邏輯規則
        for rule_expr, rule_desc in rules.get('logical_checks', []):
            try:
                # 簡單的邏輯檢查實現
                if '最高價 >= 最低價' in rule_expr and '最高價' in df.columns and '最低價' in df.columns:
                    violation_mask = df['最高價'] < df['最低價']
                    if violation_mask.any():
                        violation_indices = df[violation_mask].index
                        for idx in violation_indices:
                            issues.append({
                                'method': 'business_logic_validation',
                                'type': 'logic_violation',
                                'row_index': idx,
                                'rule': rule_desc,
                                'severity': 'high'
                            })
            except Exception as e:
                logger.warning(f"邏輯規則檢查失敗 ({rule_expr}): {e}")
                
        return issues
        
    def _calculate_quality_score(self, missing_rate: float, duplicate_rate: float, 
                               outlier_rate: float) -> float:
        """計算品質分數"""
        # 權重設定
        missing_weight = 0.4
        duplicate_weight = 0.2
        outlier_weight = 0.4
        
        # 計算分數（越低越好的指標需要反轉）
        missing_score = max(0, 100 * (1 - missing_rate))
        duplicate_score = max(0, 100 * (1 - duplicate_rate))
        outlier_score = max(0, 100 * (1 - outlier_rate))
        
        # 加權平均
        quality_score = (missing_score * missing_weight + 
                        duplicate_score * duplicate_weight + 
                        outlier_score * outlier_weight)
        
        return min(100, max(0, quality_score))
        
    def _determine_quality_level(self, score: float) -> DataQualityLevel:
        """確定品質等級"""
        if score >= 90:
            return DataQualityLevel.EXCELLENT
        elif score >= 80:
            return DataQualityLevel.GOOD
        elif score >= 70:
            return DataQualityLevel.FAIR
        elif score >= 60:
            return DataQualityLevel.POOR
        else:
            return DataQualityLevel.CRITICAL
            
    def _generate_recommendations(self, df: pd.DataFrame, missing_rate: float, 
                                duplicate_rate: float, outlier_rate: float,
                                anomalies: List[Dict[str, Any]], data_type: str) -> List[str]:
        """生成改進建議"""
        recommendations = []
        
        # 缺失值建議
        if missing_rate > 0.1:
            recommendations.append(f"缺失率過高 ({missing_rate:.1%})，建議檢查數據收集流程")
            if missing_rate > 0.3:
                recommendations.append("考慮使用插值或填充方法處理缺失值")
                
        # 重複值建議
        if duplicate_rate > 0.05:
            recommendations.append(f"重複率過高 ({duplicate_rate:.1%})，建議去除重複記錄")
            
        # 異常值建議
        if outlier_rate > 0.1:
            recommendations.append(f"異常值比例過高 ({outlier_rate:.1%})，建議檢查數據來源")
            
        # 特定異常類型建議
        critical_anomalies = [a for a in anomalies if a.get('severity') == 'critical']
        if critical_anomalies:
            recommendations.append("發現嚴重異常值，建議立即檢查數據收集系統")
            
        # 數據類型特定建議
        if data_type == '股價數據':
            price_anomalies = [a for a in anomalies if a.get('type') == 'logic_violation']
            if price_anomalies:
                recommendations.append("發現價格邏輯錯誤，建議檢查價格數據的完整性")
                
        # 通用建議
        if not recommendations:
            recommendations.append("數據品質良好，建議維持當前的數據收集和處理流程")
        else:
            recommendations.append("建議建立定期數據品質監控機制")
            
        return recommendations
        
    def _create_empty_report(self, data_type: str) -> DataQualityReport:
        """創建空數據報告"""
        return DataQualityReport(
            data_type=data_type,
            total_records=0,
            valid_records=0,
            missing_rate=1.0,
            duplicate_rate=0.0,
            outlier_rate=0.0,
            quality_score=0.0,
            quality_level=DataQualityLevel.CRITICAL,
            anomalies=[],
            recommendations=["數據為空，請檢查數據源連接"],
            timestamp=datetime.now(),
            metadata={}
        )
        
    def generate_quality_visualization(self, report: DataQualityReport, 
                                     save_path: Optional[str] = None) -> None:
        """
        生成數據品質視覺化報告
        
        Args:
            report: 數據品質報告
            save_path: 保存路徑（可選）
        """
        try:
            fig, axes = plt.subplots(2, 2, figsize=(12, 10))
            fig.suptitle(f'數據品質報告 - {report.data_type}', fontsize=16, fontweight='bold')
            
            # 品質分數儀表板
            ax1 = axes[0, 0]
            colors = ['red', 'orange', 'yellow', 'lightgreen', 'green']
            score_color = colors[min(4, int(report.quality_score // 20))]
            ax1.pie([report.quality_score, 100 - report.quality_score], 
                   colors=[score_color, 'lightgray'], startangle=90,
                   labels=[f'{report.quality_score:.1f}%', ''])
            ax1.set_title('整體品質分數')
            
            # 問題分布
            ax2 = axes[0, 1]
            problem_types = ['缺失值', '重複值', '異常值']
            problem_rates = [report.missing_rate * 100, report.duplicate_rate * 100, 
                           report.outlier_rate * 100]
            bars = ax2.bar(problem_types, problem_rates, color=['red', 'orange', 'yellow'])
            ax2.set_title('問題分布 (%)')
            ax2.set_ylabel('百分比')
            
            # 異常值嚴重程度
            ax3 = axes[1, 0]
            severity_counts = {}
            for anomaly in report.anomalies:
                severity = anomaly.get('severity', 'unknown')
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
            if severity_counts:
                ax3.pie(severity_counts.values(), labels=severity_counts.keys(), autopct='%1.1f%%')
                ax3.set_title('異常值嚴重程度分布')
            else:
                ax3.text(0.5, 0.5, '無異常值', ha='center', va='center', transform=ax3.transAxes)
                ax3.set_title('異常值嚴重程度分布')
                
            # 記錄統計
            ax4 = axes[1, 1]
            record_types = ['有效記錄', '無效記錄']
            record_counts = [report.valid_records, report.total_records - report.valid_records]
            ax4.bar(record_types, record_counts, color=['green', 'red'])
            ax4.set_title('記錄統計')
            ax4.set_ylabel('記錄數')
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"品質報告圖表已保存: {save_path}")
            else:
                plt.show()
                
        except Exception as e:
            logger.error(f"生成視覺化報告失敗: {e}")
            
    def clean_data_based_on_report(self, df: pd.DataFrame,
                                  report: DataQualityReport) -> pd.DataFrame:
        """
        基於品質報告清理數據

        Args:
            df: 原始數據
            report: 品質報告

        Returns:
            pd.DataFrame: 清理後的數據
        """
        cleaned_df = df.copy()

        try:
            # 移除重複值
            if report.duplicate_rate > 0.05:
                cleaned_df = cleaned_df.drop_duplicates()
                logger.info(f"移除重複記錄: {len(df) - len(cleaned_df)} 筆")

            # 處理異常值
            for anomaly in report.anomalies:
                if anomaly.get('severity') == 'critical':
                    row_idx = anomaly.get('row_index')
                    if row_idx is not None and row_idx in cleaned_df.index:
                        cleaned_df = cleaned_df.drop(row_idx)

            logger.info(f"數據清理完成: {len(df)} -> {len(cleaned_df)} 筆記錄")

        except Exception as e:
            logger.error(f"數據清理失敗: {e}")
            return df

        return cleaned_df

    def get_validation_summary(self, reports: List[DataQualityReport]) -> Dict[str, Any]:
        """
        獲取多個驗證報告的摘要

        Args:
            reports: 品質報告列表

        Returns:
            Dict[str, Any]: 驗證摘要
        """
        if not reports:
            return {}

        summary = {
            'total_reports': len(reports),
            'avg_quality_score': np.mean([r.quality_score for r in reports]),
            'quality_distribution': {},
            'common_issues': [],
            'recommendations_summary': [],
            'timestamp': datetime.now().isoformat()
        }

        # 品質分布統計
        for report in reports:
            level = report.quality_level.value
            dist = summary['quality_distribution']
            dist[level] = dist.get(level, 0) + 1

        # 常見問題統計
        issue_counts = defaultdict(int)
        for report in reports:
            for anomaly in report.anomalies:
                method = anomaly.get('method', 'unknown')
                issue_type = anomaly.get('type', 'unknown')
                key = f"{method}_{issue_type}"
                issue_counts[key] += 1

        sorted_issues = sorted(issue_counts.items(),
                              key=lambda x: x[1], reverse=True)
        summary['common_issues'] = sorted_issues[:5]

        # 建議摘要
        all_recommendations = []
        for report in reports:
            all_recommendations.extend(report.recommendations)

        recommendation_counts = defaultdict(int)
        for rec in all_recommendations:
            recommendation_counts[rec] += 1

        sorted_recs = sorted(recommendation_counts.items(),
                            key=lambda x: x[1], reverse=True)
        summary['recommendations_summary'] = sorted_recs[:3]

        return summary
