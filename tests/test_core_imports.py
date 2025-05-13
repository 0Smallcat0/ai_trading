import pytest


# 測試 src/core 主要模組能否正確匯入
@pytest.mark.parametrize(
    "module_path",
    [
        "src.core.executor",
        "src.core.backtest",
        "src.core.data_ingest",
        "src.core.event_monitor",
        "src.core.portfolio",
        "src.core.risk_control",
        "src.core.signal_gen",
        "src.core.features",
        "src.core.logger",
    ],
)
def test_core_module_import(module_path):
    """測試核心模組能否正確匯入。"""
    __import__(module_path)
