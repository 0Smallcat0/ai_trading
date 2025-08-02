#!/usr/bin/env python3
"""
AI 交易系統模擬後端服務

服務管理器職責分工：
- ServiceManager: 通用服務管理器 (src/core/services/service_manager.py)
- PortfolioService: 投資組合服務管理 (src/services/portfolio_service/__init__.py)
- MockBackendServices: 模擬後端服務管理 (本檔案)
詳見：docs/開發者指南/服務管理器使用指南.md

當實際後端服務不可用時，提供模擬的服務響應，確保 UI 功能正常運行。

Version: v1.0
Author: AI Trading System
"""

import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class MockDataManagementService:
    """模擬數據管理服務"""
    
    def __init__(self):
        self.last_update = datetime.now() - timedelta(hours=1)
    
    def update_data(self, data_types: List[str] = None) -> Dict[str, Any]:
        """模擬數據更新"""
        time.sleep(2)  # 模擬處理時間
        
        self.last_update = datetime.now()
        
        return {
            "success": True,
            "updated_types": data_types or ["price", "bargin", "pe"],
            "update_time": self.last_update,
            "records_updated": random.randint(100, 1000),
            "message": "數據更新完成"
        }
    
    def get_stock_data(self, symbol: str) -> Dict[str, Any]:
        """模擬股票數據獲取"""
        return {
            "symbol": symbol,
            "price": round(random.uniform(10, 200), 2),
            "change": round(random.uniform(-5, 5), 2),
            "change_pct": round(random.uniform(-10, 10), 2),
            "volume": random.randint(1000000, 10000000),
            "timestamp": datetime.now()
        }
    
    def get_market_info(self) -> Dict[str, Any]:
        """模擬市場信息獲取"""
        return {
            "market_status": "open",
            "total_stocks": random.randint(4000, 5000),
            "active_stocks": random.randint(3000, 4000),
            "last_update": self.last_update
        }


