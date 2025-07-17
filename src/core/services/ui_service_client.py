"""
UI 服務客戶端模組

為 UI 層提供統一的服務訪問接口，簡化服務調用。
"""

import logging
from typing import Optional, Dict, Any, List

from .service_manager import ServiceManager
from .base_service import BaseService


class UIServiceClient:
    """UI 服務客戶端
    
    為 UI 層提供簡化的服務訪問接口，隱藏服務管理的複雜性。
    
    Attributes:
        service_manager: 服務管理器
        logger: 日誌記錄器
    """
    
    def __init__(self, service_manager: Optional[ServiceManager] = None):
        """初始化 UI 服務客戶端
        
        Args:
            service_manager: 服務管理器實例（可選）
        """
        self.service_manager = service_manager or ServiceManager()
        self.logger = logging.getLogger("ui.service_client")
        
        self.logger.info("UI 服務客戶端已初始化")
    
    # 認證服務
    def get_auth_service(self):
        """獲取認證服務
        
        Returns:
            認證服務實例
        """
        return self.service_manager.get_service("AuthenticationService")
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """用戶認證
        
        Args:
            username: 用戶名
            password: 密碼
            
        Returns:
            bool: 認證是否成功
        """
        auth_service = self.get_auth_service()
        if auth_service:
            return auth_service.authenticate(username, password)
        return False
    
    def is_user_authenticated(self, username: str) -> bool:
        """檢查用戶是否已認證
        
        Args:
            username: 用戶名
            
        Returns:
            bool: 是否已認證
        """
        auth_service = self.get_auth_service()
        if auth_service:
            return auth_service.is_authenticated(username)
        return False
    
    # 回測服務
    def get_backtest_service(self):
        """獲取回測服務
        
        Returns:
            回測服務實例
        """
        return self.service_manager.get_service("BacktestService")
    
    def start_backtest(self, config: Dict[str, Any]) -> Optional[str]:
        """啟動回測
        
        Args:
            config: 回測配置
            
        Returns:
            Optional[str]: 回測ID
        """
        backtest_service = self.get_backtest_service()
        if backtest_service:
            try:
                from ..backtest import BacktestConfig
                backtest_config = BacktestConfig(**config)
                return backtest_service.start_backtest(backtest_config)
            except Exception as e:
                self.logger.error(f"啟動回測失敗: {e}")
        return None
    
    def get_backtest_status(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """獲取回測狀態
        
        Args:
            backtest_id: 回測ID
            
        Returns:
            Optional[Dict[str, Any]]: 回測狀態
        """
        backtest_service = self.get_backtest_service()
        if backtest_service:
            try:
                return backtest_service.get_backtest_status(backtest_id)
            except Exception as e:
                self.logger.error(f"獲取回測狀態失敗: {e}")
        return None
    
    def get_backtest_results(self, backtest_id: str) -> Optional[Dict[str, Any]]:
        """獲取回測結果
        
        Args:
            backtest_id: 回測ID
            
        Returns:
            Optional[Dict[str, Any]]: 回測結果
        """
        backtest_service = self.get_backtest_service()
        if backtest_service:
            try:
                return backtest_service.get_backtest_results(backtest_id)
            except Exception as e:
                self.logger.error(f"獲取回測結果失敗: {e}")
        return None
    
    def list_backtests(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出回測任務
        
        Args:
            status: 過濾狀態
            
        Returns:
            List[Dict[str, Any]]: 回測任務列表
        """
        backtest_service = self.get_backtest_service()
        if backtest_service:
            try:
                return backtest_service.list_backtests(status)
            except Exception as e:
                self.logger.error(f"列出回測任務失敗: {e}")
        return []
    
    # 交易服務
    def get_trading_service(self):
        """獲取交易服務
        
        Returns:
            交易服務實例
        """
        return self.service_manager.get_service("TradingService")
    
    def place_order(self, order_data: Dict[str, Any]) -> Optional[str]:
        """下單
        
        Args:
            order_data: 訂單數據
            
        Returns:
            Optional[str]: 訂單ID
        """
        trading_service = self.get_trading_service()
        if trading_service:
            try:
                return trading_service.place_order(order_data)
            except Exception as e:
                self.logger.error(f"下單失敗: {e}")
        return None
    
    def get_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """獲取訂單列表
        
        Args:
            status: 訂單狀態過濾
            
        Returns:
            List[Dict[str, Any]]: 訂單列表
        """
        trading_service = self.get_trading_service()
        if trading_service:
            try:
                return trading_service.get_orders(status)
            except Exception as e:
                self.logger.error(f"獲取訂單失敗: {e}")
        return []
    
    # 風險管理服務
    def get_risk_service(self):
        """獲取風險管理服務
        
        Returns:
            風險管理服務實例
        """
        return self.service_manager.get_service("RiskManagementService")
    
    def get_risk_metrics(self) -> Optional[Dict[str, Any]]:
        """獲取風險指標
        
        Returns:
            Optional[Dict[str, Any]]: 風險指標
        """
        risk_service = self.get_risk_service()
        if risk_service:
            try:
                return risk_service.get_risk_metrics()
            except Exception as e:
                self.logger.error(f"獲取風險指標失敗: {e}")
        return None
    
    def check_position_risk(self, position_data: Dict[str, Any]) -> bool:
        """檢查倉位風險
        
        Args:
            position_data: 倉位數據
            
        Returns:
            bool: 風險檢查結果
        """
        risk_service = self.get_risk_service()
        if risk_service:
            try:
                return risk_service.check_position_risk(position_data)
            except Exception as e:
                self.logger.error(f"檢查倉位風險失敗: {e}")
        return False
    
    # 投資組合服務
    def get_portfolio_service(self):
        """獲取投資組合服務
        
        Returns:
            投資組合服務實例
        """
        return self.service_manager.get_service("PortfolioService")
    
    def get_portfolio_summary(self) -> Optional[Dict[str, Any]]:
        """獲取投資組合摘要
        
        Returns:
            Optional[Dict[str, Any]]: 投資組合摘要
        """
        portfolio_service = self.get_portfolio_service()
        if portfolio_service:
            try:
                return portfolio_service.get_portfolio_summary()
            except Exception as e:
                self.logger.error(f"獲取投資組合摘要失敗: {e}")
        return None
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """獲取持倉列表
        
        Returns:
            List[Dict[str, Any]]: 持倉列表
        """
        portfolio_service = self.get_portfolio_service()
        if portfolio_service:
            try:
                return portfolio_service.get_positions()
            except Exception as e:
                self.logger.error(f"獲取持倉列表失敗: {e}")
        return []
    
    # 數據服務
    def get_data_service(self):
        """獲取數據服務
        
        Returns:
            數據服務實例
        """
        return self.service_manager.get_service("DataService")
    
    def get_market_data(self, symbols: List[str], start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """獲取市場數據
        
        Args:
            symbols: 股票代碼列表
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            Optional[Dict[str, Any]]: 市場數據
        """
        data_service = self.get_data_service()
        if data_service:
            try:
                return data_service.get_market_data(symbols, start_date, end_date)
            except Exception as e:
                self.logger.error(f"獲取市場數據失敗: {e}")
        return None
    
    # 系統服務
    def get_system_status(self) -> Dict[str, Any]:
        """獲取系統狀態
        
        Returns:
            Dict[str, Any]: 系統狀態
        """
        return self.service_manager.get_system_status()
    
    def get_service_health(self, service_name: str) -> Optional[Dict[str, Any]]:
        """獲取服務健康狀態
        
        Args:
            service_name: 服務名稱
            
        Returns:
            Optional[Dict[str, Any]]: 服務健康狀態
        """
        return self.service_manager.get_service_health(service_name)
    
    def list_available_services(self) -> List[str]:
        """列出可用服務
        
        Returns:
            List[str]: 可用服務列表
        """
        return self.service_manager.list_services()
    
    def restart_service(self, service_name: str) -> bool:
        """重啟服務
        
        Args:
            service_name: 服務名稱
            
        Returns:
            bool: 是否成功重啟
        """
        return self.service_manager.restart_service(service_name)
    
    # 便利方法
    def is_service_available(self, service_name: str) -> bool:
        """檢查服務是否可用
        
        Args:
            service_name: 服務名稱
            
        Returns:
            bool: 服務是否可用
        """
        service = self.service_manager.get_service(service_name)
        return service is not None and service.is_healthy()
    
    def get_available_features(self) -> Dict[str, bool]:
        """獲取可用功能列表
        
        Returns:
            Dict[str, bool]: 功能可用性字典
        """
        return {
            "authentication": self.is_service_available("AuthenticationService"),
            "backtest": self.is_service_available("BacktestService"),
            "trading": self.is_service_available("TradingService"),
            "risk_management": self.is_service_available("RiskManagementService"),
            "portfolio": self.is_service_available("PortfolioService"),
            "data": self.is_service_available("DataService"),
        }
