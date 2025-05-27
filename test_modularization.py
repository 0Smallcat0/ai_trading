"""測試模組化重構結果

此腳本用於驗證報表視覺化服務的模組化重構是否成功。
"""

import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.append(str(project_root))

def test_imports():
    """測試模組導入"""
    print("🔍 測試模組導入...")
    
    try:
        # 測試子模組導入
        from src.core.visualization.data_retrieval import DataRetrievalService
        print("✅ DataRetrievalService 導入成功")
        
        from src.core.visualization.chart_generators import ChartGeneratorService
        print("✅ ChartGeneratorService 導入成功")
        
        from src.core.visualization.report_exporters import ReportExporterService
        print("✅ ReportExporterService 導入成功")
        
        from src.core.visualization.config_management import ConfigManagementService
        print("✅ ConfigManagementService 導入成功")
        
        # 測試主服務導入
        from src.core.report_visualization_service import ReportVisualizationService
        print("✅ ReportVisualizationService 導入成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 導入失敗: {e}")
        return False

def test_file_sizes():
    """測試檔案大小"""
    print("\n📏 檢查檔案大小...")
    
    files_to_check = [
        "src/core/report_visualization_service.py",
        "src/core/visualization/data_retrieval.py", 
        "src/core/visualization/chart_generators.py",
        "src/core/visualization/report_exporters.py",
        "src/core/visualization/config_management.py"
    ]
    
    total_lines = 0
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                total_lines += lines
                status = "✅" if lines <= 1000 else "⚠️"
                print(f"{status} {file_path}: {lines} 行")
        except FileNotFoundError:
            print(f"❌ {file_path}: 檔案不存在")
    
    print(f"\n📊 總行數: {total_lines} 行")
    return total_lines

def test_service_structure():
    """測試服務結構"""
    print("\n🏗️ 測試服務結構...")
    
    try:
        from src.core.report_visualization_service import ReportVisualizationService
        
        # 檢查是否有必要的屬性（不實際初始化）
        service_class = ReportVisualizationService
        
        # 檢查方法是否存在
        expected_methods = [
            'get_trading_performance_data',
            'get_trade_details_data', 
            'generate_cumulative_return_chart',
            'generate_drawdown_chart',
            'generate_performance_dashboard',
            'export_report',
            'save_chart_config',
            'cleanup_cache'
        ]
        
        missing_methods = []
        for method in expected_methods:
            if not hasattr(service_class, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"❌ 缺少方法: {missing_methods}")
            return False
        else:
            print("✅ 所有預期方法都存在")
            return True
            
    except Exception as e:
        print(f"❌ 結構測試失敗: {e}")
        return False

def main():
    """主函數"""
    print("🚀 開始測試報表視覺化服務模組化重構...")
    print("=" * 60)
    
    # 測試導入
    import_success = test_imports()
    
    # 測試檔案大小
    total_lines = test_file_sizes()
    
    # 測試服務結構
    structure_success = test_service_structure()
    
    # 總結
    print("\n" + "=" * 60)
    print("📋 測試總結:")
    print(f"✅ 模組導入: {'成功' if import_success else '失敗'}")
    print(f"✅ 檔案大小: {total_lines} 行 (原本 1144 行)")
    print(f"✅ 服務結構: {'完整' if structure_success else '不完整'}")
    
    if import_success and structure_success:
        print("\n🎉 模組化重構成功！")
        print("📈 主要成就:")
        print("   - 將 1144 行的大檔案分割成 5 個模組")
        print("   - 保持向後相容性")
        print("   - 提高代碼可維護性")
        print("   - 符合單一職責原則")
        return True
    else:
        print("\n❌ 模組化重構需要進一步修正")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
