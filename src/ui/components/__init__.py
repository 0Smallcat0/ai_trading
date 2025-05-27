"""
元件模組

此模組包含所有 Web UI 的可重用元件。
"""


def login_form(*args, **kwargs):
    """延遲導入登入表單"""
    from .auth import login_form as _login_form
    return _login_form(*args, **kwargs)


def show_notification(*args, **kwargs):
    """延遲導入通知組件"""
    from .notifications import show_notification as _show_notification
    return _show_notification(*args, **kwargs)


def line_chart(*args, **kwargs):
    """延遲導入線圖組件"""
    from .charts import line_chart as _line_chart
    return _line_chart(*args, **kwargs)


def bar_chart(*args, **kwargs):
    """延遲導入柱狀圖組件"""
    from .charts import bar_chart as _bar_chart
    return _bar_chart(*args, **kwargs)


def candlestick_chart(*args, **kwargs):
    """延遲導入K線圖組件"""
    from .charts import candlestick_chart as _candlestick_chart
    return _candlestick_chart(*args, **kwargs)


def data_table(*args, **kwargs):
    """延遲導入數據表組件"""
    from .tables import data_table as _data_table
    return _data_table(*args, **kwargs)


def create_form(*args, **kwargs):
    """延遲導入表單組件"""
    from .forms import create_form as _create_form
    return _create_form(*args, **kwargs)


__all__ = [
    "login_form",
    "show_notification",
    "line_chart",
    "bar_chart",
    "candlestick_chart",
    "data_table",
    "create_form",
]
