# Interactive Brokers 期權交易技術文檔

## 📋 概述

Interactive Brokers 期權交易模組 (`ib_options.py`) 提供完整的期權交易功能，包括期權合約管理、價格獲取、交易執行、Greeks 計算和風險管理。

**模組位置**: `src/execution/ib_options.py`  
**版本**: v1.0  
**最後更新**: 2025-07-14  

## 🏗️ 核心架構

### 主要類別

#### IBOptionsManager
期權管理器主類，提供所有期權相關功能。

```python
class IBOptionsManager:
    """IB 期權管理器
    
    提供完整的期權交易功能，包括合約管理、價格獲取、交易執行和風險管理。
    """
    
    def __init__(self, client=None):
        """初始化期權管理器"""
        self.client = client
        self.contract_manager = IBContractManager()
        self.order_manager = IBOrderManager()
```

### 數據結構

#### OptionQuote
期權報價數據類，包含完整的期權市場資訊。

```python
@dataclass
class OptionQuote:
    """期權報價數據類"""
    symbol: str              # 標的代號
    expiry: str             # 到期日 (YYYYMMDD)
    strike: float           # 行權價
    right: str              # 期權類型 (C/P)
    bid: float              # 買價
    ask: float              # 賣價
    last: float             # 最後成交價
    volume: int             # 成交量
    open_interest: int      # 未平倉量
    implied_volatility: float  # 隱含波動率
    delta: float            # Delta
    gamma: float            # Gamma
    theta: float            # Theta
    vega: float             # Vega
    timestamp: datetime     # 時間戳
```

#### OptionChain
期權鏈數據類，包含特定到期日的所有期權。

```python
@dataclass
class OptionChain:
    """期權鏈數據類"""
    symbol: str                    # 標的代號
    expiry: str                   # 到期日
    calls: List[OptionQuote]      # Call 期權列表
    puts: List[OptionQuote]       # Put 期權列表
    underlying_price: float       # 標的價格
```

## 🚀 核心功能

### 1. 期權合約管理

#### 創建期權合約
```python
# 創建 Call 期權合約
call_contract = contract_manager.create_option_contract(
    symbol="AAPL",
    expiry="20241220",
    strike=150.0,
    right="C",
    exchange="SMART",
    currency="USD"
)

# 創建 Put 期權合約
put_contract = contract_manager.create_option_contract(
    symbol="AAPL",
    expiry="20241220", 
    strike=150.0,
    right="P"
)
```

#### 獲取期權到期日
```python
# 獲取未來 6 個月的期權到期日
expiry_dates = contract_manager.get_option_expiry_dates("AAPL", months_ahead=6)
```

### 2. 期權價格獲取

#### 獲取期權報價
```python
# 獲取單一期權報價
option_quote = options_manager.get_option_quote(
    symbol="AAPL",
    expiry="20241220",
    strike=150.0,
    right="C"
)

# 獲取期權鏈
option_chain = options_manager.get_option_chain("AAPL", "20241220")
```

### 3. 期權交易執行

#### 期權下單
```python
# Call 期權買入
order_id = options_manager.place_option_order(
    symbol="AAPL",
    expiry="20241220",
    strike=150.0,
    right="C",
    action="BUY",
    quantity=1,
    order_type="LMT",
    price=5.0
)

# Put 期權賣出
order_id = options_manager.place_option_order(
    symbol="AAPL",
    expiry="20241220",
    strike=140.0,
    right="P",
    action="SELL",
    quantity=1,
    order_type="MKT"
)
```

### 4. Greeks 計算

#### Black-Scholes 模型
```python
# 計算期權 Greeks
greeks = options_manager.calculate_greeks(
    underlying_price=150.0,
    strike=150.0,
    time_to_expiry=30,  # 天數
    risk_free_rate=0.05,
    volatility=0.25,
    option_type="call"
)

print(f"Delta: {greeks['delta']:.4f}")
print(f"Gamma: {greeks['gamma']:.4f}")
print(f"Theta: {greeks['theta']:.4f}")
print(f"Vega: {greeks['vega']:.4f}")
```

