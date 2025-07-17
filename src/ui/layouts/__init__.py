"""
UI 佈局模組初始化

此模組提供 UI 佈局的統一導入介面。
"""

from .page_layout import setup_page_config, apply_responsive_design, show_page_header

__all__ = [
    'setup_page_config',
    'apply_responsive_design',
    'show_page_header'
]
