"""
歷史資料回填與驗證模組增強功能示例

此示例展示如何使用新實作的四個子功能：
1. 分時段平行下載機制
2. 增量更新識別模式
3. 時間序列連續性檢查
4. 異常值自動標記系統
"""

import datetime
import logging
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.historical_backfill import (
    HistoricalBackfill,
    OutlierDetectionMethod,
    OutlierTreatmentStrategy,
    DataQualityStatus,
    backfill_historical_data,
)

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_parallel_download():
    """示例1: 分時段平行下載機制"""
    print("\n" + "="*60)
    print("示例1: 分時段平行下載機制")
    print("="*60)
    
    # 創建回填器實例
    backfiller = HistoricalBackfill(
        max_workers=3,
        chunk_size=15,  # 每15天一個分塊
        enable_progress_tracking=True
    )
    
    # 執行分時段下載
    try:
        result = backfiller.parallel_download_with_time_segments(
            symbols=['AAPL', 'GOOGL'],
            start_date='2023-01-01',
            end_date='2023-01-31',
            show_progress=True
        )
        
        print(f"成功下載 {len(result)} 個股票的數據")
        for symbol, data in result.items():
            print(f"  {symbol}: {len(data)} 筆記錄")
            
        # 顯示進度資訊
        progress = backfiller.get_progress_info()
        print(f"下載進度: {progress['chunk_progress']:.1f}%")
        
    except Exception as e:
        print(f"下載失敗: {e}")


def demo_incremental_update():
    """示例2: 增量更新識別模式"""
    print("\n" + "="*60)
    print("示例2: 增量更新識別模式")
    print("="*60)
    
    backfiller = HistoricalBackfill()
    
    try:
        # 執行增量更新檢測
        update_info = backfiller.incremental_update_detection(
            symbols=['AAPL', 'MSFT'],
            start_date='2023-01-01',
            end_date='2023-12-31'
        )
        
        print("增量更新檢測結果:")
        for symbol, info in update_info.items():
            print(f"  {symbol}:")
            print(f"    需要更新: {info.needs_update}")
            print(f"    更新範圍數量: {len(info.update_ranges)}")
            if info.update_ranges:
                print(f"    第一個範圍: {info.update_ranges[0]}")
                
    except Exception as e:
        print(f"增量更新檢測失敗: {e}")


def demo_continuity_check():
    """示例3: 時間序列連續性檢查"""
    print("\n" + "="*60)
    print("示例3: 時間序列連續性檢查")
    print("="*60)
    
    import pandas as pd
    import numpy as np
    
    # 創建測試數據（有缺失日期）
    dates = pd.date_range('2023-01-01', '2023-01-31', freq='D')
    # 移除一些日期來模擬缺失
    incomplete_dates = dates.drop([dates[10], dates[15], dates[20]])
    
    test_data = {
        'AAPL': pd.DataFrame({
            'open': np.random.uniform(150, 160, len(incomplete_dates)),
            'high': np.random.uniform(160, 170, len(incomplete_dates)),
            'low': np.random.uniform(140, 150, len(incomplete_dates)),
            'close': np.random.uniform(145, 165, len(incomplete_dates)),
            'volume': np.random.randint(1000000, 5000000, len(incomplete_dates)),
        }, index=incomplete_dates)
    }
    
    backfiller = HistoricalBackfill()
    
    try:
        # 執行連續性檢查
        reports = backfiller.comprehensive_continuity_check(
            data=test_data,
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2023, 1, 31)
        )
        
        print("時間序列連續性檢查結果:")
        for symbol, report in reports.items():
            print(f"  {symbol}:")
            print(f"    總記錄數: {report.total_records}")
            print(f"    缺失日期數: {len(report.missing_dates)}")
            print(f"    連續性分數: {report.continuity_score:.3f}")
            print(f"    品質狀態: {report.quality_status.value}")
            print(f"    問題數量: {len(report.issues)}")
            if report.recommendations:
                print(f"    建議: {report.recommendations[0]}")
                
    except Exception as e:
        print(f"連續性檢查失敗: {e}")


