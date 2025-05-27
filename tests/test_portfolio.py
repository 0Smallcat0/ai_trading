"""
投資組合管理模組測試

注意：這個測試文件僅用於驗證 portfolio.py 模組的存在性，
不會實際執行其中的代碼，因為它依賴於一些可能不容易安裝的套件。
"""

import os
import sys

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# 檢查 portfolio.py 文件是否存在
def test_portfolio_module_exists():
    """測試 portfolio.py 模組是否存在"""
    module_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "core", "portfolio.py"
    )
    assert os.path.exists(module_path), "portfolio.py 模組不存在"


# 檢查 portfolio.py 文件中是否包含必要的類和函數
def test_portfolio_module_content():
    """測試 portfolio.py 模組是否包含必要的類和函數"""
    module_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "core", "portfolio.py"
    )
    with open(module_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 檢查必要的類
    assert "class Portfolio" in content, "Portfolio 類不存在"
    assert "class EqualWeightPortfolio" in content, "EqualWeightPortfolio 類不存在"
    assert "class MeanVariancePortfolio" in content, "MeanVariancePortfolio 類不存在"
    assert "class RiskParityPortfolio" in content, "RiskParityPortfolio 類不存在"
    assert "class MaxSharpePortfolio" in content, "MaxSharpePortfolio 類不存在"
    assert "class MinVariancePortfolio" in content, "MinVariancePortfolio 類不存在"

    # 檢查必要的函數
    assert "def optimize(" in content, "optimize 函數不存在"
    assert "def simulate_portfolios(" in content, "simulate_portfolios 函數不存在"
    assert (
        "def compare_portfolio_performance(" in content
    ), "compare_portfolio_performance 函數不存在"


# 檢查 portfolio.py 文件中是否包含必要的方法
def test_portfolio_methods():
    """測試 portfolio.py 模組是否包含必要的方法"""
    module_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "core", "portfolio.py"
    )
    with open(module_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 檢查 Portfolio 類的方法
    assert "def simulate(" in content, "Portfolio.simulate 方法不存在"
    assert (
        "def _update_positions_value(" in content
    ), "Portfolio._update_positions_value 方法不存在"
    assert "def _record_state(" in content, "Portfolio._record_state 方法不存在"
    assert (
        "def _execute_rebalance(" in content
    ), "Portfolio._execute_rebalance 方法不存在"
    assert "def _buy_stock(" in content, "Portfolio._buy_stock 方法不存在"
    assert "def _sell_stock(" in content, "Portfolio._sell_stock 方法不存在"
    assert (
        "def _calculate_performance(" in content
    ), "Portfolio._calculate_performance 方法不存在"

    # 檢查其他重要函數
    assert "def backtest_portfolio(" in content, "backtest_portfolio 函數不存在"
    assert "def evaluate_portfolio(" in content, "evaluate_portfolio 函數不存在"
    assert (
        "def plot_portfolio_performance(" in content
    ), "plot_portfolio_performance 函數不存在"