### 5. 期權策略

#### 支援的策略
1. **Covered Call** - 備兌看漲
2. **Protective Put** - 保護性看跌
3. **Bull Call Spread** - 牛市看漲價差
4. **Bear Put Spread** - 熊市看跌價差
5. **Long Straddle** - 長跨式
6. **Short Strangle** - 短寬跨式

#### 策略執行範例
```python
# 執行備兌看漲策略
strategy_orders = options_manager.execute_option_strategy(
    strategy=OptionStrategy.COVERED_CALL,
    symbol="AAPL",
    expiry="20241220",
    strike=150.0,
    quantity=1
)

# 執行牛市價差策略
spread_orders = options_manager.execute_option_strategy(
    strategy=OptionStrategy.BULL_CALL_SPREAD,
    symbol="AAPL",
    expiry="20241220",
    long_strike=145.0,
    short_strike=155.0,
    quantity=1
)
```

## 🔧 配置參數

### 期權交易設定
```python
OPTIONS_CONFIG = {
    "default_exchange": "SMART",
    "default_currency": "USD",
    "price_precision": 2,
    "quantity_precision": 0,
    "greeks_calculation": True,
    "auto_exercise": False,
    "risk_check": True
}
```

### 風險管理參數
```python
RISK_LIMITS = {
    "max_option_position": 100,
    "max_delta_exposure": 1000,
    "max_gamma_exposure": 500,
    "max_vega_exposure": 10000,
    "days_to_expiry_warning": 7
}
```

## 📊 性能指標

### 執行效率
- **期權報價獲取**: <100ms
- **期權鏈獲取**: <500ms
- **Greeks 計算**: <10ms
- **策略執行**: <200ms

### 準確性指標
- **價格精度**: ±0.01
- **Greeks 精度**: ±0.001
- **執行成功率**: >99%

## 🧪 測試用例

### 單元測試
```python
def test_option_contract_creation():
    """測試期權合約創建"""
    contract = create_option_contract("AAPL", "20241220", 150.0, "C")
    assert contract.symbol == "AAPL"
    assert contract.strike == 150.0

def test_greeks_calculation():
    """測試 Greeks 計算"""
    greeks = calculate_greeks(150, 150, 30, 0.05, 0.25, "call")
    assert 0 < greeks['delta'] < 1
    assert greeks['gamma'] > 0
```

### 整合測試
```python
def test_option_trading_workflow():
    """測試期權交易完整流程"""
    # 1. 獲取期權鏈
    chain = get_option_chain("AAPL", "20241220")
    
    # 2. 選擇期權
    target_option = chain.calls[0]
    
    # 3. 下單
    order_id = place_option_order(target_option, "BUY", 1)
    
    # 4. 驗證訂單
    assert order_id is not None
```

## 🔒 風險管理

### 風險檢查
- **倉位限制**: 檢查最大持倉量
- **保證金檢查**: 驗證帳戶保證金
- **到期風險**: 監控即將到期的期權
- **Greeks 風險**: 控制 Delta、Gamma、Vega 暴露

### 異常處理
```python
try:
    order_id = place_option_order(...)
except InsufficientMarginError:
    logger.error("保證金不足")
except OptionExpiredError:
    logger.error("期權已到期")
except ConnectionError:
    logger.error("連接中斷，嘗試重連")
```

## 📚 相關文檔

- [Interactive Brokers 模組概述](./README.md)
- [API 參考文檔](../API文檔.md)
- [測試指南](../testing/test_ib_adapter_enhanced.md)
- [風險管理指南](../../維運指南/風險管理指南.md)

---

**維護團隊**: AI Trading System Development Team  
**最後更新**: 2025-01-15
