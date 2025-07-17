#!/usr/bin/env python3
"""
AI 交易系統 Web UI 後端整合模組

此模組提供 Web UI 與後端服務的統一整合接口，包括：
- 數據更新服務整合
- 核心功能模組連接
- 錯誤處理和用戶反饋
- 進度指示和狀態管理

Version: v1.0
Author: AI Trading System
"""

import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
import threading
import time

import streamlit as st
import pandas as pd
import numpy as np

# 設定日誌
logger = logging.getLogger(__name__)

class BackendIntegrationService:
    """後端整合服務類"""
    
    def __init__(self):
        """初始化後端整合服務"""
        self.services = {}
        self.data_sources = {}
        self.is_initialized = False
        self._initialize_services()
    
    def _initialize_services(self):
        """初始化所有後端服務"""
        try:
            # 初始化數據管理服務
            self._init_data_management_service()
            
            # 初始化回測服務
            self._init_backtest_service()
            
            # 初始化投資組合服務
            self._init_portfolio_service()
            
            # 初始化風險管理服務
            self._init_risk_management_service()
            
            # 初始化策略管理服務
            self._init_strategy_management_service()
            
            # 初始化 AI 模型服務
            self._init_ai_model_service()
            
            # 初始化系統監控服務
            self._init_system_monitoring_service()
            
            self.is_initialized = True
            logger.info("後端服務初始化完成")
            
        except Exception as e:
            logger.error(f"後端服務初始化失敗: {e}")
            self.is_initialized = False
    
    def _init_data_management_service(self):
        """初始化數據管理服務"""
        try:
            from src.core.data_management_service import DataManagementService
            from src.core.data_api import get_stock_data, update_data, get_market_info

            self.services['data_management'] = DataManagementService()
            self.services['data_api'] = {
                'get_stock_data': get_stock_data,
                'update_data': update_data,
                'get_market_info': get_market_info
            }
            logger.info("數據管理服務初始化成功")
        except ImportError as e:
            logger.warning(f"數據管理服務不可用，使用模擬服務: {e}")
            try:
                from src.ui.mock_backend_services import get_mock_service
                self.services['data_management'] = get_mock_service('data_management')
            except ImportError:
                logger.error("模擬服務也無法導入，使用基本模擬")
                self.services['data_management'] = self._create_basic_mock_service('data_management')
    
    def _init_backtest_service(self):
        """初始化回測服務"""
        try:
            from src.core.backtest_service import BacktestService
            from src.core.backtest.service import BacktestService as BacktestServiceV2

            # 嘗試使用新版本的回測服務
            try:
                self.services['backtest'] = BacktestServiceV2()
            except:
                self.services['backtest'] = BacktestService()

            logger.info("回測服務初始化成功")
        except ImportError as e:
            logger.warning(f"回測服務不可用，使用模擬服務: {e}")
            try:
                from src.ui.mock_backend_services import get_mock_service
                self.services['backtest'] = get_mock_service('backtest')
            except ImportError:
                logger.error("模擬服務也無法導入，使用基本模擬")
                self.services['backtest'] = self._create_basic_mock_service('backtest')
    
    def _init_portfolio_service(self):
        """初始化投資組合服務"""
        try:
            from src.core.portfolio_service import PortfolioService

            self.services['portfolio'] = PortfolioService()
            logger.info("投資組合服務初始化成功")
        except ImportError as e:
            logger.warning(f"投資組合服務不可用，使用模擬服務: {e}")
            try:
                from src.ui.mock_backend_services import get_mock_service
                self.services['portfolio'] = get_mock_service('portfolio')
            except ImportError:
                logger.error("模擬服務也無法導入，使用基本模擬")
                self.services['portfolio'] = self._create_basic_mock_service('portfolio')
    
    def _init_risk_management_service(self):
        """初始化風險管理服務"""
        try:
            from src.core.risk_management_service import RiskManagementService

            self.services['risk_management'] = RiskManagementService()
            logger.info("風險管理服務初始化成功")
        except ImportError as e:
            logger.warning(f"風險管理服務不可用，使用模擬服務: {e}")
            try:
                from src.ui.mock_backend_services import get_mock_service
                self.services['risk_management'] = get_mock_service('risk_management')
            except ImportError:
                logger.error("模擬服務也無法導入，使用基本模擬")
                self.services['risk_management'] = self._create_basic_mock_service('risk_management')
    
    def _init_strategy_management_service(self):
        """初始化策略管理服務"""
        try:
            from src.core.strategy_management_service import StrategyManagementService

            self.services['strategy_management'] = StrategyManagementService()
            logger.info("策略管理服務初始化成功")
        except ImportError as e:
            logger.warning(f"策略管理服務不可用，使用模擬服務: {e}")
            try:
                from src.ui.mock_backend_services import get_mock_service
                self.services['strategy_management'] = get_mock_service('strategy_management')
            except ImportError:
                logger.error("模擬服務也無法導入，使用基本模擬")
                self.services['strategy_management'] = self._create_basic_mock_service('strategy_management')

    def _init_ai_model_service(self):
        """初始化 AI 模型服務"""
        try:
            from src.core.ai_model_management_service import AIModelManagementService

            self.services['ai_model'] = AIModelManagementService()
            logger.info("AI 模型服務初始化成功")
        except ImportError as e:
            logger.warning(f"AI 模型服務不可用，使用模擬服務: {e}")
            try:
                from src.ui.mock_backend_services import get_mock_service
                self.services['ai_model'] = get_mock_service('ai_model')
            except ImportError:
                logger.error("模擬服務也無法導入，使用基本模擬")
                self.services['ai_model'] = self._create_basic_mock_service('ai_model')

    def _init_system_monitoring_service(self):
        """初始化系統監控服務"""
        try:
            from src.core.system_monitoring_service import SystemMonitoringService

            self.services['system_monitoring'] = SystemMonitoringService()
            logger.info("系統監控服務初始化成功")
        except ImportError as e:
            logger.warning(f"系統監控服務不可用，使用模擬服務: {e}")
            try:
                from src.ui.mock_backend_services import get_mock_service
                self.services['system_monitoring'] = get_mock_service('system_monitoring')
            except ImportError:
                logger.error("模擬服務也無法導入，使用基本模擬")
                self.services['system_monitoring'] = self._create_basic_mock_service('system_monitoring')

    def _create_basic_mock_service(self, service_name: str):
        """創建基本模擬服務"""
        class BasicMockService:
            def __init__(self, name):
                self.name = name

            def __getattr__(self, item):
                def mock_method(*args, **kwargs):
                    logger.info(f"調用模擬服務 {self.name}.{item}")
                    return {"status": "success", "message": f"模擬 {item} 完成", "data": {}}
                return mock_method

        return BasicMockService(service_name)

    def get_service(self, service_name: str) -> Optional[Any]:
        """獲取指定的服務實例"""
        return self.services.get(service_name)
    
    def is_service_available(self, service_name: str) -> bool:
        """檢查服務是否可用"""
        return self.services.get(service_name) is not None
    
    def get_service_status(self) -> Dict[str, bool]:
        """獲取所有服務的狀態"""
        return {
            name: service is not None 
            for name, service in self.services.items()
        }


