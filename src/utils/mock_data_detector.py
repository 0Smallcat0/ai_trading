#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模擬數據檢測工具
==============

提供工具來檢測和標記模擬數據，幫助開發者區分真實數據和模擬數據。
"""

import pandas as pd
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)

class MockDataDetector:
    """模擬數據檢測器"""
    
    def __init__(self):
        self.mock_indicators = [
            '[模擬數據]',
            'MOCK_DATA',
            '_模擬數據',
            '模擬數據',
            'mock_data',
            'simulation',
            'fake_data'
        ]
    
    def is_mock_data(self, df: pd.DataFrame) -> bool:
        """檢測DataFrame是否包含模擬數據"""
        if df.empty:
            return False
        
        # 檢查data_type欄位
        if 'data_type' in df.columns:
            if any(df['data_type'].astype(str).str.contains('MOCK_DATA', na=False)):
                return True
        
        # 檢查data_source欄位
        if 'data_source' in df.columns:
            for indicator in self.mock_indicators:
                if any(df['data_source'].astype(str).str.contains(indicator, na=False)):
                    return True
        
        # 檢查所有文字欄位
        for col in df.columns:
            if df[col].dtype == 'object':  # 文字欄位
                for indicator in self.mock_indicators:
                    if any(df[col].astype(str).str.contains(indicator, na=False)):
                        return True
        
        return False
    
    def get_mock_data_info(self, df: pd.DataFrame) -> Dict[str, Any]:
        """獲取模擬數據的詳細資訊"""
        info = {
            'is_mock': False,
            'mock_records': 0,
            'total_records': len(df),
            'mock_columns': [],
            'mock_indicators_found': []
        }
        
        if df.empty:
            return info
        
        info['is_mock'] = self.is_mock_data(df)
        
        if info['is_mock']:
            # 統計包含模擬數據標記的記錄數
            mock_mask = pd.Series([False] * len(df))
            
            for col in df.columns:
                if df[col].dtype == 'object':
                    for indicator in self.mock_indicators:
                        col_mask = df[col].astype(str).str.contains(indicator, na=False)
                        if col_mask.any():
                            mock_mask |= col_mask
                            if col not in info['mock_columns']:
                                info['mock_columns'].append(col)
                            if indicator not in info['mock_indicators_found']:
                                info['mock_indicators_found'].append(indicator)
            
            info['mock_records'] = mock_mask.sum()
        
        return info
    
    def add_mock_warning(self, df: pd.DataFrame, warning_message: str = None) -> pd.DataFrame:
        """為模擬數據添加警告標記"""
        if df.empty:
            return df
        
        df_copy = df.copy()
        
        if self.is_mock_data(df_copy):
            if warning_message is None:
                warning_message = "⚠️ 此數據包含模擬數據，請勿用於生產環境"
            
            # 添加警告欄位
            df_copy['mock_data_warning'] = warning_message
            
            # 在日誌中記錄警告
            logger.warning(f"檢測到模擬數據: {warning_message}")
        
        return df_copy
    
    def generate_mock_data_report(self, data_results: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """生成模擬數據檢測報告"""
        report = {
            'total_sources': len(data_results),
            'mock_sources': 0,
            'real_sources': 0,
            'mixed_sources': 0,
            'source_details': {},
            'summary': {
                'total_records': 0,
                'mock_records': 0,
                'real_records': 0
            }
        }
        
        for source_name, df in data_results.items():
            mock_info = self.get_mock_data_info(df)
            
            source_detail = {
                'is_mock': mock_info['is_mock'],
                'total_records': mock_info['total_records'],
                'mock_records': mock_info['mock_records'],
                'real_records': mock_info['total_records'] - mock_info['mock_records'],
                'mock_columns': mock_info['mock_columns'],
                'indicators_found': mock_info['mock_indicators_found']
            }
            
            report['source_details'][source_name] = source_detail
            report['summary']['total_records'] += source_detail['total_records']
            report['summary']['mock_records'] += source_detail['mock_records']
            report['summary']['real_records'] += source_detail['real_records']
            
            # 分類數據源
            if mock_info['mock_records'] == mock_info['total_records'] and mock_info['total_records'] > 0:
                report['mock_sources'] += 1
            elif mock_info['mock_records'] > 0:
                report['mixed_sources'] += 1
            else:
                report['real_sources'] += 1
        
        return report
    
    def print_mock_data_report(self, report: Dict[str, Any]):
        """打印模擬數據檢測報告"""
        print("\n🔍 模擬數據檢測報告")
        print("=" * 50)
        
        print(f"📊 數據源統計:")
        print(f"   總數據源: {report['total_sources']} 個")
        print(f"   純模擬數據源: {report['mock_sources']} 個")
        print(f"   純真實數據源: {report['real_sources']} 個")
        print(f"   混合數據源: {report['mixed_sources']} 個")
        
        print(f"\n📋 記錄統計:")
        print(f"   總記錄數: {report['summary']['total_records']} 筆")
        print(f"   模擬記錄數: {report['summary']['mock_records']} 筆")
        print(f"   真實記錄數: {report['summary']['real_records']} 筆")
        
        if report['summary']['total_records'] > 0:
            mock_ratio = report['summary']['mock_records'] / report['summary']['total_records']
            print(f"   模擬數據比例: {mock_ratio:.1%}")
        
        print(f"\n📝 各數據源詳情:")
        for source_name, detail in report['source_details'].items():
            status = "🔴 純模擬" if detail['mock_records'] == detail['total_records'] and detail['total_records'] > 0 else \
                    "🟡 混合" if detail['mock_records'] > 0 else \
                    "🟢 真實"
            
            print(f"   {source_name}: {status}")
            print(f"     總記錄: {detail['total_records']} 筆")
            if detail['mock_records'] > 0:
                print(f"     模擬記錄: {detail['mock_records']} 筆")
                print(f"     模擬欄位: {', '.join(map(str, detail['mock_columns']))}")
                print(f"     檢測標記: {', '.join(map(str, detail['indicators_found']))}")
        
        print(f"\n💡 建議:")
        if report['mock_sources'] > 0:
            print(f"   ⚠️ 發現 {report['mock_sources']} 個純模擬數據源，請勿用於生產環境")
        if report['mixed_sources'] > 0:
            print(f"   ⚠️ 發現 {report['mixed_sources']} 個混合數據源，請仔細檢查數據品質")
        if report['real_sources'] == report['total_sources']:
            print(f"   ✅ 所有數據源都是真實數據，可安全使用")

def detect_mock_data_in_results(data_results: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """便捷函數：檢測數據結果中的模擬數據"""
    detector = MockDataDetector()
    return detector.generate_mock_data_report(data_results)

def print_mock_data_summary(data_results: Dict[str, pd.DataFrame]):
    """便捷函數：打印模擬數據檢測摘要"""
    detector = MockDataDetector()
    report = detector.generate_mock_data_report(data_results)
    detector.print_mock_data_report(report)

def add_mock_warnings_to_results(data_results: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """便捷函數：為所有模擬數據添加警告標記"""
    detector = MockDataDetector()
    warned_results = {}
    
    for source_name, df in data_results.items():
        warned_results[source_name] = detector.add_mock_warning(df)
    
    return warned_results

# 使用範例
if __name__ == "__main__":
    # 創建測試數據
    mock_df = pd.DataFrame({
        'name': ['測試公司 [模擬數據]', '真實公司'],
        'value': [100, 200],
        'data_source': ['測試_模擬數據', '真實數據源'],
        'data_type': ['MOCK_DATA', 'REAL_DATA']
    })
    
    real_df = pd.DataFrame({
        'name': ['真實公司A', '真實公司B'],
        'value': [300, 400],
        'data_source': ['真實數據源A', '真實數據源B']
    })
    
    test_results = {
        'mock_source': mock_df,
        'real_source': real_df
    }
    
    # 檢測和報告
    print_mock_data_summary(test_results)
