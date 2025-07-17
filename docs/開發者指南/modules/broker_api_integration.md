# 券商 API 整合模組

## 📋 概述

本文檔詳細說明了 AI 交易系統中券商 API 整合模組的架構設計和實現細節，包括永豐證券 API 和 Interactive Brokers API 的整合。

**版本**: v2.0  
**最後更新**: 2025-01-15  
**維護狀態**: ✅ 活躍維護

## 🏗️ 模組架構

### 核心設計

```
src/execution/
├── broker_base.py          # 券商基礎介面
├── shioaji_adapter.py      # 永豐證券適配器
├── ib_adapter.py           # Interactive Brokers 適配器
└── broker_factory.py       # 券商工廠類
```

### 統一介面設計

```python
class BrokerBase(ABC):
    """券商 API 基礎介面
    
    所有券商適配器必須實現此介面。
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """連接券商 API"""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """斷開券商 API 連接"""
        pass
    
    @abstractmethod
    def place_order(self, order: Order) -> str:
        """下單"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """撤單"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """獲取帳戶資訊"""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """獲取持倉"""
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> OrderStatus:
        """獲取訂單狀態"""
        pass
    
    @abstractmethod
    def subscribe_market_data(self, symbols: List[str]) -> bool:
        """訂閱市場數據"""
        pass
```

## 🚀 已實現券商適配器

### 1. 永豐證券 API 整合 (ShioajiAdapter)

**代碼品質**: Pylint 評分 9.44/10 ⭐

**已實現功能**:
- ✅ API 認證與安全連接機制
- ✅ 帳戶資訊查詢功能 (餘額、持倉等)
- ✅ 即時報價訂閱系統
- ✅ 下單與撤單功能 (市價單、限價單、IOC、FOK)
- ✅ 持倉與交易記錄查詢功能
- ✅ 連接狀態即時監控 (心跳檢測)
- ✅ 自動重連機制 (斷線重連)
- ✅ 統一錯誤處理與重試邏輯
- ✅ 訂單狀態追蹤與回調機制
- ✅ 多市場支援 (台股、美股、港股)

**技術特點**:
- 使用 Google Style Docstring
- 實現了複雜度控制 (方法拆分)
- 統一的日誌格式 (lazy % formatting)
- 完整的錯誤處理機制
- 線程安全的心跳檢測

**使用範例**:

```python
from src.execution.shioaji_adapter import ShioajiAdapter
from src.execution.broker_base import Order, OrderType

# 初始化適配器
adapter = ShioajiAdapter(
    api_key="your_api_key",
    secret_key="your_secret_key",
    person_id="your_person_id"
)

# 連接 API
if adapter.connect():
    print("已連接到永豐證券 API")
    
    # 創建訂單
    order = Order(
        stock_id="2330",
        action="buy",
        quantity=1,
        order_type=OrderType.MARKET
    )
    
    # 下單
    order_id = adapter.place_order(order)
    if order_id:
        print(f"訂單已提交: {order_id}")
        
        # 獲取訂單狀態
        status = adapter.get_order_status(order_id)
        print(f"訂單狀態: {status}")
```

### 2. Interactive Brokers API 整合 (IBAdapter)

**代碼品質**: Pylint 評分 9.1/10 (已優化) ⭐

**已實現功能**:
- ✅ TWS API 連接模組
- ✅ 基本的下單與撤單功能
- ✅ 訂單狀態追蹤
- ✅ 基本帳戶資訊查詢
- ✅ 持倉查詢功能
- ✅ 美股即時數據接收
- ✅ 連接監控和強制重連功能
- ✅ 多市場合約創建 (美股、台股、港股)
- ✅ 期權交易支援
- ✅ 完整的即時報價訂閱系統

**使用範例**:

```python
from src.execution.ib_adapter import IBAdapter
from src.execution.broker_base import Order, OrderType

# 初始化適配器
adapter = IBAdapter(
    host="127.0.0.1",
    port=7497,  # TWS 端口
    client_id=1
)

# 連接 IB API
if adapter.connect():
    print("已連接到 Interactive Brokers")
    
    # 創建訂單
    order = Order(
        stock_id="AAPL",
        action="buy",
        quantity=1,
        order_type=OrderType.MARKET
    )
    
    # 下單
    order_id = adapter.place_order(order)
    if order_id:
        print(f"訂單已提交: {order_id}")
```

## 🔧 券商工廠類

為了實現券商適配器的統一管理和動態創建，系統實現了券商工廠類：

```python
class BrokerFactory:
    """券商工廠類
    
    用於創建不同券商的適配器實例。
    """
    
    @staticmethod
    def create_broker(broker_type: str, **kwargs) -> BrokerBase:
        """創建券商適配器
        
        Args:
            broker_type: 券商類型 ("shioaji", "ib")
            **kwargs: 券商特定參數
            
        Returns:
            BrokerBase: 券商適配器實例
            
        Raises:
            ValueError: 不支援的券商類型
        """
        if broker_type.lower() == "shioaji":
            return ShioajiAdapter(**kwargs)
        elif broker_type.lower() == "ib":
            return IBAdapter(**kwargs)
        else:
            raise ValueError(f"不支援的券商類型: {broker_type}")
```

**使用範例**:

```python
from src.execution.broker_factory import BrokerFactory

# 創建永豐證券適配器
shioaji_broker = BrokerFactory.create_broker(
    "shioaji",
    api_key="your_api_key",
    secret_key="your_secret_key",
    person_id="your_person_id"
)

# 創建 IB 適配器
ib_broker = BrokerFactory.create_broker(
    "ib",
    host="127.0.0.1",
    port=7497,
    client_id=1
)
```

## 📊 性能指標

### 永豐證券適配器
- **連接建立**: <3 秒
- **訂單提交**: <150ms
- **市場數據更新**: <50ms
- **記憶體使用**: ~30MB (基礎運行)

### IB 適配器
- **連接建立**: <5 秒
- **訂單提交**: <200ms
- **市場數據更新**: <50ms
- **記憶體使用**: ~50MB (基礎運行)

## 🧪 測試覆蓋

### 測試類型
- **單元測試**: 90%+ 覆蓋率
- **整合測試**: 端到端功能驗證
- **模擬測試**: 使用模擬券商 API

### 測試執行

```bash
# 執行所有券商相關測試
python -m pytest tests/test_broker_*.py -v

# 執行永豐證券測試
python -m pytest tests/test_shioaji_adapter.py -v

# 執行 IB 測試
python -m pytest tests/test_ib_adapter.py -v
```

## 📚 相關文檔

### 技術文檔
- [Interactive Brokers 模組](./interactive_brokers/README.md)
- [期權交易指南](./interactive_brokers/ib_options.md)
- [API 參考文檔](../API文檔.md)

### 使用者文檔
- [券商 API 設定教程](../../使用者手冊/券商API設定教程.md)

---

**維護團隊**: AI Trading System Development Team  
**最後更新**: 2025-01-15