def demo_outlier_detection():
    """示例4: 異常值自動標記系統"""
    print("\n" + "="*60)
    print("示例4: 異常值自動標記系統")
    print("="*60)
    
    import pandas as pd
    import numpy as np
    
    # 創建包含異常值的測試數據
    dates = pd.date_range('2023-01-01', '2023-01-31', freq='D')
    normal_prices = np.random.uniform(100, 110, len(dates))
    
    # 添加一些異常值
    normal_prices[10] = 200  # 異常高價
    normal_prices[20] = 50   # 異常低價
    
    test_data = {
        'AAPL': pd.DataFrame({
            'open': normal_prices * 0.98,
            'high': normal_prices * 1.02,
            'low': normal_prices * 0.95,
            'close': normal_prices,
            'volume': np.random.randint(1000000, 5000000, len(dates)),
        }, index=dates)
    }
    
    backfiller = HistoricalBackfill(
        outlier_detection_method=OutlierDetectionMethod.Z_SCORE,
        outlier_treatment=OutlierTreatmentStrategy.MARK_ONLY
    )
    
    try:
        # 執行異常值檢測
        outlier_results = backfiller.automated_outlier_detection_system(
            data=test_data,
            methods=[OutlierDetectionMethod.Z_SCORE, OutlierDetectionMethod.IQR]
        )
        
        print("異常值檢測結果:")
        for symbol, result in outlier_results.items():
            print(f"  {symbol}:")
            print(f"    檢測到異常值: {result['outliers_detected']}")
            print(f"    異常值數量: {result['outlier_count']}")
            print(f"    異常值百分比: {result['outlier_percentage']:.2f}%")
            print(f"    使用方法: {', '.join(result['methods_used'])}")
            print(f"    處理策略已應用: {result['treatment_applied']}")
            
    except Exception as e:
        print(f"異常值檢測失敗: {e}")


def demo_comprehensive_backfill():
    """示例5: 綜合回填與驗證"""
    print("\n" + "="*60)
    print("示例5: 綜合回填與驗證")
    print("="*60)
    
    try:
        # 使用便捷函數執行綜合回填
        result = backfill_historical_data(
            symbols=['AAPL'],
            start_date='2023-01-01',
            end_date='2023-01-15',
            max_workers=2,
            chunk_size=7,
            validate=True,
            save_result=False,  # 不儲存以避免檔案操作
            enable_incremental=True,
            enable_outlier_detection=True
        )
        
        print("綜合回填結果:")
        print(f"  執行成功: {result['success']}")
        print(f"  執行時間: {result['execution_time']:.2f} 秒")
        print(f"  下載股票數: {len(result.get('data', {}))}")
        
        if 'statistics' in result:
            stats = result['statistics']
            print(f"  總記錄數: {stats['total_records']}")
            print(f"  數據品質分佈:")
            for quality, count in stats['data_quality'].items():
                if count > 0:
                    print(f"    {quality}: {count}")
                    
        if 'quality_reports' in result:
            print(f"  品質報告數: {len(result['quality_reports'])}")
            
        if 'outlier_results' in result:
            print(f"  異常值檢測結果數: {len(result['outlier_results'])}")
            
    except Exception as e:
        print(f"綜合回填失敗: {e}")


def main():
    """主函數"""
    print("歷史資料回填與驗證模組增強功能示例")
    print("此示例展示四個主要子功能的使用方法")
    
    # 執行各個示例
    demo_parallel_download()
    demo_incremental_update()
    demo_continuity_check()
    demo_outlier_detection()
    demo_comprehensive_backfill()
    
    print("\n" + "="*60)
    print("所有示例執行完成！")
    print("="*60)


if __name__ == "__main__":
    main()
