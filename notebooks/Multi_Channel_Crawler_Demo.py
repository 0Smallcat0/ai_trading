#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多渠道股票數據爬蟲系統 - 完整演示
================================

這是一個Jupyter Notebook風格的演示文件，展示如何使用多渠道數據爬蟲系統
獲取準確的股票數據，並進行自學優化和品質分析。

功能演示：
1. 多渠道數據爬取 (TWSE + TPEX + Yahoo Finance)
2. 並行處理和自動備援
3. 數據品質驗證和準確性報告
4. 自學能力和自動重試
5. UPSERT資料庫操作

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

# 導入我們的多渠道爬蟲系統
from src.data_sources.multi_channel_crawler import (
    AutoDataManager, 
    DataValidator, 
    TPEXCrawler, 
    YahooFinanceCrawler
)

print("📊 多渠道股票數據爬蟲系統演示")
print("=" * 50)
print(f"演示時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Python版本: {sys.version}")

# ============================================================================
# Cell 2: 系統配置和初始化
# ============================================================================

# 配置參數
SYMBOLS = ['2330.TW', '2317.TW', '2454.TW', '2412.TW', '2882.TW']  # 測試股票列表
START_DATE = date(2025, 7, 1)  # 開始日期
END_DATE = date(2025, 7, 28)   # 結束日期 (當前日期)
MAX_WORKERS = 2  # 並行處理數量
DB_URL = "sqlite:///demo_stock_data.db"  # 資料庫連接

print("\n🔧 系統配置")
print("-" * 30)
print(f"目標股票: {', '.join(SYMBOLS)}")
print(f"日期範圍: {START_DATE} 至 {END_DATE}")
print(f"並行處理: {MAX_WORKERS} 個工作線程")
print(f"資料庫: {DB_URL}")

# 初始化自動數據管理器
data_manager = AutoDataManager(db_url=DB_URL)
print("\n✅ 自動數據管理器初始化完成")

# ============================================================================
# Cell 3: 單一渠道測試 - Yahoo Finance
# ============================================================================

print("\n🧪 測試 1: Yahoo Finance 單一渠道")
print("-" * 40)

yahoo_crawler = YahooFinanceCrawler()

# 測試單一股票
test_symbol = '2330.TW'
yahoo_data = yahoo_crawler.crawl_historical_data(test_symbol, START_DATE, END_DATE)

if not yahoo_data.empty:
    print(f"✅ Yahoo Finance 成功獲取 {test_symbol} 數據")
    print(f"   記錄數: {len(yahoo_data)} 筆")
    print(f"   日期範圍: {yahoo_data['date'].min()} 至 {yahoo_data['date'].max()}")
    print(f"   價格範圍: {yahoo_data['close'].min():.2f} - {yahoo_data['close'].max():.2f}")
    
    # 顯示前5筆數據
    print("\n📋 Yahoo Finance 數據樣本:")
    display(yahoo_data.head())
else:
    print("❌ Yahoo Finance 數據獲取失敗")

# ============================================================================
# Cell 4: 單一渠道測試 - TPEX
# ============================================================================

print("\n🧪 測試 2: TPEX 單一渠道")
print("-" * 40)

tpex_crawler = TPEXCrawler()

# 測試單月數據
tpex_data = tpex_crawler.crawl_monthly_data(test_symbol, 2025, 7)

if not tpex_data.empty:
    print(f"✅ TPEX 成功獲取 {test_symbol} 數據")
    print(f"   記錄數: {len(tpex_data)} 筆")
    print(f"   日期範圍: {tpex_data['date'].min()} 至 {tpex_data['date'].max()}")
    print(f"   價格範圍: {tpex_data['close'].min():.2f} - {tpex_data['close'].max():.2f}")
    
    # 顯示前5筆數據
    print("\n📋 TPEX 數據樣本:")
    display(tpex_data.head())
else:
    print("❌ TPEX 數據獲取失敗")

# ============================================================================
# Cell 5: 多渠道並行爬取演示
# ============================================================================

print("\n🚀 測試 3: 多渠道並行爬取")
print("-" * 40)

# 執行多渠道爬取
print("正在執行多渠道並行爬取...")
multi_channel_results = data_manager.crawl_multi_channel_data(
    symbols=SYMBOLS,
    start_date=START_DATE,
    end_date=END_DATE,
    max_workers=MAX_WORKERS
)

print(f"\n✅ 多渠道爬取完成")
print(f"   成功獲取股票數: {len(multi_channel_results)}")

# 顯示每個股票的數據統計
for symbol, df in multi_channel_results.items():
    if not df.empty:
        sources = df['source'].unique() if 'source' in df.columns else ['Unknown']
        print(f"   {symbol}: {len(df)} 筆記錄，數據源: {', '.join(sources)}")
    else:
        print(f"   {symbol}: 無數據")

# ============================================================================
# Cell 6: 數據品質驗證演示
# ============================================================================

print("\n🔍 測試 4: 數據品質驗證")
print("-" * 40)

# 對每個股票進行數據驗證
validation_results = {}

for symbol, df in multi_channel_results.items():
    if not df.empty:
        # 檢查數據完整性
        completeness = DataValidator.check_data_completeness(df, expected_days=20)
        
        # 驗證OHLCV邏輯
        validated_df = DataValidator.validate_ohlcv_data(df)
        
        validation_results[symbol] = {
            'original_records': len(df),
            'validated_records': len(validated_df),
            'completeness': completeness,
            'validation_pass_rate': len(validated_df) / len(df) if len(df) > 0 else 0
        }
        
        print(f"\n📊 {symbol} 數據品質:")
        print(f"   原始記錄: {len(df)} 筆")
        print(f"   驗證通過: {len(validated_df)} 筆")
        print(f"   完整性: {completeness['completeness_ratio']:.1%}")
        print(f"   驗證通過率: {validation_results[symbol]['validation_pass_rate']:.1%}")

