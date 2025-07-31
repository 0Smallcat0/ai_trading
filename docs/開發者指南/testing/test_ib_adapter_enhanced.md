# IB Adapter 增強測試指南

## 📋 概述

本文檔提供 Interactive Brokers (IB) 適配器的完整測試指南，包括單元測試、整合測試、性能測試和故障測試。

**版本**: v1.0  
**最後更新**: 2025-01-15  
**測試覆蓋率**: 90%+

## 🧪 測試架構

### 測試分類

```
tests/
├── unit/                   # 單元測試
│   ├── test_ib_adapter.py
│   ├── test_ib_wrapper.py
│   ├── test_ib_contracts.py
│   └── test_ib_options.py
├── integration/            # 整合測試
│   ├── test_ib_connection.py
│   ├── test_ib_trading.py
│   └── test_ib_market_data.py
├── performance/            # 性能測試
│   ├── test_ib_latency.py
│   └── test_ib_throughput.py
└── fixtures/               # 測試夾具
    ├── mock_ib_client.py
    └── test_data.py
```

## 🔧 測試環境設置

### 依賴安裝

```bash
# 安裝測試依賴
pip install pytest pytest-cov pytest-mock pytest-asyncio

# 安裝 IB API
pip install ibapi

# 安裝其他測試工具
pip install factory-boy freezegun
```

### 測試配置

```python
# conftest.py
import pytest
from unittest.mock import Mock, MagicMock
from src.execution.ib_adapter import IBAdapter

@pytest.fixture
def mock_ib_client():
    """模擬 IB 客戶端"""
    client = Mock()
    client.connect.return_value = True
    client.disconnect.return_value = True
    client.isConnected.return_value = True
    return client

@pytest.fixture
def ib_adapter(mock_ib_client):
    """IB 適配器測試夾具"""
    adapter = IBAdapter(host="127.0.0.1", port=7497, client_id=1)
    adapter.client = mock_ib_client
    return adapter
```

## 🧪 單元測試

### 1. 連接測試

```python
def test_ib_adapter_connection(ib_adapter, mock_ib_client):
    """測試 IB 適配器連接功能"""
    # 測試連接
    result = ib_adapter.connect()
    assert result is True
    mock_ib_client.connect.assert_called_once()
    
    # 測試斷開連接
    result = ib_adapter.disconnect()
    assert result is True
    mock_ib_client.disconnect.assert_called_once()

def test_connection_retry(ib_adapter, mock_ib_client):
    """測試連接重試機制"""
    # 模擬連接失敗
    mock_ib_client.connect.side_effect = [False, False, True]
    
    result = ib_adapter.connect(max_retries=3)
    assert result is True
    assert mock_ib_client.connect.call_count == 3
```

### 2. 訂單測試

```python
def test_place_order(ib_adapter, mock_ib_client):
    """測試下單功能"""
    from src.execution.broker_base import Order, OrderType
    
    # 創建測試訂單
    order = Order(
        stock_id="AAPL",
        action="buy",
        quantity=100,
        order_type=OrderType.MARKET
    )
    
    # 模擬下單成功
    mock_ib_client.placeOrder.return_value = None
    ib_adapter._next_order_id = 1
    
    order_id = ib_adapter.place_order(order)
    assert order_id == "1"
    mock_ib_client.placeOrder.assert_called_once()

def test_cancel_order(ib_adapter, mock_ib_client):
    """測試撤單功能"""
    order_id = "123"
    
    result = ib_adapter.cancel_order(order_id)
    assert result is True
    mock_ib_client.cancelOrder.assert_called_once_with(123)
```

### 3. 期權測試

```python
def test_option_contract_creation():
    """測試期權合約創建"""
    from src.execution.ib_contracts import IBContractManager
    
    contract_manager = IBContractManager()
    
    contract = contract_manager.create_option_contract(
        symbol="AAPL",
        expiry="20241220",
        strike=150.0,
        right="C"
    )
    
    assert contract.symbol == "AAPL"
    assert contract.lastTradeDateOrContractMonth == "20241220"
    assert contract.strike == 150.0
    assert contract.right == "C"

def test_option_greeks_calculation():
    """測試期權 Greeks 計算"""
    from src.execution.ib_options import IBOptionsManager
    
    options_manager = IBOptionsManager()
    
    greeks = options_manager.calculate_greeks(
        underlying_price=150.0,
        strike=150.0,
        time_to_expiry=30,
        risk_free_rate=0.05,
        volatility=0.25,
        option_type="call"
    )
    
    assert 0 < greeks['delta'] < 1
    assert greeks['gamma'] > 0
    assert greeks['theta'] < 0
    assert greeks['vega'] > 0
```

## 🔗 整合測試

### 1. 端到端交易測試

```python
@pytest.mark.integration
def test_end_to_end_trading():
    """端到端交易測試"""
    # 注意：此測試需要實際的 IB 連接
    adapter = IBAdapter(host="127.0.0.1", port=7497, client_id=999)
    
    try:
        # 1. 連接
        assert adapter.connect()
        
        # 2. 獲取帳戶資訊
        account_info = adapter.get_account_info()
        assert account_info is not None
        
        # 3. 獲取持倉
        positions = adapter.get_positions()
        assert isinstance(positions, list)
        
        # 4. 下單 (小額測試)
        order = Order(
            stock_id="AAPL",
            action="buy",
            quantity=1,
            order_type=OrderType.LIMIT,
            price=1.0  # 極低價格，不會成交
        )
        
        order_id = adapter.place_order(order)
        assert order_id is not None
        
        # 5. 撤單
        time.sleep(1)  # 等待訂單提交
        result = adapter.cancel_order(order_id)
        assert result is True
        
    finally:
        adapter.disconnect()
```

