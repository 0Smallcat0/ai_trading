"""
使用者介面模組 (整合版)

此模組提供系統的Web使用者介面，整合了所有UI功能：
- 儀表板與數據可視化
- 資料管理與特徵工程
- 策略管理與AI模型
- 回測與投資組合優化
- 風險管理與交易執行
- 系統監控與報告
- 響應式設計與性能優化
"""


def run_web_ui(*args, **kwargs):
    """延遲導入並運行Web UI (整合版)

    此函數提供統一的入口點，整合了所有UI功能：
    - web_ui.py (性能優化版)
    - web_ui_enhanced.py (增強版)
    - web_ui_new.py (新版本)

    Args:
        *args: 傳遞給 web_ui.run_web_ui 的位置參數
        **kwargs: 傳遞給 web_ui.run_web_ui 的關鍵字參數

    Returns:
        web_ui.run_web_ui 的返回值
    """
    from .web_ui import run_web_ui as _run_web_ui

    return _run_web_ui(*args, **kwargs)


__all__ = ["run_web_ui"]
