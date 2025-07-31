"""投資組合異常處理模組

此模組定義了投資組合管理中使用的各種異常類別。

主要異常類別：
- PortfolioOptimizationError: 投資組合最佳化錯誤
- DependencyError: 依賴套件錯誤
- ValidationError: 資料驗證錯誤
- InsufficientFundsError: 資金不足錯誤
- InvalidWeightsError: 無效權重錯誤
"""


class PortfolioOptimizationError(Exception):
    """投資組合最佳化錯誤
    
    當投資組合最佳化過程中發生錯誤時拋出此異常。
    """
    
    def __init__(self, message: str = "投資組合最佳化失敗"):
        """初始化異常
        
        Args:
            message: 錯誤訊息
        """
        self.message = message
        super().__init__(self.message)


class DependencyError(Exception):
    """依賴套件錯誤
    
    當缺少必要的依賴套件時拋出此異常。
    """
    
    def __init__(self, package_name: str, message: str = None):
        """初始化異常
        
        Args:
            package_name: 缺少的套件名稱
            message: 自定義錯誤訊息
        """
        self.package_name = package_name
        if message is None:
            message = f"缺少必要的依賴套件: {package_name}"
        self.message = message
        super().__init__(self.message)


class ValidationError(Exception):
    """資料驗證錯誤
    
    當輸入資料不符合要求時拋出此異常。
    """
    
    def __init__(self, message: str = "資料驗證失敗"):
        """初始化異常
        
        Args:
            message: 錯誤訊息
        """
        self.message = message
        super().__init__(self.message)


class InsufficientFundsError(Exception):
    """資金不足錯誤
    
    當可用資金不足以執行交易時拋出此異常。
    """
    
    def __init__(self, required: float, available: float):
        """初始化異常
        
        Args:
            required: 所需資金
            available: 可用資金
        """
        self.required = required
        self.available = available
        self.message = f"資金不足: 需要 {required:,.2f}, 可用 {available:,.2f}"
        super().__init__(self.message)


class InvalidWeightsError(Exception):
    """無效權重錯誤
    
    當投資組合權重不符合要求時拋出此異常。
    """
    
    def __init__(self, message: str = "無效的投資組合權重"):
        """初始化異常
        
        Args:
            message: 錯誤訊息
        """
        self.message = message
        super().__init__(self.message)


class OptimizationConvergenceError(PortfolioOptimizationError):
    """最佳化收斂錯誤
    
    當最佳化演算法無法收斂時拋出此異常。
    """
    
    def __init__(self, iterations: int = None):
        """初始化異常
        
        Args:
            iterations: 已執行的迭代次數
        """
        self.iterations = iterations
        if iterations is not None:
            message = f"最佳化演算法在 {iterations} 次迭代後未能收斂"
        else:
            message = "最佳化演算法未能收斂"
        super().__init__(message)


class RiskConstraintViolationError(Exception):
    """風險約束違反錯誤
    
    當投資組合違反風險約束時拋出此異常。
    """
    
    def __init__(self, constraint_type: str, value: float, limit: float):
        """初始化異常
        
        Args:
            constraint_type: 約束類型
            value: 實際值
            limit: 限制值
        """
        self.constraint_type = constraint_type
        self.value = value
        self.limit = limit
        self.message = f"違反 {constraint_type} 約束: {value:.4f} > {limit:.4f}"
        super().__init__(self.message)


class DataQualityError(Exception):
    """資料品質錯誤
    
    當輸入資料品質不符合要求時拋出此異常。
    """
    
    def __init__(self, message: str = "資料品質不符合要求"):
        """初始化異常
        
        Args:
            message: 錯誤訊息
        """
        self.message = message
        super().__init__(self.message)


# 為了向後相容性，保留原有的異常類別別名
PortfolioError = PortfolioOptimizationError
