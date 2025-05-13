import pytest


@pytest.mark.parametrize(
    "module_path",
    [
        "src.strategy.strategy",
        "src.strategy.momentum",
        "src.strategy.mean_reversion",
    ],
)
def test_strategy_module_import(module_path):
    """測試策略模組能否正確匯入。"""
    __import__(module_path)
