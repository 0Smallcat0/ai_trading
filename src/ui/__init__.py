"""
使用者介面模組

此模組提供系統的Web使用者介面，包括：
- 儀表板
- 資料管理頁面
- 策略管理頁面
- 回測頁面
- 交易執行頁面
- 系統監控頁面
"""


def run_web_ui(*args, **kwargs):
    """延遲導入並運行Web UI

    Args:
        *args: 傳遞給 web_ui.run_web_ui 的位置參數
        **kwargs: 傳遞給 web_ui.run_web_ui 的關鍵字參數

    Returns:
        web_ui.run_web_ui 的返回值
    """
    from .web_ui import run_web_ui as _run_web_ui
    return _run_web_ui(*args, **kwargs)


__all__ = ["run_web_ui"]
