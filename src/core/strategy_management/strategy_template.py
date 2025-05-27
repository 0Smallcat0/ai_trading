"""策略模板管理模組

此模組提供策略模板的管理功能，包括模板定義、獲取、匯入匯出等操作。
"""

import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class StrategyTemplateError(Exception):
    """策略模板異常類別"""


class StrategyTemplate:
    """策略模板管理類別"""

    def __init__(self):
        """初始化策略模板管理"""
        self._strategy_types = self._init_strategy_types()
        self._strategy_templates = self._init_strategy_templates()

    def get_strategy_types(self) -> Dict[str, List[str]]:
        """獲取策略類型定義

        Returns:
            Dict[str, List[str]]: 策略類型字典
        """
        return self._strategy_types

    def get_strategy_templates(self) -> Dict[str, Dict]:
        """獲取策略模板

        Returns:
            Dict[str, Dict]: 策略模板字典
        """
        return self._strategy_templates

    def get_template(self, template_name: str) -> Dict:
        """獲取特定模板

        Args:
            template_name: 模板名稱

        Returns:
            Dict: 模板信息

        Raises:
            StrategyTemplateError: 模板不存在時拋出
        """
        if template_name not in self._strategy_templates:
            raise StrategyTemplateError(f"模板不存在: {template_name}")

        return self._strategy_templates[template_name]

    def validate_strategy_data(self, strategy_dict: Dict) -> bool:
        """驗證策略數據格式

        Args:
            strategy_dict: 策略數據字典

        Returns:
            bool: 是否有效

        Raises:
            StrategyTemplateError: 驗證失敗時拋出
        """
        required_fields = ["name", "type", "description"]

        for field in required_fields:
            if field not in strategy_dict:
                raise StrategyTemplateError(f"缺少必要欄位: {field}")

        # 驗證策略類型
        strategy_type = strategy_dict["type"]
        all_types = []
        for category_types in self._strategy_types.values():
            all_types.extend(category_types)

        if strategy_type not in all_types:
            raise StrategyTemplateError(f"無效的策略類型: {strategy_type}")

        return True

    def export_strategy_template(self, strategy_data: Dict) -> str:
        """匯出策略為模板格式

        Args:
            strategy_data: 策略數據

        Returns:
            str: JSON 格式的模板字符串
        """
        try:
            template = {
                "name": strategy_data.get("name"),
                "type": strategy_data.get("type"),
                "category": strategy_data.get("category"),
                "description": strategy_data.get("description"),
                "code": strategy_data.get("code", ""),
                "parameters": strategy_data.get("parameters", {}),
                "risk_parameters": strategy_data.get("risk_parameters", {}),
                "tags": strategy_data.get("tags", []),
                "template_version": "1.0",
                "created_at": strategy_data.get("created_at"),
            }

            return json.dumps(template, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error("匯出策略模板時發生錯誤: %s", e)
            raise StrategyTemplateError("匯出模板失敗") from e

    def _init_strategy_types(self) -> Dict[str, List[str]]:
        """初始化策略類型定義"""
        return {
            "技術分析策略": [
                "移動平均線交叉策略",
                "RSI策略",
                "MACD策略",
                "布林通道策略",
                "KD指標策略",
                "突破策略",
                "趨勢跟蹤策略",
                "動量策略",
                "均值回歸策略",
            ],
            "基本面策略": [
                "價值投資策略",
                "成長投資策略",
                "股息策略",
                "財報分析策略",
                "產業分析策略",
                "基本面評分策略",
            ],
            "套利策略": [
                "配對交易策略",
                "統計套利策略",
                "價差套利策略",
                "合約轉換套利策略",
                "ETF套利策略",
            ],
            "AI/機器學習策略": [
                "機器學習策略",
                "深度學習策略",
                "強化學習策略",
                "集成學習策略",
                "自然語言處理策略",
                "情緒分析策略",
            ],
            "量化策略": [
                "因子模型策略",
                "多因子策略",
                "風險平價策略",
                "動量因子策略",
                "價值因子策略",
                "品質因子策略",
            ],
        }

    def _init_strategy_templates(self) -> Dict[str, Dict]:
        """初始化策略模板"""
        return {
            "移動平均線交叉策略": {
                "code": '''"""
移動平均線交叉策略

當短期移動平均線向上穿越長期移動平均線時產生買入信號，
當短期移動平均線向下穿越長期移動平均線時產生賣出信號。
"""

import pandas as pd
import numpy as np

def generate_signals(data, short_window=20, long_window=50):
    """
    生成移動平均線交叉信號

    Args:
        data: 價格數據 DataFrame
        short_window: 短期移動平均窗口
        long_window: 長期移動平均窗口

    Returns:
        DataFrame: 包含信號的數據
    """
    # 計算移動平均線
    data['MA_short'] = data['close'].rolling(window=short_window).mean()
    data['MA_long'] = data['close'].rolling(window=long_window).mean()

    # 生成信號
    data['signal'] = 0
    data['signal'][short_window:] = np.where(
        data['MA_short'][short_window:] > data['MA_long'][short_window:], 1, 0
    )

    # 計算持倉變化
    data['positions'] = data['signal'].diff()

    return data

def calculate_returns(data):
    """計算策略收益"""
    data['returns'] = data['close'].pct_change()
    data['strategy_returns'] = data['signal'].shift(1) * data['returns']
    return data
''',
                "parameters": {
                    "short_window": {"type": "int", "default": 20, "min": 5, "max": 50},
                    "long_window": {
                        "type": "int",
                        "default": 50,
                        "min": 20,
                        "max": 200,
                    },
                },
                "risk_parameters": {
                    "stop_loss": {
                        "type": "float",
                        "default": 0.05,
                        "min": 0.01,
                        "max": 0.2,
                    },
                    "take_profit": {
                        "type": "float",
                        "default": 0.15,
                        "min": 0.05,
                        "max": 0.5,
                    },
                },
                "description": "基於移動平均線交叉的趨勢跟蹤策略",
                "category": "技術分析策略",
            },
            "RSI策略": {
                "code": '''"""
RSI 超買超賣策略

當 RSI 指標低於超賣線時產生買入信號，
當 RSI 指標高於超買線時產生賣出信號。
"""

import pandas as pd
import numpy as np

def calculate_rsi(data, window=14):
    """計算 RSI 指標"""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def generate_signals(data, rsi_window=14, oversold=30, overbought=70):
    """生成 RSI 信號"""
    data['RSI'] = calculate_rsi(data, rsi_window)

    data['signal'] = 0
    data['signal'] = np.where(data['RSI'] < oversold, 1, data['signal'])
    data['signal'] = np.where(data['RSI'] > overbought, -1, data['signal'])

    return data
''',
                "parameters": {
                    "rsi_window": {"type": "int", "default": 14, "min": 5, "max": 30},
                    "oversold": {"type": "int", "default": 30, "min": 10, "max": 40},
                    "overbought": {"type": "int", "default": 70, "min": 60, "max": 90},
                },
                "risk_parameters": {
                    "stop_loss": {
                        "type": "float",
                        "default": 0.03,
                        "min": 0.01,
                        "max": 0.1,
                    },
                    "position_size": {
                        "type": "float",
                        "default": 0.1,
                        "min": 0.05,
                        "max": 0.3,
                    },
                },
                "description": "基於 RSI 指標的超買超賣策略",
                "category": "技術分析策略",
            },
        }

    def search_templates(self, query: str) -> List[str]:
        """搜尋策略模板

        Args:
            query: 搜尋關鍵字

        Returns:
            List[str]: 匹配的模板名稱列表
        """
        results = []
        query_lower = query.lower()

        for template_name, template_data in self._strategy_templates.items():
            if (
                query_lower in template_name.lower()
                or query_lower in template_data.get("description", "").lower()
            ):
                results.append(template_name)

        return results
