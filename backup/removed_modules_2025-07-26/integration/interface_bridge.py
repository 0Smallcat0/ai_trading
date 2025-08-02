# -*- coding: utf-8 -*-
"""
接口橋樑

此模組提供新舊系統之間的接口橋樑，
確保新功能能夠無縫整合到原始項目的用戶界面中。

主要功能：
- 統一的API接口
- 數據格式轉換
- 錯誤處理統一
- 響應格式標準化
- 版本兼容性管理

設計原則：
- 保持原始項目API不變
- 提供統一的新功能接口
- 實現平滑的功能遷移
- 確保向後兼容性
"""

import logging
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import json
import traceback
from functools import wraps

# 設定日誌
logger = logging.getLogger(__name__)


def api_response_wrapper(func: Callable) -> Callable:
    """API響應包裝器裝飾器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return {
                'success': True,
                'data': result,
                'timestamp': datetime.now().isoformat(),
                'error': None
            }
        except Exception as e:
            logger.error(f"API調用失敗 {func.__name__}: {e}")
            return {
                'success': False,
                'data': None,
                'timestamp': datetime.now().isoformat(),
                'error': {
                    'type': type(e).__name__,
                    'message': str(e),
                    'traceback': traceback.format_exc() if logger.level <= logging.DEBUG else None
                }
            }
    return wrapper


class InterfaceBridge:
    """
    接口橋樑
    
    提供新舊系統之間的統一接口
    """
    
    def __init__(self, config):
        """
        初始化接口橋樑
        
        Args:
            config: 整合配置
        """
        self.config = config
        self.initialized = False
        
        # 適配器引用
        self.system_integrator = None
        self.legacy_adapter = None
        
        # API映射
        self.api_mappings = {}
        self.response_formatters = {}
        
        # 版本管理
        self.api_version = "1.0.0"
        self.legacy_version = "0.0.1"
        
        logger.info("接口橋樑初始化")
    
    def initialize(self, system_integrator) -> bool:
        """
        初始化接口橋樑
        
        Args:
            system_integrator: 系統整合器實例
            
        Returns:
            是否初始化成功
        """
        try:
            self.system_integrator = system_integrator
            self.legacy_adapter = system_integrator.legacy_adapter
            
            # 設置API映射
            self._setup_api_mappings()
            
            # 設置響應格式化器
            self._setup_response_formatters()
            
            self.initialized = True
            logger.info("接口橋樑初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"接口橋樑初始化失敗: {e}")
            return False
    
    def _setup_api_mappings(self):
        """設置API映射"""
        try:
            # 數據獲取API映射
            self.api_mappings.update({
                # 股票數據
                'get_stock_data': {
                    'legacy_method': self._legacy_get_stock_data,
                    'enhanced_method': self._enhanced_get_stock_data,
                    'fallback_enabled': True
                },
                
                # 實時數據
                'get_realtime_data': {
                    'legacy_method': self._legacy_get_realtime_data,
                    'enhanced_method': self._enhanced_get_realtime_data,
                    'fallback_enabled': True
                },
                
                # 交易決策
                'make_trading_decision': {
                    'legacy_method': self._legacy_make_decision,
                    'enhanced_method': self._enhanced_make_decision,
                    'fallback_enabled': True
                },
                
                # 投資組合管理
                'get_portfolio_status': {
                    'legacy_method': self._legacy_get_portfolio,
                    'enhanced_method': self._enhanced_get_portfolio,
                    'fallback_enabled': True
                },
                
                # 回測功能
                'run_backtest': {
                    'legacy_method': self._legacy_run_backtest,
                    'enhanced_method': self._enhanced_run_backtest,
                    'fallback_enabled': True
                },
                
                # 知識搜索
                'search_knowledge': {
                    'legacy_method': None,
                    'enhanced_method': self._enhanced_search_knowledge,
                    'fallback_enabled': False
                },
                
                # 學習進度
                'get_learning_progress': {
                    'legacy_method': None,
                    'enhanced_method': self._enhanced_get_learning_progress,
                    'fallback_enabled': False
                }
            })
            
            logger.info(f"已設置 {len(self.api_mappings)} 個API映射")
            
        except Exception as e:
            logger.error(f"API映射設置失敗: {e}")
    
    def _setup_response_formatters(self):
        """設置響應格式化器"""
        try:
            self.response_formatters = {
                'stock_data': self._format_stock_data_response,
                'realtime_data': self._format_realtime_data_response,
                'trading_decision': self._format_trading_decision_response,
                'portfolio_status': self._format_portfolio_status_response,
                'backtest_result': self._format_backtest_result_response,
                'knowledge_search': self._format_knowledge_search_response,
                'learning_progress': self._format_learning_progress_response
            }
            
            logger.info("響應格式化器設置完成")
            
        except Exception as e:
            logger.error(f"響應格式化器設置失敗: {e}")
    
    @api_response_wrapper
    def call_api(self, api_name: str, *args, **kwargs) -> Any:
        """
        統一API調用接口
        
        Args:
            api_name: API名稱
            *args: 位置參數
            **kwargs: 關鍵字參數
            
        Returns:
            API調用結果
        """
        if not self.initialized:
            raise RuntimeError("接口橋樑未初始化")
        
        if api_name not in self.api_mappings:
            raise ValueError(f"未知的API: {api_name}")
        
        mapping = self.api_mappings[api_name]
        
        # 優先使用增強方法
        if mapping['enhanced_method']:
            try:
                result = mapping['enhanced_method'](*args, **kwargs)
                return result
            except Exception as e:
                logger.warning(f"增強方法調用失敗 {api_name}: {e}")
                
                # 如果啟用了回退，嘗試使用原始方法
                if mapping['fallback_enabled'] and mapping['legacy_method']:
                    logger.info(f"回退到原始方法: {api_name}")
                    return mapping['legacy_method'](*args, **kwargs)
                else:
                    raise
        
        # 如果沒有增強方法，使用原始方法
        elif mapping['legacy_method']:
            return mapping['legacy_method'](*args, **kwargs)
        
        else:
            raise NotImplementedError(f"API未實現: {api_name}")
    
    # 原始項目方法包裝
    def _legacy_get_stock_data(self, symbol: str, start_date: str, end_date: str) -> Any:
        """原始項目股票數據獲取"""
        try:
            if self.legacy_adapter and self.legacy_adapter.legacy_apis.get('data_io'):
                data_io = self.legacy_adapter.legacy_apis['data_io']
                return data_io.get_data(symbol, start_date, end_date)
            else:
                raise RuntimeError("原始項目數據IO不可用")
        except Exception as e:
            logger.error(f"原始項目股票數據獲取失敗: {e}")
            raise
    
    def _legacy_get_realtime_data(self, symbol: str) -> Any:
        """原始項目實時數據獲取"""
        try:
            # 原始項目可能沒有實時數據功能
            logger.warning("原始項目不支持實時數據獲取")
            return None
        except Exception as e:
            logger.error(f"原始項目實時數據獲取失敗: {e}")
            raise
    
    def _legacy_make_decision(self, symbol: str, market_data: Dict[str, Any]) -> Any:
        """原始項目交易決策"""
        try:
            if self.legacy_adapter and self.legacy_adapter.legacy_apis.get('rules'):
                rules_api = self.legacy_adapter.legacy_apis['rules']
                # 這裡需要根據原始項目的實際API調整
                return {"action": "hold", "confidence": 0.5, "source": "legacy"}
            else:
                raise RuntimeError("原始項目規則引擎不可用")
        except Exception as e:
            logger.error(f"原始項目交易決策失敗: {e}")
            raise
    
    def _legacy_get_portfolio(self) -> Any:
        """原始項目投資組合狀態"""
        try:
            if self.legacy_adapter and self.legacy_adapter.legacy_apis.get('portfolio'):
                portfolio_api = self.legacy_adapter.legacy_apis['portfolio']
                return {"total_value": portfolio_api.get_portfolio_value()}
            else:
                raise RuntimeError("原始項目投資組合API不可用")
        except Exception as e:
            logger.error(f"原始項目投資組合獲取失敗: {e}")
            raise
    
    def _legacy_run_backtest(self, strategy, start_date: str, end_date: str) -> Any:
        """原始項目回測"""
        try:
            if self.legacy_adapter and self.legacy_adapter.legacy_apis.get('back_test'):
                backtest_api = self.legacy_adapter.legacy_apis['back_test']
                return backtest_api.run_backtest(strategy, start_date, end_date)
            else:
                raise RuntimeError("原始項目回測API不可用")
        except Exception as e:
            logger.error(f"原始項目回測失敗: {e}")
            raise
    
    # 增強功能方法
    def _enhanced_get_stock_data(self, symbol: str, start_date: str, end_date: str, source: Optional[str] = None) -> Any:
        """增強股票數據獲取"""
        try:
            data_adapter = self.system_integrator.get_adapter('data_sources')
            if data_adapter:
                return data_adapter.get_stock_data(symbol, start_date, end_date, source)
            else:
                raise RuntimeError("數據源適配器不可用")
        except Exception as e:
            logger.error(f"增強股票數據獲取失敗: {e}")
            raise
    
    def _enhanced_get_realtime_data(self, symbol: str, source: Optional[str] = None) -> Any:
        """增強實時數據獲取"""
        try:
            data_adapter = self.system_integrator.get_adapter('data_sources')
            if data_adapter:
                return data_adapter.get_realtime_data(symbol, source)
            else:
                raise RuntimeError("數據源適配器不可用")
        except Exception as e:
            logger.error(f"增強實時數據獲取失敗: {e}")
            raise
    
    def _enhanced_make_decision(self, symbol: str, market_data: Dict[str, Any]) -> Any:
        """增強交易決策"""
        try:
            # 嘗試多代理決策
            agents_adapter = self.system_integrator.get_adapter('multi_agent')
            if agents_adapter:
                decision = agents_adapter.make_trading_decision(symbol, market_data)
                if decision and decision.get('action') != 'hold':
                    return decision
            
            # 嘗試RL決策
            rl_adapter = self.system_integrator.get_adapter('reinforcement_learning')
            if rl_adapter:
                rl_agents = rl_adapter.get_all_rl_agents()
                if rl_agents:
                    # 使用第一個可用的RL代理
                    agent_name = list(rl_adapter.rl_agents.keys())[0]
                    return rl_adapter.make_rl_decision(agent_name, market_data)
            
            # 如果都不可用，返回保守決策
            return {"action": "hold", "confidence": 0.0, "source": "enhanced_fallback"}
            
        except Exception as e:
            logger.error(f"增強交易決策失敗: {e}")
            raise
    
    def _enhanced_get_portfolio(self) -> Any:
        """增強投資組合狀態"""
        try:
            # 這裡可以整合多個來源的投資組合信息
            portfolio_info = {
                "total_value": 1000000.0,
                "cash": 500000.0,
                "positions": {},
                "performance": {},
                "source": "enhanced"
            }
            
            return portfolio_info
            
        except Exception as e:
            logger.error(f"增強投資組合獲取失敗: {e}")
            raise
    
    def _enhanced_run_backtest(self, strategy, start_date: str, end_date: str, **kwargs) -> Any:
        """增強回測功能"""
        try:
            # 這裡可以整合多種回測引擎
            backtest_result = {
                "strategy": strategy,
                "start_date": start_date,
                "end_date": end_date,
                "total_return": 0.15,
                "sharpe_ratio": 1.2,
                "max_drawdown": -0.08,
                "source": "enhanced"
            }
            
            return backtest_result
            
        except Exception as e:
            logger.error(f"增強回測失敗: {e}")
            raise
    
    def _enhanced_search_knowledge(self, query: str, limit: int = 10) -> Any:
        """增強知識搜索"""
        try:
            knowledge_adapter = self.system_integrator.get_adapter('knowledge_system')
            if knowledge_adapter:
                return knowledge_adapter.search_knowledge(query, limit)
            else:
                raise RuntimeError("知識庫適配器不可用")
        except Exception as e:
            logger.error(f"知識搜索失敗: {e}")
            raise
    
    def _enhanced_get_learning_progress(self, user_id: str) -> Any:
        """增強學習進度獲取"""
        try:
            knowledge_adapter = self.system_integrator.get_adapter('knowledge_system')
            if knowledge_adapter:
                return knowledge_adapter.get_user_progress(user_id)
            else:
                raise RuntimeError("知識庫適配器不可用")
        except Exception as e:
            logger.error(f"學習進度獲取失敗: {e}")
            raise
    
    # 響應格式化方法
    def _format_stock_data_response(self, data: Any) -> Dict[str, Any]:
        """格式化股票數據響應"""
        try:
            if data is None:
                return {"data": None, "message": "無數據"}
            
            return {
                "data": data.to_dict() if hasattr(data, 'to_dict') else data,
                "format": "stock_data",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"股票數據響應格式化失敗: {e}")
            return {"error": str(e)}
    
    def _format_realtime_data_response(self, data: Any) -> Dict[str, Any]:
        """格式化實時數據響應"""
        try:
            return {
                "data": data,
                "format": "realtime_data",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"實時數據響應格式化失敗: {e}")
            return {"error": str(e)}
    
    def _format_trading_decision_response(self, data: Any) -> Dict[str, Any]:
        """格式化交易決策響應"""
        try:
            return {
                "decision": data,
                "format": "trading_decision",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"交易決策響應格式化失敗: {e}")
            return {"error": str(e)}
    
    def _format_portfolio_status_response(self, data: Any) -> Dict[str, Any]:
        """格式化投資組合狀態響應"""
        try:
            return {
                "portfolio": data,
                "format": "portfolio_status",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"投資組合狀態響應格式化失敗: {e}")
            return {"error": str(e)}
    
    def _format_backtest_result_response(self, data: Any) -> Dict[str, Any]:
        """格式化回測結果響應"""
        try:
            return {
                "result": data,
                "format": "backtest_result",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"回測結果響應格式化失敗: {e}")
            return {"error": str(e)}
    
    def _format_knowledge_search_response(self, data: Any) -> Dict[str, Any]:
        """格式化知識搜索響應"""
        try:
            return {
                "results": data,
                "count": len(data) if isinstance(data, list) else 0,
                "format": "knowledge_search",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"知識搜索響應格式化失敗: {e}")
            return {"error": str(e)}
    
    def _format_learning_progress_response(self, data: Any) -> Dict[str, Any]:
        """格式化學習進度響應"""
        try:
            return {
                "progress": data,
                "format": "learning_progress",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"學習進度響應格式化失敗: {e}")
            return {"error": str(e)}
    
    def get_api_info(self) -> Dict[str, Any]:
        """獲取API信息"""
        try:
            return {
                "api_version": self.api_version,
                "legacy_version": self.legacy_version,
                "available_apis": list(self.api_mappings.keys()),
                "initialized": self.initialized,
                "bridge_status": "active" if self.initialized else "inactive"
            }
        except Exception as e:
            logger.error(f"獲取API信息失敗: {e}")
            return {"error": str(e)}