### 2. 市場數據測試

```python
@pytest.mark.integration
def test_market_data_subscription():
    """市場數據訂閱測試"""
    adapter = IBAdapter(host="127.0.0.1", port=7497, client_id=999)
    
    try:
        assert adapter.connect()
        
        # 訂閱市場數據
        symbols = ["AAPL", "GOOGL"]
        result = adapter.subscribe_market_data(symbols)
        assert result is True
        
        # 等待數據更新
        time.sleep(5)
        
        # 檢查數據是否更新
        for symbol in symbols:
            price = adapter.get_last_price(symbol)
            assert price > 0
            
    finally:
        adapter.disconnect()
```

## ⚡ 性能測試

### 1. 延遲測試

```python
@pytest.mark.performance
def test_order_latency():
    """測試下單延遲"""
    import time
    
    adapter = IBAdapter(host="127.0.0.1", port=7497, client_id=999)
    
    try:
        assert adapter.connect()
        
        latencies = []
        
        for i in range(10):
            order = Order(
                stock_id="AAPL",
                action="buy",
                quantity=1,
                order_type=OrderType.LIMIT,
                price=1.0
            )
            
            start_time = time.time()
            order_id = adapter.place_order(order)
            end_time = time.time()
            
            latency = (end_time - start_time) * 1000  # 毫秒
            latencies.append(latency)
            
            # 立即撤單
            adapter.cancel_order(order_id)
            time.sleep(0.1)
        
        avg_latency = sum(latencies) / len(latencies)
        print(f"平均下單延遲: {avg_latency:.2f}ms")
        
        # 斷言延遲小於 200ms
        assert avg_latency < 200
        
    finally:
        adapter.disconnect()
```

### 2. 吞吐量測試

```python
@pytest.mark.performance
def test_order_throughput():
    """測試訂單吞吐量"""
    import concurrent.futures
    import time
    
    adapter = IBAdapter(host="127.0.0.1", port=7497, client_id=999)
    
    try:
        assert adapter.connect()
        
        def place_and_cancel_order(i):
            order = Order(
                stock_id="AAPL",
                action="buy",
                quantity=1,
                order_type=OrderType.LIMIT,
                price=1.0
            )
            
            order_id = adapter.place_order(order)
            time.sleep(0.1)
            adapter.cancel_order(order_id)
            return order_id
        
        start_time = time.time()
        
        # 並發下單
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(place_and_cancel_order, i) for i in range(50)]
            results = [future.result() for future in futures]
        
        end_time = time.time()
        
        duration = end_time - start_time
        throughput = len(results) / duration
        
        print(f"訂單吞吐量: {throughput:.2f} 訂單/秒")
        
        # 斷言吞吐量大於 10 訂單/秒
        assert throughput > 10
        
    finally:
        adapter.disconnect()
```

## 🚨 故障測試

### 1. 網路中斷測試

```python
@pytest.mark.fault_tolerance
def test_network_disconnection():
    """測試網路中斷處理"""
    adapter = IBAdapter(host="127.0.0.1", port=7497, client_id=999)
    
    try:
        assert adapter.connect()
        
        # 模擬網路中斷
        adapter.client.disconnect()
        
        # 檢查連接狀態
        assert not adapter.is_connected()
        
        # 測試自動重連
        result = adapter.reconnect()
        assert result is True
        assert adapter.is_connected()
        
    finally:
        adapter.disconnect()
```

### 2. 異常處理測試

```python
def test_invalid_order_handling(ib_adapter, mock_ib_client):
    """測試無效訂單處理"""
    from src.execution.broker_base import Order, OrderType
    
    # 測試無效股票代碼
    invalid_order = Order(
        stock_id="INVALID",
        action="buy",
        quantity=100,
        order_type=OrderType.MARKET
    )
    
    # 模擬 API 錯誤
    mock_ib_client.placeOrder.side_effect = Exception("Invalid symbol")
    
    with pytest.raises(Exception):
        ib_adapter.place_order(invalid_order)
```

## 📊 測試報告

### 執行測試

```bash
# 執行所有測試
python -m pytest tests/ -v

# 執行特定測試類型
python -m pytest tests/unit/ -v                    # 單元測試
python -m pytest tests/integration/ -v             # 整合測試
python -m pytest -m performance tests/ -v          # 性能測試
python -m pytest -m fault_tolerance tests/ -v      # 故障測試

# 生成覆蓋率報告
python -m pytest --cov=src.execution tests/ --cov-report=html

# 生成詳細報告
python -m pytest --html=report.html --self-contained-html
```

### 持續集成

```yaml
# .github/workflows/test.yml
name: IB Adapter Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run unit tests
      run: pytest tests/unit/ -v
    
    - name: Generate coverage report
      run: pytest --cov=src.execution tests/unit/ --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v1
```

---

**維護團隊**: AI Trading System Testing Team  
**最後更新**: 2025-01-15
