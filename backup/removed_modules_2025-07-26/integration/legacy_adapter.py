# -*- coding: utf-8 -*-
"""
原始項目適配器

此模組提供與原始 ai_quant_trade-0.0.1 項目的適配接口，
確保新功能能夠無縫整合到原始項目中，同時保持原始項目的完整性。

主要功能：
- 原始項目接口封裝
- 數據格式轉換
- API兼容性保證
- 配置管理適配
- 錯誤處理統一

適配策略：
- 保持原始項目完全不變
- 通過包裝器模式提供統一接口
- 實現雙向數據轉換
- 提供兼容性檢查
"""

import logging
import os
import sys
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import importlib.util
import json
import pickle

# 設定日誌
logger = logging.getLogger(__name__)


class LegacyProjectAdapter:
    """
    原始項目適配器
    
    提供與原始 ai_quant_trade-0.0.1 項目的適配接口
    """
    
    def __init__(self, config):
        """
        初始化原始項目適配器
        
        Args:
            config: 整合配置
        """
        self.config = config
        self.legacy_path = Path(config.legacy_project_path)
        
        # 原始項目組件
        self.legacy_modules = {}
        self.legacy_apis = {}
        
        # 適配器狀態
        self.initialized = False
        self.compatibility_checked = False
        
        # 數據轉換器
        self.data_converters = {}
        
        logger.info(f"原始項目適配器初始化: {self.legacy_path}")
    
    def initialize(self) -> bool:
        """
        初始化適配器
        
        Returns:
            是否初始化成功
        """
        try:
            # 檢查原始項目結構
            if not self._check_project_structure():
                return False
            
            # 加載原始項目模組
            if not self._load_legacy_modules():
                return False
            
            # 初始化API適配器
            if not self._initialize_api_adapters():
                return False
            
            # 設置數據轉換器
            self._setup_data_converters()
            
            # 兼容性檢查
            if not self._check_compatibility():
                logger.warning("兼容性檢查失敗，但繼續初始化")
            
            self.initialized = True
            logger.info("原始項目適配器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"原始項目適配器初始化失敗: {e}")
            return False
    
    def _check_project_structure(self) -> bool:
        """檢查原始項目結構"""
        try:
            if not self.legacy_path.exists():
                logger.error(f"原始項目路徑不存在: {self.legacy_path}")
                return False
            
            # 檢查關鍵目錄
            required_dirs = {
                'quant_brain': '核心量化邏輯',
                'tools': '工具函數',
                'docs': '文檔',
                'egs_data': '數據示例',
                'egs_trade': '交易示例'
            }
            
            missing_dirs = []
            for dir_name, description in required_dirs.items():
                dir_path = self.legacy_path / dir_name
                if not dir_path.exists():
                    missing_dirs.append(f"{dir_name} ({description})")
                    logger.warning(f"缺少目錄: {dir_path}")
            
            if missing_dirs:
                logger.warning(f"原始項目缺少以下目錄: {', '.join(missing_dirs)}")
            
            # 檢查關鍵文件
            key_files = [
                'quant_brain/__init__.py',
                'tools/__init__.py'
            ]
            
            for file_path in key_files:
                full_path = self.legacy_path / file_path
                if not full_path.exists():
                    logger.warning(f"關鍵文件不存在: {full_path}")
            
            logger.info("原始項目結構檢查完成")
            return True
            
        except Exception as e:
            logger.error(f"項目結構檢查失敗: {e}")
            return False
    
    def _load_legacy_modules(self) -> bool:
        """加載原始項目模組"""
        try:
            # 添加原始項目路徑到sys.path
            legacy_path_str = str(self.legacy_path.absolute())
            if legacy_path_str not in sys.path:
                sys.path.insert(0, legacy_path_str)
            
            # 嘗試導入核心模組
            core_modules = {
                'quant_brain': 'quant_brain',
                'tools': 'tools'
            }
            
            for module_name, import_path in core_modules.items():
                try:
                    module = importlib.import_module(import_path)
                    self.legacy_modules[module_name] = module
                    logger.info(f"成功加載原始模組: {module_name}")
                except ImportError as e:
                    logger.warning(f"無法加載原始模組 {module_name}: {e}")
            
            # 嘗試加載子模組
            sub_modules = {
                'data_io': 'quant_brain.data_io',
                'portfolio': 'quant_brain.portfolio',
                'back_test': 'quant_brain.back_test',
                'rules': 'quant_brain.rules'
            }
            
            for module_name, import_path in sub_modules.items():
                try:
                    module = importlib.import_module(import_path)
                    self.legacy_modules[module_name] = module
                    logger.info(f"成功加載子模組: {module_name}")
                except ImportError as e:
                    logger.debug(f"子模組加載失敗 {module_name}: {e}")
            
            logger.info(f"已加載 {len(self.legacy_modules)} 個原始項目模組")
            return True
            
        except Exception as e:
            logger.error(f"原始項目模組加載失敗: {e}")
            return False
    
    def _initialize_api_adapters(self) -> bool:
        """初始化API適配器"""
        try:
            # 數據IO適配器
            if 'data_io' in self.legacy_modules:
                self.legacy_apis['data_io'] = DataIOAdapter(self.legacy_modules['data_io'])
            
            # 投資組合適配器
            if 'portfolio' in self.legacy_modules:
                self.legacy_apis['portfolio'] = PortfolioAdapter(self.legacy_modules['portfolio'])
            
            # 回測適配器
            if 'back_test' in self.legacy_modules:
                self.legacy_apis['back_test'] = BackTestAdapter(self.legacy_modules['back_test'])
            
            # 規則適配器
            if 'rules' in self.legacy_modules:
                self.legacy_apis['rules'] = RulesAdapter(self.legacy_modules['rules'])
            
            logger.info(f"已初始化 {len(self.legacy_apis)} 個API適配器")
            return True
            
        except Exception as e:
            logger.error(f"API適配器初始化失敗: {e}")
            return False
    
    def _setup_data_converters(self):
        """設置數據轉換器"""
        try:
            # 價格數據轉換器
            self.data_converters['price_data'] = PriceDataConverter()
            
            # 投資組合數據轉換器
            self.data_converters['portfolio_data'] = PortfolioDataConverter()
            
            # 策略數據轉換器
            self.data_converters['strategy_data'] = StrategyDataConverter()
            
            # 回測結果轉換器
            self.data_converters['backtest_result'] = BacktestResultConverter()
            
            logger.info("數據轉換器設置完成")
            
        except Exception as e:
            logger.error(f"數據轉換器設置失敗: {e}")
    
    def _check_compatibility(self) -> bool:
        """檢查兼容性"""
        try:
            compatibility_issues = []
            
            # 檢查Python版本
            python_version = sys.version_info
            if python_version < (3, 7):
                compatibility_issues.append(f"Python版本過低: {python_version}")
            
            # 檢查必需的依賴
            required_packages = ['pandas', 'numpy', 'matplotlib']
            for package in required_packages:
                try:
                    importlib.import_module(package)
                except ImportError:
                    compatibility_issues.append(f"缺少必需包: {package}")
            
            # 檢查原始項目API
            if 'quant_brain' in self.legacy_modules:
                brain_module = self.legacy_modules['quant_brain']
                if not hasattr(brain_module, '__version__'):
                    compatibility_issues.append("原始項目缺少版本信息")
            
            if compatibility_issues:
                logger.warning(f"發現兼容性問題: {compatibility_issues}")
                self.compatibility_checked = False
                return False
            else:
                logger.info("兼容性檢查通過")
                self.compatibility_checked = True
                return True
                
        except Exception as e:
            logger.error(f"兼容性檢查失敗: {e}")
            return False
    
    def get_legacy_module(self, module_name: str) -> Optional[Any]:
        """獲取原始項目模組"""
        return self.legacy_modules.get(module_name)
    
    def get_legacy_api(self, api_name: str) -> Optional[Any]:
        """獲取原始項目API適配器"""
        return self.legacy_apis.get(api_name)
    
    def convert_data(self, data_type: str, data: Any, direction: str = 'to_legacy') -> Any:
        """
        轉換數據格式
        
        Args:
            data_type: 數據類型
            data: 要轉換的數據
            direction: 轉換方向 ('to_legacy' 或 'from_legacy')
            
        Returns:
            轉換後的數據
        """
        try:
            if data_type not in self.data_converters:
                logger.warning(f"未找到數據轉換器: {data_type}")
                return data
            
            converter = self.data_converters[data_type]
            
            if direction == 'to_legacy':
                return converter.to_legacy_format(data)
            elif direction == 'from_legacy':
                return converter.from_legacy_format(data)
            else:
                logger.error(f"無效的轉換方向: {direction}")
                return data
                
        except Exception as e:
            logger.error(f"數據轉換失敗: {e}")
            return data
    
    def is_compatible(self) -> bool:
        """檢查是否兼容"""
        return self.compatibility_checked
    
    def get_project_info(self) -> Dict[str, Any]:
        """獲取原始項目信息"""
        try:
            info = {
                'path': str(self.legacy_path),
                'modules_loaded': len(self.legacy_modules),
                'apis_available': len(self.legacy_apis),
                'compatible': self.compatibility_checked,
                'initialized': self.initialized
            }
            
            # 添加模組信息
            info['available_modules'] = list(self.legacy_modules.keys())
            info['available_apis'] = list(self.legacy_apis.keys())
            
            return info
            
        except Exception as e:
            logger.error(f"獲取項目信息失敗: {e}")
            return {}


# 數據轉換器基類
class BaseDataConverter:
    """數據轉換器基類"""
    
    def to_legacy_format(self, data: Any) -> Any:
        """轉換為原始項目格式"""
        return data
    
    def from_legacy_format(self, data: Any) -> Any:
        """從原始項目格式轉換"""
        return data


class PriceDataConverter(BaseDataConverter):
    """價格數據轉換器"""
    
    def to_legacy_format(self, data: Any) -> Any:
        """轉換為原始項目的價格數據格式"""
        # 實現具體的轉換邏輯
        return data
    
    def from_legacy_format(self, data: Any) -> Any:
        """從原始項目格式轉換價格數據"""
        # 實現具體的轉換邏輯
        return data


class PortfolioDataConverter(BaseDataConverter):
    """投資組合數據轉換器"""
    pass


class StrategyDataConverter(BaseDataConverter):
    """策略數據轉換器"""
    pass


class BacktestResultConverter(BaseDataConverter):
    """回測結果轉換器"""
    pass


# API適配器基類
class BaseAPIAdapter:
    """API適配器基類"""
    
    def __init__(self, legacy_module):
        self.legacy_module = legacy_module


class DataIOAdapter(BaseAPIAdapter):
    """數據IO適配器"""
    
    def get_data(self, symbol: str, start_date: str, end_date: str) -> Any:
        """獲取數據的統一接口"""
        try:
            # 調用原始項目的數據獲取方法
            if hasattr(self.legacy_module, 'get_stock_data'):
                return self.legacy_module.get_stock_data(symbol, start_date, end_date)
            else:
                logger.warning("原始項目缺少get_stock_data方法")
                return None
        except Exception as e:
            logger.error(f"數據獲取失敗: {e}")
            return None


class PortfolioAdapter(BaseAPIAdapter):
    """投資組合適配器"""
    
    def get_portfolio_value(self) -> float:
        """獲取投資組合價值"""
        try:
            if hasattr(self.legacy_module, 'get_total_value'):
                return self.legacy_module.get_total_value()
            else:
                logger.warning("原始項目缺少get_total_value方法")
                return 0.0
        except Exception as e:
            logger.error(f"獲取投資組合價值失敗: {e}")
            return 0.0


class BackTestAdapter(BaseAPIAdapter):
    """回測適配器"""
    
    def run_backtest(self, strategy, start_date: str, end_date: str) -> Any:
        """運行回測"""
        try:
            if hasattr(self.legacy_module, 'run_backtest'):
                return self.legacy_module.run_backtest(strategy, start_date, end_date)
            else:
                logger.warning("原始項目缺少run_backtest方法")
                return None
        except Exception as e:
            logger.error(f"回測運行失敗: {e}")
            return None


class RulesAdapter(BaseAPIAdapter):
    """規則適配器"""
    
    def add_rule(self, rule) -> bool:
        """添加交易規則"""
        try:
            if hasattr(self.legacy_module, 'add_rule'):
                return self.legacy_module.add_rule(rule)
            else:
                logger.warning("原始項目缺少add_rule方法")
                return False
        except Exception as e:
            logger.error(f"添加規則失敗: {e}")
            return False