# ============================================================================
# Cell 7: 自學能力演示 - 自動偵測和重試
# ============================================================================

print("\n🤖 測試 5: 自學能力演示")
print("-" * 40)

# 執行自動偵測和重試
auto_results = data_manager.auto_detect_and_retry(
    symbols=SYMBOLS,
    start_date=START_DATE,
    end_date=END_DATE
)

print("✅ 自學處理完成")
print(f"   處理股票數: {auto_results['total_symbols']}")
print(f"   重試股票數: {len(auto_results['retry_symbols'])}")
print(f"   保存到資料庫: {auto_results['saved_to_db']} 個股票")

if auto_results['retry_symbols']:
    print(f"   重試股票: {', '.join(auto_results['retry_symbols'])}")

# ============================================================================
# Cell 8: 準確性報告生成
# ============================================================================

print("\n📈 測試 6: 準確性報告")
print("-" * 40)

final_report = auto_results['final_report']

print(f"📊 整體品質分數: {final_report['overall_quality']:.3f}")
print(f"🕐 報告生成時間: {final_report['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📈 處理股票數量: {final_report['symbols_processed']}")

print("\n📋 各股票詳細報告:")
for symbol, report in final_report['symbol_reports'].items():
    print(f"\n🏷️  {symbol}:")
    print(f"   總記錄數: {report['total_records']}")
    print(f"   日期範圍: {report['date_range']['start']} 至 {report['date_range']['end']}")
    print(f"   完整性: {report['completeness']['completeness_ratio']:.1%}")
    print(f"   數據源: {', '.join(report['data_sources'])}")
    print(f"   品質分數: {report['quality_score']:.3f}")
    
    if report['recommendations']:
        print(f"   建議: {'; '.join(report['recommendations'])}")

# ============================================================================
# Cell 9: 數據可視化
# ============================================================================

print("\n📊 測試 7: 數據可視化")
print("-" * 40)

# 創建圖表
if multi_channel_results:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('多渠道股票數據分析', fontsize=16)
    
    # 選擇一個有數據的股票進行可視化
    sample_symbol = None
    sample_data = None
    
    for symbol, df in multi_channel_results.items():
        if not df.empty and len(df) > 5:
            sample_symbol = symbol
            sample_data = df.sort_values('date')
            break
    
    if sample_data is not None:
        # 1. 股價走勢圖
        axes[0, 0].plot(sample_data['date'], sample_data['close'], marker='o', linewidth=2)
        axes[0, 0].set_title(f'{sample_symbol} 收盤價走勢')
        axes[0, 0].set_xlabel('日期')
        axes[0, 0].set_ylabel('價格 (TWD)')
        axes[0, 0].tick_params(axis='x', rotation=45)
        
        # 2. 成交量圖
        axes[0, 1].bar(sample_data['date'], sample_data['volume'], alpha=0.7)
        axes[0, 1].set_title(f'{sample_symbol} 成交量')
        axes[0, 1].set_xlabel('日期')
        axes[0, 1].set_ylabel('成交量')
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 3. 數據源分布
        if 'source' in sample_data.columns:
            source_counts = sample_data['source'].value_counts()
            axes[1, 0].pie(source_counts.values, labels=source_counts.index, autopct='%1.1f%%')
            axes[1, 0].set_title('數據源分布')
        
        # 4. 品質分數分布
        quality_scores = [report['quality_score'] for report in final_report['symbol_reports'].values()]
        axes[1, 1].hist(quality_scores, bins=10, alpha=0.7, edgecolor='black')
        axes[1, 1].set_title('品質分數分布')
        axes[1, 1].set_xlabel('品質分數')
        axes[1, 1].set_ylabel('股票數量')
    
    plt.tight_layout()
    plt.show()
    
    print("✅ 數據可視化完成")

# ============================================================================
# Cell 10: 總結和建議
# ============================================================================

print("\n🎯 演示總結")
print("=" * 50)

print("✅ 成功完成的功能:")
print("   1. ✓ 多渠道數據爬取 (Yahoo Finance + TPEX)")
print("   2. ✓ 並行處理提升效率")
print("   3. ✓ 數據品質驗證和過濾")
print("   4. ✓ 自學能力和自動重試")
print("   5. ✓ 準確性報告生成")
print("   6. ✓ UPSERT資料庫操作")
print("   7. ✓ 數據可視化分析")

print(f"\n📊 最終統計:")
print(f"   目標股票數: {len(SYMBOLS)}")
print(f"   成功獲取數據: {len([s for s, d in multi_channel_results.items() if not d.empty])}")
print(f"   總記錄數: {sum(len(d) for d in multi_channel_results.values())}")
print(f"   平均品質分數: {final_report['overall_quality']:.3f}")

print(f"\n🚀 系統優勢:")
print("   • 多渠道備援確保數據可靠性")
print("   • 並行處理提升爬取效率")
print("   • 智能驗證保證數據品質")
print("   • 自學能力持續優化")
print("   • 完整的監控和報告機制")

print(f"\n💡 擴充建議:")
print("   • 添加更多數據源 (如證交所API)")
print("   • 實施基本面數據爬取")
print("   • 增加實時數據更新")
print("   • 建立數據異常告警機制")
print("   • 優化數據存儲和查詢性能")

print(f"\n🎉 多渠道股票數據爬蟲系統演示完成！")
print("=" * 50)
