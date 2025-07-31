#!/usr/bin/env python3
"""
Performance Monitor Component - Phase 3 Optimization

Real-time performance monitoring component for the Streamlit sidebar.
Shows memory usage, AI framework status, and performance recommendations.
"""

import streamlit as st
import psutil
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def show_performance_monitor():
    """顯示性能監控面板 - Phase 3 優化"""
    try:
        # 獲取當前記憶體使用量
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # 檢查 Phase 3 優化狀態
        lazy_loading_status = check_lazy_loading_status()
        memory_optimizer_status = check_memory_optimizer_status()
        
        # 顯示性能指標
        st.sidebar.markdown("### 🚀 性能監控 (Phase 3)")
        
        # 記憶體使用量指標
        show_memory_metrics(memory_mb)
        
        # AI 框架狀態
        show_ai_framework_status(lazy_loading_status)
        
        # 記憶體優化器狀態
        show_memory_optimizer_status(memory_optimizer_status)
        
        # 性能建議
        show_performance_recommendations(memory_mb, lazy_loading_status)
        
        # 快速操作按鈕
        show_quick_actions()
        
    except Exception as e:
        st.sidebar.error(f"性能監控錯誤: {e}")
        logger.error(f"Performance monitor error: {e}")


def check_lazy_loading_status() -> Dict[str, Any]:
    """檢查懶加載系統狀態"""
    try:
        from src.ui.utils.ai_framework_lazy_loader import ai_framework_loader
        
        frameworks_info = ai_framework_loader.get_all_frameworks_info()
        
        return {
            'available': True,
            'loaded_frameworks': sum(1 for fw in frameworks_info.values() if fw.is_loaded),
            'available_frameworks': sum(1 for fw in frameworks_info.values() if fw.is_available),
            'frameworks_info': frameworks_info
        }
    except ImportError:
        return {
            'available': False,
            'error': 'Lazy loading system not available'
        }
    except Exception as e:
        return {
            'available': False,
            'error': str(e)
        }


def check_memory_optimizer_status() -> Dict[str, Any]:
    """檢查記憶體優化器狀態"""
    try:
        from src.ui.utils.memory_optimizer import memory_optimizer
        
        stats = memory_optimizer.get_statistics()
        report = memory_optimizer.get_memory_report()
        
        return {
            'available': True,
            'is_running': memory_optimizer.cleanup_running,
            'stats': stats,
            'report': report
        }
    except ImportError:
        return {
            'available': False,
            'error': 'Memory optimizer not available'
        }
    except Exception as e:
        return {
            'available': False,
            'error': str(e)
        }


def show_memory_metrics(memory_mb: float):
    """顯示記憶體使用量指標"""
    # 記憶體使用量顏色編碼
    if memory_mb < 200:
        color = "normal"
        status = "✅ 正常"
    elif memory_mb < 300:
        color = "inverse"
        status = "⚠️ 偏高"
    else:
        color = "inverse"
        status = "🔴 過高"
    
    st.sidebar.metric(
        "記憶體使用量", 
        f"{memory_mb:.1f}MB",
        delta=f"目標: <200MB ({status})",
        delta_color=color
    )
    
    # 記憶體使用量進度條
    memory_percentage = min(memory_mb / 500 * 100, 100)  # 假設 500MB 為最大值
    st.sidebar.progress(memory_percentage / 100)


def show_ai_framework_status(lazy_status: Dict[str, Any]):
    """顯示 AI 框架狀態"""
    if lazy_status['available']:
        loaded = lazy_status['loaded_frameworks']
        available = lazy_status['available_frameworks']
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            st.metric("已載入框架", f"{loaded}")
        
        with col2:
            st.metric("可用框架", f"{available}")
        
        if loaded == 0:
            st.sidebar.success("✅ 懶加載正常 - 無不必要的框架載入")
        else:
            st.sidebar.warning(f"⚠️ {loaded} 個框架已載入")
            
            # 顯示已載入的框架詳情
            with st.sidebar.expander("已載入框架詳情"):
                for name, fw in lazy_status['frameworks_info'].items():
                    if fw.is_loaded:
                        st.write(f"• **{name}**: {fw.memory_usage:.1f}MB")
    else:
        st.sidebar.info("ℹ️ 懶加載系統未啟用")
        if 'error' in lazy_status:
            st.sidebar.caption(f"錯誤: {lazy_status['error']}")


