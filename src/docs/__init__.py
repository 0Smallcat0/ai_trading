"""文檔管理模組

此模組提供文檔相關的管理和標準化工具。

主要功能：
- 文檔標準化和格式統一
- 版本控制和變更歷史管理
- 技術準確性驗證
- 多語言一致性檢查
"""

from .doc_standardizer import DocumentStandardizer

__all__ = [
    "DocumentStandardizer",
]

__version__ = "1.0.0"
