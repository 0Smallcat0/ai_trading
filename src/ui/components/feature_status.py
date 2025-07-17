"""
功能狀態指示器組件

此模組提供系統功能可用性的視覺化指示，幫助用戶了解：
- 哪些功能可以正常使用
- 哪些功能需要額外配置
- 如何啟用不可用的功能
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class FeatureStatusIndicator:
    """功能狀態指示器"""
    
    def __init__(self):
        self.feature_checks = {
            "數據管理": self._check_data_management,
            "策略管理": self._check_strategy_management,
            "回測分析": self._check_backtest,
            "風險管理": self._check_risk_management,
            "交易執行": self._check_trading,
            "AI模型": self._check_ai_models,
            "券商整合": self._check_broker_integration,
            "通知服務": self._check_notifications,
        }
    
    def check_all_features(self) -> Dict[str, Dict[str, Any]]:
        """檢查所有功能狀態"""
        results = {}
        
        for feature_name, check_func in self.feature_checks.items():
            try:
                status, message, suggestions = check_func()
                results[feature_name] = {
                    "status": status,
                    "message": message,
                    "suggestions": suggestions
                }
            except Exception as e:
                results[feature_name] = {
                    "status": "error",
                    "message": f"檢查失敗: {str(e)}",
                    "suggestions": ["聯繫技術支援"]
                }
        
        return results
    
    def _check_data_management(self) -> Tuple[str, str, List[str]]:
        """檢查數據管理功能"""
        try:
            from src.data_sources.unified_data_manager import UnifiedDataManager
            manager = UnifiedDataManager()
            sources = manager.get_available_sources()
            
            if len(sources) >= 2:
                return "healthy", f"數據管理正常 ({len(sources)} 個數據源可用)", []
            elif len(sources) == 1:
                return "warning", f"數據管理部分可用 ({len(sources)} 個數據源)", [
                    "安裝更多數據源: pip install baostock FinMind",
                    "配置API金鑰以啟用更多數據源"
                ]
            else:
                return "error", "數據管理不可用", [
                    "運行: python install_dependencies.py",
                    "檢查網路連接",
                    "查看數據源配置指南"
                ]
        except Exception as e:
            return "error", f"數據管理模組錯誤: {str(e)}", [
                "重新安裝依賴包",
                "檢查模組導入路徑"
            ]
    
    def _check_strategy_management(self) -> Tuple[str, str, List[str]]:
        """檢查策略管理功能"""
        try:
            from src.strategy.base import Strategy
            from src.strategy.technical import MovingAverageCrossStrategy
            return "healthy", "策略管理功能正常", []
        except Exception as e:
            return "error", f"策略管理錯誤: {str(e)}", [
                "檢查策略模組安裝",
                "重新安裝系統依賴"
            ]
    
    def _check_backtest(self) -> Tuple[str, str, List[str]]:
        """檢查回測功能"""
        try:
            from src.core.backtest_service import BacktestService
            
            # 檢查backtrader
            try:
                import backtrader
                return "healthy", "回測功能完全可用 (包含高級功能)", []
            except ImportError:
                return "warning", "回測功能基礎可用 (缺少高級功能)", [
                    "安裝backtrader: pip install backtrader",
                    "啟用專業回測功能"
                ]
        except Exception as e:
            return "error", f"回測功能錯誤: {str(e)}", [
                "檢查回測模組",
                "重新安裝依賴"
            ]
    
    def _check_risk_management(self) -> Tuple[str, str, List[str]]:
        """檢查風險管理功能"""
        try:
            from src.risk_management.risk_manager_refactored import RiskManager
            manager = RiskManager()
            return "healthy", "風險管理功能正常", []
        except Exception as e:
            return "error", f"風險管理錯誤: {str(e)}", [
                "檢查風險管理模組",
                "重新安裝系統"
            ]
    
    def _check_trading(self) -> Tuple[str, str, List[str]]:
        """檢查交易執行功能"""
        try:
            from src.execution.simulator_adapter import SimulatorAdapter
            simulator = SimulatorAdapter()
            
            # 檢查真實券商適配器
            real_brokers = 0
            try:
                # 更新導入：使用推薦的重構版本
                try:
                    from src.execution.ib_adapter_refactored import IBAdapterRefactored as IBAdapter
                except ImportError:
                    # 如果重構版本不存在，跳過
                    pass
                real_brokers += 1
            except:
                pass
            
            try:
                from src.execution.shioaji_adapter import ShioajiAdapter
                real_brokers += 1
            except:
                pass
            
            if real_brokers > 0:
                return "healthy", f"交易功能正常 (模擬 + {real_brokers} 個真實券商)", []
            else:
                return "warning", "交易功能部分可用 (僅模擬交易)", [
                    "配置券商API以啟用真實交易",
                    "查看券商整合指南"
                ]
        except Exception as e:
            return "error", f"交易功能錯誤: {str(e)}", [
                "檢查交易執行模組"
            ]
    
    def _check_ai_models(self) -> Tuple[str, str, List[str]]:
        """檢查AI模型功能"""
        try:
            from src.models.ml_models import MLModels
            
            # 檢查深度學習框架
            frameworks = []
            try:
                import tensorflow
                frameworks.append("TensorFlow")
            except ImportError:
                pass
            
            try:
                import torch
                frameworks.append("PyTorch")
            except ImportError:
                pass
            
            if frameworks:
                return "healthy", f"AI模型功能正常 ({', '.join(frameworks)} 可用)", []
            else:
                return "warning", "AI模型基礎功能可用 (缺少深度學習)", [
                    "安裝TensorFlow: pip install tensorflow",
                    "安裝PyTorch: pip install torch",
                    "啟用深度學習功能"
                ]
        except Exception as e:
            return "warning", "AI模型功能部分可用", [
                "檢查機器學習依賴",
                "安裝scikit-learn"
            ]
    
    def _check_broker_integration(self) -> Tuple[str, str, List[str]]:
        """檢查券商整合功能"""
        available_brokers = []
        
        # 檢查各券商API
        try:
            import shioaji
            available_brokers.append("永豐證券")
        except ImportError:
            pass
        
        try:
            from ibapi import wrapper
            available_brokers.append("Interactive Brokers")
        except ImportError:
            pass
        
        if len(available_brokers) >= 2:
            return "healthy", f"券商整合正常 ({', '.join(available_brokers)})", []
        elif len(available_brokers) == 1:
            return "warning", f"部分券商可用 ({available_brokers[0]})", [
                "安裝更多券商API",
                "查看券商整合指南"
            ]
        else:
            return "warning", "僅模擬交易可用", [
                "安裝券商API: pip install shioaji ibapi",
                "配置券商帳戶"
            ]
    
    def _check_notifications(self) -> Tuple[str, str, List[str]]:
        """檢查通知服務功能"""
        try:
            from src.monitoring.notification_manager import NotificationManager
            return "healthy", "通知服務正常", []
        except Exception as e:
            return "warning", "通知服務部分可用", [
                "配置郵件/LINE/Telegram通知",
                "查看通知設定指南"
            ]
    
    def display_feature_status(self, results: Dict[str, Dict[str, Any]]) -> None:
        """顯示功能狀態"""
        st.subheader("🔍 系統功能狀態")
        
        # 統計狀態
        healthy_count = sum(1 for r in results.values() if r["status"] == "healthy")
        warning_count = sum(1 for r in results.values() if r["status"] == "warning")
        error_count = sum(1 for r in results.values() if r["status"] == "error")
        total_count = len(results)
        
        # 顯示總體狀態
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("正常功能", healthy_count, f"{healthy_count/total_count*100:.0f}%")
        with col2:
            st.metric("部分可用", warning_count, f"{warning_count/total_count*100:.0f}%")
        with col3:
            st.metric("需要修復", error_count, f"{error_count/total_count*100:.0f}%")
        with col4:
            st.metric("總功能數", total_count)
        
        # 顯示詳細狀態
        for feature_name, result in results.items():
            status = result["status"]
            message = result["message"]
            suggestions = result["suggestions"]
            
            if status == "healthy":
                st.success(f"✅ **{feature_name}**: {message}")
            elif status == "warning":
                st.warning(f"⚠️ **{feature_name}**: {message}")
                if suggestions:
                    with st.expander(f"💡 {feature_name} 改進建議"):
                        for suggestion in suggestions:
                            st.write(f"• {suggestion}")
            else:
                st.error(f"❌ **{feature_name}**: {message}")
                if suggestions:
                    with st.expander(f"🔧 {feature_name} 修復建議"):
                        for suggestion in suggestions:
                            st.write(f"• {suggestion}")


# 全局實例
feature_status = FeatureStatusIndicator()


def show_feature_status():
    """顯示功能狀態頁面"""
    st.title("🔍 系統功能狀態")
    
    with st.spinner("正在檢查系統功能..."):
        results = feature_status.check_all_features()
    
    feature_status.display_feature_status(results)
    
    # 提供快速操作
    st.subheader("🚀 快速操作")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 重新檢查", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("📦 安裝依賴", use_container_width=True):
            st.info("請在終端運行: python install_dependencies.py")
    
    with col3:
        if st.button("📚 查看指南", use_container_width=True):
            st.info("請查看docs/新手快速啟動指南.md")