def show_memory_optimizer_status(optimizer_status: Dict[str, Any]):
    """顯示記憶體優化器狀態"""
    if optimizer_status['available']:
        is_running = optimizer_status.get('is_running', False)
        
        if is_running:
            st.sidebar.success("🧠 記憶體優化器: 運行中")
        else:
            st.sidebar.info("🧠 記憶體優化器: 未運行")
        
        # 顯示統計資訊
        if 'stats' in optimizer_status:
            stats = optimizer_status['stats']
            
            with st.sidebar.expander("優化器統計"):
                st.write(f"• 清理次數: {stats.get('cleanups_performed', 0)}")
                st.write(f"• 釋放記憶體: {stats.get('memory_freed_mb', 0):.1f}MB")
                st.write(f"• 快取驅逐: {stats.get('cache_evictions', 0)}")
    else:
        st.sidebar.warning("⚠️ 記憶體優化器未啟用")


def show_performance_recommendations(memory_mb: float, lazy_status: Dict[str, Any]):
    """顯示性能建議"""
    recommendations = []
    
    if memory_mb > 300:
        recommendations.append("🚨 記憶體使用過高 - 建議重啟應用程式")
    elif memory_mb > 200:
        recommendations.append("⚠️ 記憶體使用偏高 - 避免使用 AI 功能")
    
    if lazy_status['available'] and lazy_status['loaded_frameworks'] > 0:
        recommendations.append("💡 有 AI 框架已載入 - 考慮使用基礎功能")
    
    if not lazy_status['available']:
        recommendations.append("🔧 懶加載系統未啟用 - 性能可能受影響")
    
    if recommendations:
        with st.sidebar.expander("💡 性能建議", expanded=memory_mb > 200):
            for rec in recommendations:
                st.write(f"• {rec}")
    else:
        st.sidebar.success("✅ 系統性能良好")


def show_quick_actions():
    """顯示快速操作按鈕"""
    st.sidebar.markdown("### ⚡ 快速操作")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("🧹 清理記憶體", help="強制執行記憶體清理"):
            perform_memory_cleanup()
    
    with col2:
        if st.button("📊 詳細報告", help="顯示詳細性能報告"):
            show_detailed_report()


def perform_memory_cleanup():
    """執行記憶體清理"""
    try:
        from src.ui.utils.memory_optimizer import memory_optimizer
        
        with st.sidebar.spinner("正在清理記憶體..."):
            result = memory_optimizer.force_cleanup()
            
        if result['cleanup_successful']:
            st.sidebar.success(f"✅ 清理完成！釋放 {result['memory_freed_mb']:.1f}MB")
        else:
            st.sidebar.warning("⚠️ 清理完成，但未釋放顯著記憶體")
            
    except ImportError:
        st.sidebar.error("❌ 記憶體優化器不可用")
    except Exception as e:
        st.sidebar.error(f"❌ 清理失敗: {e}")


def show_detailed_report():
    """顯示詳細性能報告"""
    try:
        # 獲取系統資訊
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()
        
        # 顯示詳細報告
        with st.sidebar.expander("📊 詳細性能報告", expanded=True):
            st.write("**系統資源:**")
            st.write(f"• RSS 記憶體: {memory_info.rss / 1024 / 1024:.1f}MB")
            st.write(f"• VMS 記憶體: {memory_info.vms / 1024 / 1024:.1f}MB")
            st.write(f"• CPU 使用率: {cpu_percent:.1f}%")
            
            # 獲取記憶體優化器報告
            try:
                from src.ui.utils.memory_optimizer import memory_optimizer
                report = memory_optimizer.get_memory_report()
                
                st.write("**記憶體優化:**")
                st.write(f"• 目標記憶體: {report['memory_target_mb']:.1f}MB")
                st.write(f"• 當前記憶體: {report['current_memory_mb']:.1f}MB")
                st.write(f"• 記憶體增長: {report['memory_increase_mb']:.1f}MB")
                st.write(f"• 管理快取: {report['managed_caches']} 個")
                
            except ImportError:
                st.write("記憶體優化器報告不可用")
                
    except Exception as e:
        st.sidebar.error(f"無法生成詳細報告: {e}")


def show_performance_alert(message: str, alert_type: str = "warning"):
    """顯示性能警告"""
    if alert_type == "error":
        st.sidebar.error(f"🚨 {message}")
    elif alert_type == "warning":
        st.sidebar.warning(f"⚠️ {message}")
    else:
        st.sidebar.info(f"ℹ️ {message}")


# 便利函數
def get_current_memory_usage() -> float:
    """獲取當前記憶體使用量 (MB)"""
    try:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except Exception:
        return 0.0


def is_memory_usage_high() -> bool:
    """檢查記憶體使用量是否過高"""
    return get_current_memory_usage() > 200.0


def is_lazy_loading_active() -> bool:
    """檢查懶加載是否啟用"""
    try:
        from src.ui.utils.ai_framework_lazy_loader import ai_framework_loader
        return True
    except ImportError:
        return False
