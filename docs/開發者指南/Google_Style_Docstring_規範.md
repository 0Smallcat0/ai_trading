# Google Style Docstring 規範

## 概述

本專案採用 Google Style Docstring 規範來撰寫文檔字符串。這種格式清晰、易讀，並且與許多文檔生成工具兼容。

## 基本格式

```python
def function_name(param1: type, param2: type) -> return_type:
    """簡短的一行描述。

    更詳細的描述，可以跨越多行。解釋函數的目的、
    行為和任何重要的實現細節。

    Args:
        param1: 參數1的描述。
        param2: 參數2的描述。

    Returns:
        返回值的描述。

    Raises:
        ValueError: 當參數無效時拋出。
        TypeError: 當參數類型錯誤時拋出。

    Example:
        基本用法示例：

        >>> result = function_name("hello", 42)
        >>> print(result)
        "hello: 42"

    Note:
        任何重要的注意事項或限制。
    """
    pass
```

## 各部分說明

### 1. 簡短描述
- 第一行應該是簡短的一行描述
- 以大寫字母開頭，以句號結尾
- 不超過 79 個字符
- 描述函數做什麼，而不是如何做

### 2. 詳細描述
- 與簡短描述之間空一行
- 可以跨越多行
- 提供更多關於函數目的和行為的信息
- 可以包含實現細節、算法說明等

### 3. Args 部分
- 列出所有參數
- 格式為 `param_name: 參數描述`
- 如果參數有默認值，可以在描述中說明
- 如果參數是可選的，應該在描述中說明

### 4. Returns 部分
- 描述返回值
- 如果返回多個值，應該分別描述
- 如果返回 None，也應該說明

### 5. Raises 部分
- 列出函數可能拋出的異常
- 說明拋出異常的條件
- 只列出函數直接拋出的異常，不包括被調用函數可能拋出的異常

### 6. Example 部分
- 提供使用示例
- 使用 doctest 格式，可以自動測試
- 示例應該簡單明了，展示典型用法

### 7. Note 部分
- 提供任何重要的注意事項或限制
- 可以包含性能考慮、副作用等

## 類文檔字符串

```python
class SampleClass:
    """類的簡短描述。

    類的詳細描述，可以跨越多行。解釋類的目的、
    行為和任何重要的實現細節。

    Attributes:
        attr1: 屬性1的描述。
        attr2: 屬性2的描述。
    """

    def __init__(self, param1, param2):
        """初始化 SampleClass。

        Args:
            param1: 參數1的描述。
            param2: 參數2的描述。
        """
        self.attr1 = param1
        self.attr2 = param2
```

## 模組文檔字符串

```python
"""模組的簡短描述。

模組的詳細描述，可以跨越多行。解釋模組的目的、
內容和使用方法。

This module provides:
    1. Function to do X
    2. Class to represent Y
    3. Constants for Z
"""

import os
import sys
```

## 特殊情況

### 1. 屬性文檔

使用 property 裝飾器的方法應該在 docstring 中使用類似屬性的文檔格式：

```python
@property
def name(self):
    """屬性的簡短描述。

    更詳細的描述。

    Returns:
        返回值的描述。
    """
    return self._name
```

### 2. 生成器函數

生成器函數應該在 Returns 部分使用 Yields 代替：

```python
def generate_numbers(n):
    """生成 n 個數字。

    Args:
        n: 要生成的數字數量。

    Yields:
        生成的數字。
    """
    for i in range(n):
        yield i
```

### 3. 裝飾器

裝飾器應該在 docstring 中說明其對被裝飾函數的影響：

```python
def retry(max_attempts):
    """在失敗時重試函數。

    Args:
        max_attempts: 最大重試次數。

    Returns:
        裝飾器函數。

    Example:
        >>> @retry(3)
        ... def might_fail():
        ...     pass
    """
    def decorator(func):
        # 實現...
        return wrapped
    return decorator
```

## 代碼品質檢查

### 使用 pydocstyle 檢查

```bash
# 安裝 pydocstyle
pip install pydocstyle

# 檢查單個文件
pydocstyle file.py

# 檢查整個目錄
pydocstyle directory/
```

### 使用 pylint 檢查

```bash
# 安裝 pylint
pip install pylint

# 檢查文件
pylint --disable=all --enable=missing-docstring,empty-docstring file.py
```

## 文檔生成

### 使用 Sphinx 生成文檔

1. 安裝 Sphinx 和 napoleon 擴展：
   ```bash
   pip install sphinx sphinx-rtd-theme
   ```

2. 初始化 Sphinx 項目：
   ```bash
   mkdir docs
   cd docs
   sphinx-quickstart
   ```

3. 在 `conf.py` 中啟用 napoleon 擴展：
   ```python
   extensions = [
       'sphinx.ext.autodoc',
       'sphinx.ext.napoleon',
   ]
   ```

4. 生成文檔：
   ```bash
   sphinx-build -b html . _build/html
   ```

## 最佳實踐

### 1. 保持一致性
- 在整個專案中使用相同的文檔風格
- 遵循既定的格式和順序
- 使用統一的術語和表達方式

### 2. 簡潔明了
- 使用簡單、直接的語言
- 避免不必要的技術術語
- 專注於用戶需要知道的信息

### 3. 完整性
- 為所有公共 API 提供文檔
- 包含所有必要的部分
- 說明所有可能的異常和邊緣情況

### 4. 示例
- 提供有用的示例
- 展示典型用法
- 確保示例可以運行

### 5. 類型提示
- 結合類型提示和文檔字符串
- 在參數和返回值中使用類型提示
- 在文檔中解釋複雜的類型

## 常見錯誤

### 1. 不完整的文檔
- 缺少參數或返回值描述
- 沒有說明可能的異常
- 缺少使用示例

### 2. 過時的文檔
- 文檔與代碼不同步
- 描述不存在的參數
- 示例無法運行

### 3. 格式錯誤
- 不遵循 Google Style 格式
- 部分順序錯誤
- 縮進不一致

---

**文檔版本**: v1.0  
**最後更新**: 2025-01-15  
**維護團隊**: AI Trading System Development Team
