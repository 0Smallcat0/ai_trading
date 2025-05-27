"""簡單的導入測試

測試模組化重構後的導入是否正常工作。
"""

import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_individual_modules():
    """測試各個子模組的導入"""
    print("🔍 測試各個子模組導入...")
    
    try:
        from src.core.visualization.data_retrieval import DataRetrievalService
        print("✅ DataRetrievalService 導入成功")
        
        from src.core.visualization.chart_generators import ChartGeneratorService
        print("✅ ChartGeneratorService 導入成功")
        
        from src.core.visualization.report_exporters import ReportExporterService
        print("✅ ReportExporterService 導入成功")
        
        from src.core.visualization.config_management import ConfigManagementService
        print("✅ ConfigManagementService 導入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 子模組導入失敗: {e}")
        return False

def test_main_service_import():
    """測試主服務的導入（不初始化）"""
    print("\n🔍 測試主服務導入...")
    
    try:
        from src.core.report_visualization_service import ReportVisualizationService
        print("✅ ReportVisualizationService 導入成功")
        
        # 檢查類別是否有預期的方法
        expected_methods = [
            'get_trading_performance_data',
            'generate_cumulative_return_chart',
            'export_report'
        ]
        
        for method in expected_methods:
            if hasattr(ReportVisualizationService, method):
                print(f"✅ 方法 {method} 存在")
            else:
                print(f"❌ 方法 {method} 不存在")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 主服務導入失敗: {e}")
        return False

def test_file_structure():
    """測試檔案結構"""
    print("\n📁 檢查檔案結構...")
    
    files_to_check = [
        "src/core/report_visualization_service.py",
        "src/core/visualization/__init__.py",
        "src/core/visualization/data_retrieval.py", 
        "src/core/visualization/chart_generators.py",
        "src/core/visualization/report_exporters.py",
        "src/core/visualization/config_management.py"
    ]
    
    all_exist = True
    total_lines = 0
    
    for file_path in files_to_check:
        if Path(file_path).exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                total_lines += lines
                print(f"✅ {file_path}: {lines} 行")
        else:
            print(f"❌ {file_path}: 檔案不存在")
            all_exist = False
    
    print(f"\n📊 總行數: {total_lines} 行")
    return all_exist, total_lines

def main():
    """主函數"""
    print("🚀 開始簡單導入測試...")
    print("=" * 50)
    
    # 測試檔案結構
    structure_ok, total_lines = test_file_structure()
    
    # 測試子模組導入
    modules_ok = test_individual_modules()
    
    # 測試主服務導入
    main_service_ok = test_main_service_import()
    
    # 總結
    print("\n" + "=" * 50)
    print("📋 測試總結:")
    print(f"✅ 檔案結構: {'正常' if structure_ok else '異常'}")
    print(f"✅ 子模組導入: {'成功' if modules_ok else '失敗'}")
    print(f"✅ 主服務導入: {'成功' if main_service_ok else '失敗'}")
    print(f"📊 總行數: {total_lines} 行")
    
    if structure_ok and modules_ok and main_service_ok:
        print("\n🎉 模組化重構導入測試成功！")
        print("📈 主要成就:")
        print("   - 成功將大檔案分割成多個模組")
        print("   - 所有模組都能正常導入")
        print("   - 保持了 API 的完整性")
        return True
    else:
        print("\n❌ 模組化重構導入測試失敗")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