# 全局後端整合服務實例
_backend_service = None

def get_backend_service() -> BackendIntegrationService:
    """獲取後端整合服務實例（單例模式）"""
    global _backend_service
    if _backend_service is None:
        _backend_service = BackendIntegrationService()
    return _backend_service


def with_progress_indicator(func: Callable) -> Callable:
    """進度指示器裝飾器"""
    def wrapper(*args, **kwargs):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("正在處理...")
            progress_bar.progress(25)
            
            result = func(*args, **kwargs)
            
            progress_bar.progress(100)
            status_text.text("處理完成")
            
            # 清理進度指示器
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()
            
            return result
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"處理失敗: {str(e)}")
            logger.error(f"函數 {func.__name__} 執行失敗: {e}")
            return None
    
    return wrapper


def with_error_handling(func: Callable) -> Callable:
    """錯誤處理裝飾器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"操作失敗: {str(e)}"
            st.error(error_msg)
            logger.error(f"函數 {func.__name__} 執行失敗: {e}")
            logger.error(traceback.format_exc())
            return None
    
    return wrapper


def show_service_status():
    """顯示服務狀態"""
    backend = get_backend_service()
    
    if not backend.is_initialized:
        st.error("❌ 後端服務未初始化")
        return
    
    status = backend.get_service_status()
    
    st.markdown("### 🔧 服務狀態")
    
    col1, col2 = st.columns(2)
    
    with col1:
        for service_name, is_available in list(status.items())[:len(status)//2]:
            status_icon = "✅" if is_available else "❌"
            service_display_name = {
                'data_management': '數據管理',
                'backtest': '回測分析',
                'portfolio': '投資組合',
                'risk_management': '風險管理'
            }.get(service_name, service_name)
            
            st.write(f"{status_icon} {service_display_name}")
    
    with col2:
        for service_name, is_available in list(status.items())[len(status)//2:]:
            status_icon = "✅" if is_available else "❌"
            service_display_name = {
                'strategy_management': '策略管理',
                'ai_model': 'AI 模型',
                'system_monitoring': '系統監控',
                'data_api': '數據 API'
            }.get(service_name, service_name)
            
            st.write(f"{status_icon} {service_display_name}")


def execute_with_feedback(
    operation_name: str,
    operation_func: Callable,
    success_message: str = "操作成功完成",
    *args, **kwargs
) -> Any:
    """執行操作並提供用戶反饋"""
    
    # 顯示開始狀態
    with st.spinner(f"正在執行 {operation_name}..."):
        try:
            # 執行操作
            result = operation_func(*args, **kwargs)
            
            # 顯示成功消息
            st.success(success_message)
            
            return result
            
        except Exception as e:
            # 顯示錯誤消息
            st.error(f"{operation_name} 失敗: {str(e)}")
            logger.error(f"{operation_name} 執行失敗: {e}")
            logger.error(traceback.format_exc())
            
            return None


def safe_service_call(service_name: str, method_name: str, *args, **kwargs) -> Any:
    """安全的服務調用"""
    backend = get_backend_service()
    
    if not backend.is_service_available(service_name):
        st.warning(f"服務 {service_name} 不可用")
        return None
    
    service = backend.get_service(service_name)
    
    if not hasattr(service, method_name):
        st.error(f"服務 {service_name} 沒有方法 {method_name}")
        return None
    
    try:
        method = getattr(service, method_name)
        return method(*args, **kwargs)
    except Exception as e:
        st.error(f"調用 {service_name}.{method_name} 失敗: {str(e)}")
        logger.error(f"服務調用失敗: {service_name}.{method_name}, 錯誤: {e}")
        return None


# 常用的服務調用快捷函數
def update_market_data(data_types: List[str] = None) -> Dict[str, Any]:
    """更新市場數據"""
    if data_types is None:
        data_types = ["price", "bargin", "pe"]
    
    return execute_with_feedback(
        "市場數據更新",
        lambda: safe_service_call('data_api', 'update_data', data_types=data_types),
        "市場數據更新完成"
    )


def run_backtest(config: Dict[str, Any]) -> Dict[str, Any]:
    """執行回測"""
    return execute_with_feedback(
        "回測分析",
        lambda: safe_service_call('backtest', 'run_backtest', config),
        "回測分析完成"
    )


def get_portfolio_performance() -> Dict[str, Any]:
    """獲取投資組合績效"""
    return safe_service_call('portfolio', 'get_performance_metrics')


def get_risk_metrics() -> Dict[str, Any]:
    """獲取風險指標"""
    return safe_service_call('risk_management', 'calculate_risk_metrics')


def get_system_health() -> Dict[str, Any]:
    """獲取系統健康狀態"""
    return safe_service_call('system_monitoring', 'get_system_health')
