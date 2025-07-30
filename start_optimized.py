#!/usr/bin/env python3
"""
Optimized Startup Script for AI Trading System

This script starts the AI Trading System with all Phase 1-3 performance optimizations enabled.
It ensures optimal memory usage and performance from the start.
"""

import os
import sys
import subprocess
import psutil
import time
from pathlib import Path

def check_system_resources():
    """檢查系統資源"""
    print("🔍 檢查系統資源...")
    
    # 檢查可用記憶體
    memory = psutil.virtual_memory()
    available_gb = memory.available / (1024**3)
    
    print(f"  💾 可用記憶體: {available_gb:.1f}GB")
    
    if available_gb < 2.0:
        print("  ⚠️  可用記憶體不足 2GB，可能影響性能")
        return False
    
    # 檢查 CPU
    cpu_count = psutil.cpu_count()
    print(f"  🖥️  CPU 核心數: {cpu_count}")
    
    return True


def setup_environment():
    """設置環境變數"""
    print("🔧 設置環境變數...")
    
    # 設置 Python 路徑
    project_root = Path(__file__).parent
    os.environ['PYTHONPATH'] = str(project_root)
    
    # 設置 Streamlit 配置
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_SERVER_PORT'] = '8501'
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '127.0.0.1'
    
    # 設置記憶體優化
    os.environ['STREAMLIT_SERVER_MAX_UPLOAD_SIZE'] = '200'
    os.environ['STREAMLIT_SERVER_MAX_MESSAGE_SIZE'] = '200'
    
    # 設置 AI 框架優化
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 減少 TensorFlow 日誌
    os.environ['CUDA_VISIBLE_DEVICES'] = ''   # 禁用 GPU（減少記憶體使用）
    
    print("  ✅ 環境變數設置完成")


def check_optimizations():
    """檢查優化系統是否可用"""
    print("🚀 檢查性能優化系統...")
    
    optimizations = {}
    
    # 檢查 Phase 1 優化
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from src.ui.pages.data_management import get_core_modules
        optimizations['phase1'] = True
        print("  ✅ Phase 1 優化: 可用")
    except ImportError as e:
        optimizations['phase1'] = False
        print(f"  ❌ Phase 1 優化: 不可用 ({e})")
    
    # 檢查 Phase 2 優化
    try:
        from src.ui.utils.ai_lazy_loader import ai_lazy_loader
        optimizations['phase2'] = True
        print("  ✅ Phase 2 優化: 可用")
    except ImportError as e:
        optimizations['phase2'] = False
        print(f"  ❌ Phase 2 優化: 不可用 ({e})")
    
    # 檢查 Phase 3 優化
    try:
        from src.ui.utils.ai_framework_lazy_loader import ai_framework_loader
        optimizations['phase3'] = True
        print("  ✅ Phase 3 優化: 可用")
    except ImportError as e:
        optimizations['phase3'] = False
        print(f"  ❌ Phase 3 優化: 不可用 ({e})")
    
    # 檢查記憶體優化器
    try:
        from src.ui.utils.memory_optimizer import memory_optimizer
        optimizations['memory'] = True
        print("  ✅ 記憶體優化器: 可用")
    except ImportError as e:
        optimizations['memory'] = False
        print(f"  ❌ 記憶體優化器: 不可用 ({e})")
    
    return optimizations


def start_streamlit():
    """啟動 Streamlit 應用程式"""
    print("🚀 啟動 AI Trading System...")
    
    # 構建啟動命令
    cmd = [
        sys.executable, '-m', 'streamlit', 'run',
        'src/ui/web_ui.py',
        '--server.address=127.0.0.1',
        '--server.port=8501',
        '--server.headless=true',
        '--server.enableCORS=false',
        '--server.enableXsrfProtection=false',
        '--server.maxUploadSize=200',
        '--server.maxMessageSize=200'
    ]
    
    print(f"  📝 啟動命令: {' '.join(cmd)}")
    print(f"  🌐 應用程式將在 http://127.0.0.1:8501 啟動")
    print(f"  💡 使用 Ctrl+C 停止應用程式")
    print()
    
    try:
        # 啟動 Streamlit
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 應用程式已停止")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 啟動失敗: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 未知錯誤: {e}")
        return False
    
    return True


def show_performance_tips():
    """顯示性能使用建議"""
    print("\n💡 性能使用建議:")
    print("  • 首次啟動後，記憶體使用量應 <50MB")
    print("  • 只在需要時使用 AI 功能（會載入重型框架）")
    print("  • 優先選擇 '基礎圖表' 而非 'AI整合圖表'")
    print("  • 在側邊欄啟用 '性能監控' 查看即時狀態")
    print("  • 如果記憶體使用 >200MB，考慮重啟應用程式")
    print()


def main():
    """主函數"""
    print("🎯 AI Trading System - 優化啟動器")
    print("=" * 50)
    
    # 檢查系統資源
    if not check_system_resources():
        print("❌ 系統資源不足，可能影響性能")
        response = input("是否繼續啟動？(y/N): ")
        if response.lower() != 'y':
            return
    
    # 設置環境
    setup_environment()
    
    # 檢查優化系統
    optimizations = check_optimizations()
    
    available_count = sum(1 for available in optimizations.values() if available)
    total_count = len(optimizations)
    
    print(f"\n📊 優化系統狀態: {available_count}/{total_count} 可用")
    
    if available_count == 0:
        print("⚠️  沒有優化系統可用，性能可能不佳")
        response = input("是否繼續啟動？(y/N): ")
        if response.lower() != 'y':
            return
    elif available_count < total_count:
        print("⚠️  部分優化系統不可用，性能可能受影響")
    else:
        print("✅ 所有優化系統可用，預期最佳性能")
    
    # 顯示性能建議
    show_performance_tips()
    
    # 啟動應用程式
    input("按 Enter 鍵啟動應用程式...")
    start_streamlit()


if __name__ == "__main__":
    main()
