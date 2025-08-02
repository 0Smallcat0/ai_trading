#!/usr/bin/env python3
"""
AI交易系統基礎功能測試腳本

此腳本測試系統的基本功能，包括：
1. 模組導入測試
2. 核心組件可用性測試
3. 基本API端點測試
4. 數據庫連接測試
5. 配置文件驗證

執行方式：
    python test_system_basic.py
"""

import sys
import os
import time
import logging
from typing import Dict, List, Any
import traceback

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemBasicTester:
    """系統基礎功能測試器"""
    
    def __init__(self):
        self.test_results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
    def run_test(self, test_name: str, test_func):
        """執行單個測試"""
        self.total_tests += 1
        logger.info(f"執行測試: {test_name}")
        
        try:
            start_time = time.time()
            result = test_func()
            end_time = time.time()
            
            if result:
                self.passed_tests += 1
                status = "PASS"
                logger.info(f"✅ {test_name} - 通過 ({end_time - start_time:.2f}s)")
            else:
                self.failed_tests += 1
                status = "FAIL"
                logger.error(f"❌ {test_name} - 失敗")
                
            self.test_results[test_name] = {
                "status": status,
                "duration": end_time - start_time,
                "details": result if isinstance(result, dict) else {}
            }
            
        except Exception as e:
            self.failed_tests += 1
            self.test_results[test_name] = {
                "status": "ERROR",
                "duration": 0,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            logger.error(f"💥 {test_name} - 錯誤: {e}")
            
    def test_module_imports(self) -> bool:
        """測試核心模組導入"""
        try:
            # 測試UI組件導入
            from src.ui.components.auth_component import check_auth, show_login
            from src.ui.layouts.page_layout import setup_page_config, apply_responsive_design
            from src.ui.utils.page_renderer import render_page, show_default_dashboard
            
            # 測試核心服務導入
            from src.core.risk_management_service import RiskManagementService
            from src.core.ai_model_management_service import AIModelManagementService
            
            # 測試API導入
            from src.api.main import app
            
            logger.info("所有核心模組導入成功")
            return True
            
        except ImportError as e:
            logger.error(f"模組導入失敗: {e}")
            return False
            
    def test_streamlit_components(self) -> bool:
        """測試Streamlit組件"""
        try:
            import streamlit as st
            
            # 檢查Streamlit版本
            import streamlit
            version = streamlit.__version__
            logger.info(f"Streamlit版本: {version}")
            
            # 測試基本組件
            from src.ui.components.auth_component import check_auth
            auth_result = check_auth()
            logger.info(f"認證組件測試: {auth_result}")
            
            return True
            
        except Exception as e:
            logger.error(f"Streamlit組件測試失敗: {e}")
            return False
            
    def test_database_connections(self) -> bool:
        """測試數據庫連接"""
        try:
            # 檢查數據庫文件是否存在
            db_files = [
                "data/market_data.db",
                "data/portfolio.db",
                "data/strategies.db"
            ]
            
            existing_dbs = []
            for db_file in db_files:
                if os.path.exists(db_file):
                    existing_dbs.append(db_file)
                    logger.info(f"數據庫文件存在: {db_file}")
                else:
                    logger.warning(f"數據庫文件不存在: {db_file}")
                    
            return len(existing_dbs) > 0
            
        except Exception as e:
            logger.error(f"數據庫連接測試失敗: {e}")
            return False
            
    def test_config_files(self) -> bool:
        """測試配置文件"""
        try:
            config_files = [
                "pyproject.toml",
                "config/environment_config.py"
            ]
            
            existing_configs = []
            for config_file in config_files:
                if os.path.exists(config_file):
                    existing_configs.append(config_file)
                    logger.info(f"配置文件存在: {config_file}")
                else:
                    logger.warning(f"配置文件不存在: {config_file}")
                    
            return len(existing_configs) > 0
            
        except Exception as e:
            logger.error(f"配置文件測試失敗: {e}")
            return False
            
    def test_api_endpoints(self) -> bool:
        """測試API端點"""
        try:
            from src.api.main import app
            from fastapi.testclient import TestClient
            
            client = TestClient(app)
            
            # 測試健康檢查端點
            response = client.get("/health")
            if response.status_code == 200:
                logger.info("API健康檢查端點正常")
                return True
            else:
                logger.error(f"API健康檢查失敗: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"API端點測試失敗: {e}")
            return False
            
    def test_performance_metrics(self) -> Dict[str, Any]:
        """測試性能指標"""
        try:
            import psutil
            
            # 獲取系統資源使用情況
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metrics = {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_available": memory.available / (1024**3),  # GB
                "disk_usage": disk.percent,
                "disk_free": disk.free / (1024**3)  # GB
            }
            
            logger.info(f"系統性能指標: {metrics}")
            return metrics
            
        except Exception as e:
            logger.error(f"性能指標測試失敗: {e}")
            return {}
            
    def run_all_tests(self):
        """執行所有測試"""
        logger.info("開始執行AI交易系統基礎功能測試")
        logger.info("=" * 50)
        
        # 執行各項測試
        self.run_test("模組導入測試", self.test_module_imports)
        self.run_test("Streamlit組件測試", self.test_streamlit_components)
        self.run_test("數據庫連接測試", self.test_database_connections)
        self.run_test("配置文件測試", self.test_config_files)
        self.run_test("API端點測試", self.test_api_endpoints)
        
        # 性能測試
        performance_metrics = self.test_performance_metrics()
        if performance_metrics:
            self.test_results["性能指標"] = {
                "status": "INFO",
                "duration": 0,
                "metrics": performance_metrics
            }
        
        # 生成測試報告
        self.generate_report()
        
    def generate_report(self):
        """生成測試報告"""
        logger.info("=" * 50)
        logger.info("測試報告")
        logger.info("=" * 50)
        
        logger.info(f"總測試數: {self.total_tests}")
        logger.info(f"通過測試: {self.passed_tests}")
        logger.info(f"失敗測試: {self.failed_tests}")
        logger.info(f"成功率: {(self.passed_tests/self.total_tests)*100:.1f}%")
        
        logger.info("\n詳細結果:")
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "ℹ️"
            logger.info(f"{status_icon} {test_name}: {result['status']}")
            
            if "error" in result:
                logger.error(f"   錯誤: {result['error']}")
                
        # 保存報告到文件
        self.save_report_to_file()
        
    def save_report_to_file(self):
        """保存報告到文件"""
        try:
            import json
            from datetime import datetime
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_tests": self.total_tests,
                    "passed_tests": self.passed_tests,
                    "failed_tests": self.failed_tests,
                    "success_rate": (self.passed_tests/self.total_tests)*100 if self.total_tests > 0 else 0
                },
                "results": self.test_results
            }
            
            with open("test_results_basic.json", "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                
            logger.info("測試報告已保存到: test_results_basic.json")
            
        except Exception as e:
            logger.error(f"保存報告失敗: {e}")


if __name__ == "__main__":
    tester = SystemBasicTester()
    tester.run_all_tests()
