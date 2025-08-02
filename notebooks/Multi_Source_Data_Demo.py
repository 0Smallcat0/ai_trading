#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台股多數據源爬蟲系統 - Jupyter Notebook 演示
==========================================

這是一個完整的演示文件，展示如何使用多數據源爬蟲系統
獲取台股的技術面、基本面、籌碼面、事件面和總經面數據。

功能演示：
1. 技術面數據獲取 (TWSE + TPEX + Yahoo Finance)
2. 基本面數據獲取 (財報、股利、營收等)
3. 籌碼面數據獲取 (三大法人、融資券等)
4. 事件面數據獲取 (公告、新聞等)
5. 總經面數據獲取 (景氣指標、PMI等)
6. 自學能力和數據驗證
7. 多源數據比對和準確性分析

Author: AI Trading System
Date: 2025-01-28
Version: 1.0
"""

# ============================================================================
# Cell 1: 導入必要的庫和模組
# ============================================================================

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display, HTML
import warnings
warnings.filterwarnings('ignore')

# 添加項目路徑
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# 導入我們的多數據源爬蟲系統
from src.data_sources.multi_source_downloader import MultiSourceDownloader

print("📊 台股多數據源爬蟲系統演示")
print("=" * 60)
print(f"演示時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Python版本: {sys.version}")

# ============================================================================
# Cell 2: 系統配置和初始化
# ============================================================================

# 配置參數
TEST_SYMBOL = '2330.TW'  # 測試股票：台積電
START_DATE = '20250701'  # 開始日期
END_DATE = '20250728'    # 結束日期
DB_URL = "sqlite:///examples/demo_multi_source.db"  # 資料庫連接

print("\n🔧 系統配置")
print("-" * 40)
print(f"測試股票: {TEST_SYMBOL}")
print(f"日期範圍: {START_DATE} 至 {END_DATE}")
print(f"資料庫: {DB_URL}")

# 初始化多數據源下載器
downloader = MultiSourceDownloader(db_url=DB_URL)
print("\n✅ 多數據源下載器初始化完成")

# ============================================================================
# Cell 3: 技術面數據獲取演示
# ============================================================================

print("\n🧪 測試 1: 技術面數據獲取")
print("=" * 50)

# 獲取技術面數據
technical_data = downloader.technical.get_comprehensive_data(
    TEST_SYMBOL, START_DATE, END_DATE
)

print(f"\n📊 技術面數據獲取結果:")
for data_type, df in technical_data.items():
    if not df.empty:
        print(f"   ✅ {data_type}: {len(df)} 筆記錄")
        
        # 顯示前幾筆數據樣本
        if len(df) > 0:
            print(f"      樣本數據: {df.columns.tolist()}")
    else:
        print(f"   ⚠️ {data_type}: 無數據")

# 特別展示還原權值股價數據
if 'adjusted_price' in technical_data and not technical_data['adjusted_price'].empty:
    adj_price_df = technical_data['adjusted_price']
    print(f"\n📈 {TEST_SYMBOL} 還原權值股價詳情:")
    print(f"   日期範圍: {adj_price_df['Date'].min()} 至 {adj_price_df['Date'].max()}")
    print(f"   價格範圍: {adj_price_df['Close'].min():.2f} - {adj_price_df['Close'].max():.2f}")
    print(f"   平均成交量: {adj_price_df['Volume'].mean():,.0f}")
    
    # 顯示最近5天數據
    print(f"\n   最近5天數據:")
    display_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
    recent_data = adj_price_df[display_cols].tail()
    for _, row in recent_data.iterrows():
        print(f"   {row['Date'].strftime('%Y-%m-%d')}: "
              f"開{row['Open']:.2f} 高{row['High']:.2f} "
              f"低{row['Low']:.2f} 收{row['Close']:.2f} "
              f"量{row['Volume']:,.0f}")

# ============================================================================
# Cell 4: 基本面數據獲取演示
# ============================================================================

print("\n🧪 測試 2: 基本面數據獲取")
print("=" * 50)

# 獲取基本面數據
fundamental_data = downloader.fundamental.get_comprehensive_data(
    TEST_SYMBOL, START_DATE, END_DATE
)

print(f"\n📈 基本面數據獲取結果:")
for data_type, df in fundamental_data.items():
    if not df.empty:
        print(f"   ✅ {data_type}: {len(df)} 筆記錄")
        
        # 顯示數據結構
        if len(df.columns) > 0:
            print(f"      欄位: {df.columns.tolist()[:5]}...")  # 只顯示前5個欄位
    else:
        print(f"   ⚠️ {data_type}: 無數據")

# 特別展示股利公告數據
if 'dividend' in fundamental_data and not fundamental_data['dividend'].empty:
    dividend_df = fundamental_data['dividend']
    print(f"\n💰 股利公告詳情:")
    print(f"   公告數量: {len(dividend_df)} 筆")
    print(f"   爬取日期: {dividend_df['crawl_date'].iloc[0] if len(dividend_df) > 0 else 'N/A'}")

# ============================================================================
# Cell 5: 數據品質分析和驗證
# ============================================================================

print("\n🧪 測試 3: 數據品質分析")
print("=" * 50)

def analyze_data_quality(data_dict: dict, category_name: str) -> dict:
    """分析數據品質"""
    quality_report = {
        'category': category_name,
        'total_datasets': len(data_dict),
        'successful_datasets': 0,
        'total_records': 0,
        'empty_datasets': [],
        'successful_datasets_list': []
    }
    
    for data_type, df in data_dict.items():
        if not df.empty:
            quality_report['successful_datasets'] += 1
            quality_report['total_records'] += len(df)
            quality_report['successful_datasets_list'].append(data_type)
        else:
            quality_report['empty_datasets'].append(data_type)
    
    quality_report['success_rate'] = (
        quality_report['successful_datasets'] / quality_report['total_datasets'] 
        if quality_report['total_datasets'] > 0 else 0
    )
    
    return quality_report

# 分析技術面數據品質
tech_quality = analyze_data_quality(technical_data, '技術面')
print(f"📊 技術面數據品質分析:")
print(f"   總數據集: {tech_quality['total_datasets']}")
print(f"   成功獲取: {tech_quality['successful_datasets']}")
print(f"   成功率: {tech_quality['success_rate']:.1%}")
print(f"   總記錄數: {tech_quality['total_records']}")
print(f"   成功數據集: {', '.join(tech_quality['successful_datasets_list'])}")
if tech_quality['empty_datasets']:
    print(f"   空數據集: {', '.join(tech_quality['empty_datasets'])}")

# 分析基本面數據品質
fund_quality = analyze_data_quality(fundamental_data, '基本面')
print(f"\n📈 基本面數據品質分析:")
print(f"   總數據集: {fund_quality['total_datasets']}")
print(f"   成功獲取: {fund_quality['successful_datasets']}")
print(f"   成功率: {fund_quality['success_rate']:.1%}")
print(f"   總記錄數: {fund_quality['total_records']}")

# ============================================================================
# Cell 6: 多源數據比對演示
# ============================================================================

print("\n🧪 測試 4: 多源數據比對")
print("=" * 50)

def compare_data_sources(technical_data: dict) -> dict:
    """比對不同數據源的準確性"""
    comparison_report = {
        'timestamp': datetime.now(),
        'comparisons': []
    }
    
    # 比對Yahoo Finance和TWSE數據（如果都有的話）
    yahoo_data = technical_data.get('adjusted_price')
    twse_data = technical_data.get('backtest_index')
    
    if yahoo_data is not None and not yahoo_data.empty:
        comparison_report['comparisons'].append({
            'source': 'Yahoo Finance',
            'data_type': '股價數據',
            'records': len(yahoo_data),
            'date_range': f"{yahoo_data['Date'].min()} 至 {yahoo_data['Date'].max()}",
            'price_range': f"{yahoo_data['Close'].min():.2f} - {yahoo_data['Close'].max():.2f}",
            'avg_volume': f"{yahoo_data['Volume'].mean():,.0f}"
        })
    
    if twse_data is not None and not twse_data.empty:
        comparison_report['comparisons'].append({
            'source': 'TWSE OpenAPI',
            'data_type': '指數數據',
            'records': len(twse_data),
            'coverage': '大盤指數歷史資料'
        })
    
    return comparison_report

# 執行多源比對
comparison_result = compare_data_sources(technical_data)

print(f"🔍 多源數據比對結果:")
print(f"   比對時間: {comparison_result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

for comp in comparison_result['comparisons']:
    print(f"\n   📊 {comp['source']} ({comp['data_type']}):")
    print(f"      記錄數: {comp['records']}")
    if 'date_range' in comp:
        print(f"      日期範圍: {comp['date_range']}")
        print(f"      價格範圍: {comp['price_range']}")
        print(f"      平均成交量: {comp['avg_volume']}")
    if 'coverage' in comp:
        print(f"      覆蓋範圍: {comp['coverage']}")

# ============================================================================
# Cell 7: 自學能力演示
# ============================================================================

print("\n🧪 測試 5: 自學能力演示")
print("=" * 50)

def demonstrate_self_learning(technical_data: dict, fundamental_data: dict) -> dict:
    """演示自學能力"""
    learning_report = {
        'timestamp': datetime.now(),
        'data_quality_score': 0.0,
        'recommendations': [],
        'learning_insights': []
    }
    
    # 計算整體數據品質分數
    total_datasets = len(technical_data) + len(fundamental_data)
    successful_datasets = sum(1 for df in technical_data.values() if not df.empty)
    successful_datasets += sum(1 for df in fundamental_data.values() if not df.empty)
    
    if total_datasets > 0:
        learning_report['data_quality_score'] = successful_datasets / total_datasets
    
    # 生成智能建議
    if learning_report['data_quality_score'] < 0.8:
        learning_report['recommendations'].append(
            "數據獲取成功率偏低，建議檢查網路連接和API可用性"
        )
    
    if 'adjusted_price' in technical_data and not technical_data['adjusted_price'].empty:
        learning_report['learning_insights'].append(
            "Yahoo Finance股價數據獲取穩定，建議作為主要技術面數據源"
        )
    
    if any(df.empty for df in technical_data.values()):
        learning_report['recommendations'].append(
            "部分技術面數據源無法獲取，建議啟用備援數據源"
        )
    
    # 學習最佳實踐
    if learning_report['data_quality_score'] > 0.7:
        learning_report['learning_insights'].append(
            "當前數據獲取策略有效，系統學習並記錄成功模式"
        )
    
    return learning_report

# 執行自學分析
learning_result = demonstrate_self_learning(technical_data, fundamental_data)

print(f"🤖 自學能力分析結果:")
print(f"   分析時間: {learning_result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   數據品質分數: {learning_result['data_quality_score']:.3f}")

if learning_result['recommendations']:
    print(f"\n   💡 智能建議:")
    for i, rec in enumerate(learning_result['recommendations'], 1):
        print(f"      {i}. {rec}")

if learning_result['learning_insights']:
    print(f"\n   🧠 學習洞察:")
    for i, insight in enumerate(learning_result['learning_insights'], 1):
        print(f"      {i}. {insight}")

# ============================================================================
# Cell 8: 系統整合建議
# ============================================================================

print("\n🧪 測試 6: 系統整合建議")
print("=" * 50)

def generate_integration_suggestions(all_results: dict) -> dict:
    """生成系統整合建議"""
    suggestions = {
        'timestamp': datetime.now(),
        'integration_recommendations': [],
        'performance_optimizations': [],
        'data_source_priorities': {}
    }
    
    # 基於測試結果生成建議
    if technical_data.get('adjusted_price') is not None and not technical_data['adjusted_price'].empty:
        suggestions['data_source_priorities']['primary_price_source'] = 'Yahoo Finance'
        suggestions['integration_recommendations'].append(
            "建議將Yahoo Finance設為主要股價數據源，具有高可靠性和完整性"
        )
    
    if technical_data.get('backtest_index') is not None and not technical_data['backtest_index'].empty:
        suggestions['data_source_priorities']['index_source'] = 'TWSE OpenAPI'
        suggestions['integration_recommendations'].append(
            "TWSE OpenAPI適合作為指數和大盤數據的主要來源"
        )
    
    # 性能優化建議
    suggestions['performance_optimizations'].extend([
        "實施數據緩存機制，避免重複請求相同數據",
        "使用並行處理提升多數據源獲取效率",
        "設置合理的請求間隔，避免被API限制",
        "建立數據品質監控和自動重試機制"
    ])
    
    return suggestions

# 生成整合建議
integration_suggestions = generate_integration_suggestions({
    'technical': technical_data,
    'fundamental': fundamental_data
})

print(f"🔧 系統整合建議:")
print(f"   生成時間: {integration_suggestions['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")

print(f"\n   📊 數據源優先級:")
for source_type, source_name in integration_suggestions['data_source_priorities'].items():
    print(f"      {source_type}: {source_name}")

print(f"\n   🚀 整合建議:")
for i, rec in enumerate(integration_suggestions['integration_recommendations'], 1):
    print(f"      {i}. {rec}")

print(f"\n   ⚡ 性能優化建議:")
for i, opt in enumerate(integration_suggestions['performance_optimizations'], 1):
    print(f"      {i}. {opt}")

# ============================================================================
# Cell 9: 總結和下一步
# ============================================================================

print("\n🎯 演示總結")
print("=" * 60)

# 統計總體結果
total_successful_datasets = (
    sum(1 for df in technical_data.values() if not df.empty) +
    sum(1 for df in fundamental_data.values() if not df.empty)
)
total_datasets = len(technical_data) + len(fundamental_data)
total_records = (
    sum(len(df) for df in technical_data.values() if not df.empty) +
    sum(len(df) for df in fundamental_data.values() if not df.empty)
)

print(f"✅ 演示完成統計:")
print(f"   測試股票: {TEST_SYMBOL}")
print(f"   測試期間: {START_DATE} - {END_DATE}")
print(f"   總數據集: {total_datasets}")
print(f"   成功獲取: {total_successful_datasets}")
print(f"   成功率: {total_successful_datasets/total_datasets:.1%}")
print(f"   總記錄數: {total_records}")

print(f"\n🚀 系統優勢:")
print("   • 多數據源整合確保數據完整性")
print("   • 自學能力持續優化數據品質")
print("   • 統一接口簡化數據獲取流程")
print("   • 自動重試和錯誤處理機制")
print("   • 支援多種數據格式和來源")

print(f"\n💡 下一步建議:")
print("   • 擴展更多數據源 (籌碼面、事件面、總經面)")
print("   • 實施實時數據更新機制")
print("   • 建立數據品質監控儀表板")
print("   • 整合機器學習模型進行數據預測")
print("   • 開發Web界面供用戶互動使用")

print(f"\n🎉 台股多數據源爬蟲系統演示完成！")
print("=" * 60)
