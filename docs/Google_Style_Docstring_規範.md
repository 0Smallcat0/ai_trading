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
- 解釋函數的目的、行為和重要細節
- 可以包含算法說明、使用場景等

### 3. Args（參數）
- 列出所有參數
- 格式：`參數名: 描述`
- 如果參數有類型提示，描述中可以省略類型
- 對於複雜類型，可以詳細說明結構

### 4. Returns（返回值）
- 描述返回值的含義和類型
- 如果函數沒有返回值，可以省略此部分
- 對於複雜返回值，詳細說明結構

### 5. Raises（異常）
- 列出可能拋出的異常
- 格式：`異常類型: 拋出條件`
- 只列出函數直接拋出的異常

### 6. Example（示例）
- 提供使用示例
- 使用 doctest 格式
- 包含預期輸出

### 7. Note（注意事項）
- 重要的注意事項或限制
- 性能考慮
- 線程安全性等

## 類的文檔字符串

```python
class ExampleClass:
    """簡短的類描述。

    更詳細的類描述，說明類的目的、主要功能
    和使用場景。

    Attributes:
        attr1: 屬性1的描述。
        attr2: 屬性2的描述。

    Example:
        基本用法：

        >>> obj = ExampleClass("value")
        >>> obj.method()
        "result"
    """

    def __init__(self, param1: str):
        """初始化方法。

        Args:
            param1: 初始化參數的描述。
        """
        self.attr1 = param1
        self.attr2 = None

    def method(self) -> str:
        """方法的描述。

        Returns:
            方法返回值的描述。
        """
        return f"result: {self.attr1}"
```

## 模組的文檔字符串

```python
"""模組的簡短描述。

更詳細的模組描述，說明模組的目的、主要功能
和包含的類/函數概述。

Example:
    模組使用示例：

    >>> from module_name import function_name
    >>> result = function_name()

Note:
    模組的重要注意事項。
"""

import os
import sys
```

## 特殊情況

### 1. 屬性（Property）

```python
@property
def value(self) -> int:
    """屬性的描述。

    Returns:
        屬性值的描述。
    """
    return self._value

@value.setter
def value(self, new_value: int) -> None:
    """設置屬性值。

    Args:
        new_value: 新的屬性值。

    Raises:
        ValueError: 當值無效時拋出。
    """
    if new_value < 0:
        raise ValueError("Value must be non-negative")
    self._value = new_value
```

### 2. 生成器函數

```python
def generate_items() -> Iterator[str]:
    """生成項目的生成器。

    Yields:
        str: 生成的項目。

    Example:
        >>> for item in generate_items():
        ...     print(item)
        item1
        item2
    """
    yield "item1"
    yield "item2"
```

### 3. 裝飾器

```python
def decorator(func: Callable) -> Callable:
    """裝飾器的描述。

    Args:
        func: 被裝飾的函數。

    Returns:
        裝飾後的函數。

    Example:
        >>> @decorator
        ... def my_function():
        ...     pass
    """
    def wrapper(*args, **kwargs):
        # 裝飾器邏輯
        return func(*args, **kwargs)
    return wrapper
```

## 最佳實踐

### 1. 一致性
- 在整個專案中保持一致的風格
- 使用相同的術語和描述方式

### 2. 簡潔性
- 避免冗長的描述
- 重點突出關鍵信息

### 3. 準確性
- 確保文檔與代碼同步
- 及時更新文檔

### 4. 完整性
- 所有公共 API 都應該有文檔
- 包含必要的示例和注意事項

### 5. 可測試性
- 使用 doctest 格式的示例
- 確保示例可以運行

## 檢查工具

### 1. pydocstyle
```bash
# 檢查文檔字符串格式
pydocstyle --convention=google src/
```

### 2. pylint
```bash
# 檢查缺失的文檔字符串
pylint --disable=all --enable=missing-docstring src/
```

### 3. doctest
```bash
# 運行文檔測試
python -m doctest module_name.py
```

## 配置文件

### .pydocstyle
```ini
[pydocstyle]
convention = google
add-ignore = D100,D104
match-dir = (?!tests).*
```

### pylint 配置
```ini
[BASIC]
docstring-min-length = 10

[MESSAGES CONTROL]
enable = missing-docstring
```

## 常見錯誤

### 1. 缺少簡短描述
```python
# 錯誤
def bad_function():
    """
    這個函數做某些事情。
    """
    pass

# 正確
def good_function():
    """做某些事情的函數。

    更詳細的描述...
    """
    pass
```

### 2. 參數描述不完整
```python
# 錯誤
def bad_function(param1, param2):
    """函數描述。

    Args:
        param1: 參數1。
    """
    pass

# 正確
def good_function(param1, param2):
    """函數描述。

    Args:
        param1: 參數1的詳細描述。
        param2: 參數2的詳細描述。
    """
    pass
```

### 3. 缺少類型信息
```python
# 錯誤（當沒有類型提示時）
def bad_function(items):
    """處理項目列表。

    Args:
        items: 項目。
    """
    pass

# 正確
def good_function(items: List[str]):
    """處理項目列表。

    Args:
        items: 字符串項目的列表。
    """
    pass
```

## 總結

遵循 Google Style Docstring 規範可以：
- 提高代碼可讀性
- 便於自動生成文檔
- 支持 IDE 的智能提示
- 便於團隊協作
- 支持自動化測試