class MockBacktestService:
    """模擬回測服務"""
    
    def run_backtest(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """模擬回測執行"""
        time.sleep(3)  # 模擬回測計算時間
        
        # 生成模擬回測結果
        dates = pd.date_range(
            start=config.get("start_date", "2024-01-01"),
            end=config.get("end_date", "2024-12-31"),
            freq="D"
        )
        
        # 模擬收益率序列
        returns = np.random.normal(0.001, 0.02, len(dates))
        cumulative_returns = np.cumprod(1 + returns)
        
        return {
            "success": True,
            "config": config,
            "results": {
                "total_return": round((cumulative_returns[-1] - 1) * 100, 2),
                "annual_return": round(np.mean(returns) * 252 * 100, 2),
                "volatility": round(np.std(returns) * np.sqrt(252) * 100, 2),
                "sharpe_ratio": round(np.mean(returns) / np.std(returns) * np.sqrt(252), 2),
                "max_drawdown": round(random.uniform(-20, -5), 2),
                "win_rate": round(random.uniform(45, 65), 2),
                "profit_factor": round(random.uniform(1.1, 2.5), 2)
            },
            "equity_curve": {
                "dates": [d.strftime("%Y-%m-%d") for d in dates],
                "values": cumulative_returns.tolist()
            },
            "trades": self._generate_mock_trades(dates),
            "execution_time": time.time()
        }
    
    def _generate_mock_trades(self, dates: pd.DatetimeIndex) -> List[Dict[str, Any]]:
        """生成模擬交易記錄"""
        trades = []
        for i in range(random.randint(20, 50)):
            trade_date = random.choice(dates)
            trades.append({
                "date": trade_date.strftime("%Y-%m-%d"),
                "symbol": f"STOCK{random.randint(1, 100):03d}",
                "action": random.choice(["BUY", "SELL"]),
                "quantity": random.randint(100, 1000),
                "price": round(random.uniform(10, 200), 2),
                "pnl": round(random.uniform(-1000, 2000), 2)
            })
        return trades


class MockPortfolioService:
    """模擬投資組合服務"""
    
    def __init__(self):
        self.positions = self._generate_mock_positions()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """模擬投資組合績效指標"""
        total_value = sum(pos["market_value"] for pos in self.positions)
        
        return {
            "total_value": total_value,
            "daily_change": round(random.uniform(-50000, 50000), 2),
            "daily_change_pct": round(random.uniform(-5, 5), 2),
            "positions_count": len(self.positions),
            "cash_balance": round(random.uniform(50000, 200000), 2),
            "total_cost": sum(pos["cost_basis"] for pos in self.positions),
            "unrealized_pnl": sum(pos["unrealized_pnl"] for pos in self.positions),
            "realized_pnl": round(random.uniform(-10000, 30000), 2),
            "positions": self.positions
        }
    
    def _generate_mock_positions(self) -> List[Dict[str, Any]]:
        """生成模擬持倉"""
        positions = []
        for i in range(random.randint(5, 15)):
            quantity = random.randint(100, 1000)
            avg_cost = round(random.uniform(10, 200), 2)
            current_price = round(avg_cost * random.uniform(0.8, 1.3), 2)
            
            position = {
                "symbol": f"STOCK{i+1:03d}",
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "market_value": quantity * current_price,
                "cost_basis": quantity * avg_cost,
                "unrealized_pnl": quantity * (current_price - avg_cost),
                "weight": 0  # 將在後面計算
            }
            positions.append(position)
        
        # 計算權重
        total_value = sum(pos["market_value"] for pos in positions)
        for pos in positions:
            pos["weight"] = pos["market_value"] / total_value * 100
        
        return positions


class MockRiskManagementService:
    """模擬風險管理服務"""
    
    def calculate_risk_metrics(self) -> Dict[str, Any]:
        """模擬風險指標計算"""
        return {
            "var_95": round(random.uniform(-0.05, -0.02), 4),
            "cvar_95": round(random.uniform(-0.08, -0.03), 4),
            "beta": round(random.uniform(0.8, 1.5), 2),
            "alpha": round(random.uniform(-0.02, 0.05), 4),
            "tracking_error": round(random.uniform(0.02, 0.08), 4),
            "information_ratio": round(random.uniform(-0.5, 1.5), 2),
            "maximum_drawdown": round(random.uniform(-0.25, -0.05), 4),
            "volatility": round(random.uniform(0.15, 0.35), 4),
            "downside_deviation": round(random.uniform(0.10, 0.25), 4)
        }


class MockStrategyManagementService:
    """模擬策略管理服務"""
    
    def __init__(self):
        self.strategies = self._generate_mock_strategies()
    
    def get_strategies(self) -> List[Dict[str, Any]]:
        """獲取策略列表"""
        return self.strategies
    
    def create_strategy(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """創建新策略"""
        strategy = {
            "id": f"strategy_{len(self.strategies) + 1}",
            "name": config.get("name", f"策略 {len(self.strategies) + 1}"),
            "type": config.get("type", "momentum"),
            "status": "inactive",
            "created_at": datetime.now(),
            "config": config
        }
        self.strategies.append(strategy)
        return strategy
    
    def _generate_mock_strategies(self) -> List[Dict[str, Any]]:
        """生成模擬策略"""
        strategies = []
        strategy_types = ["momentum", "mean_reversion", "arbitrage", "ml_based"]
        
        for i in range(random.randint(3, 8)):
            strategy = {
                "id": f"strategy_{i+1}",
                "name": f"策略 {i+1}",
                "type": random.choice(strategy_types),
                "status": random.choice(["active", "inactive", "paused"]),
                "created_at": datetime.now() - timedelta(days=random.randint(1, 365)),
                "performance": {
                    "total_return": round(random.uniform(-20, 50), 2),
                    "sharpe_ratio": round(random.uniform(0.5, 2.5), 2),
                    "max_drawdown": round(random.uniform(-30, -5), 2)
                }
            }
            strategies.append(strategy)
        
        return strategies


class MockSystemMonitoringService:
    """模擬系統監控服務"""
    
    def get_system_health(self) -> Dict[str, Any]:
        """模擬系統健康檢查"""
        return {
            "status": "healthy",
            "cpu_usage": round(random.uniform(10, 80), 1),
            "memory_usage": round(random.uniform(30, 90), 1),
            "disk_usage": round(random.uniform(20, 70), 1),
            "active_connections": random.randint(5, 50),
            "last_check": datetime.now(),
            "uptime": timedelta(hours=random.randint(1, 720))
        }


class MockAIModelManagementService:
    """模擬 AI 模型管理服務"""
    
    def get_models(self) -> List[Dict[str, Any]]:
        """獲取模型列表"""
        models = []
        model_types = ["LSTM", "Random Forest", "XGBoost", "Transformer"]
        
        for i in range(random.randint(2, 6)):
            model = {
                "id": f"model_{i+1}",
                "name": f"模型 {i+1}",
                "type": random.choice(model_types),
                "status": random.choice(["trained", "training", "inactive"]),
                "accuracy": round(random.uniform(0.6, 0.95), 3),
                "last_trained": datetime.now() - timedelta(days=random.randint(1, 30))
            }
            models.append(model)
        
        return models
    
    def train_model(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """模擬模型訓練"""
        time.sleep(5)  # 模擬訓練時間
        
        return {
            "success": True,
            "model_id": f"model_{random.randint(100, 999)}",
            "accuracy": round(random.uniform(0.7, 0.95), 3),
            "training_time": random.randint(300, 3600),
            "config": config
        }


# 創建模擬服務實例
mock_services = {
    "data_management": MockDataManagementService(),
    "backtest": MockBacktestService(),
    "portfolio": MockPortfolioService(),
    "risk_management": MockRiskManagementService(),
    "strategy_management": MockStrategyManagementService(),
    "system_monitoring": MockSystemMonitoringService(),
    "ai_model": MockAIModelManagementService()
}


def get_mock_service(service_name: str):
    """獲取模擬服務實例"""
    return mock_services.get(service_name)
