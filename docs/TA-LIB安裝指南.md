# TA-LIB安裝指南

## Windows安裝方法

### 方法1: 使用預編譯輪子 (推薦)
```bash
# 下載預編譯輪子
# 訪問: https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
# 選擇對應Python版本的.whl文件

# 安裝下載的輪子文件
pip install TA_Lib-0.4.24-cp39-cp39-win_amd64.whl
```

### 方法2: 使用conda (推薦)
```bash
conda install -c conda-forge ta-lib
```

### 方法3: 從源碼編譯
```bash
# 1. 安裝Visual Studio Build Tools
# 2. 下載TA-LIB C庫
# 3. 編譯安裝
pip install TA-Lib
```

## Linux/Mac安裝方法
```bash
# Ubuntu/Debian
sudo apt-get install ta-lib-dev

# CentOS/RHEL
sudo yum install ta-lib-devel

# macOS
brew install ta-lib

# 然後安裝Python包
pip install TA-Lib
```

## 驗證安裝
```python
import talib
print(f"TA-Lib版本: {talib.__version__}")

# 測試基本功能
import numpy as np
close_prices = np.random.random(100)
sma = talib.SMA(close_prices, timeperiod=30)
print("SMA計算成功!")
```

## 常見問題

### 問題1: Microsoft Visual C++ 14.0 is required
**解決方案**: 安裝Visual Studio Build Tools
- 下載: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- 安裝時選擇"C++ build tools"

### 問題2: 找不到ta_lib庫
**解決方案**: 
1. 確認已安裝TA-LIB C庫
2. 設置環境變量指向庫文件位置
3. 使用conda安裝 (自動處理依賴)

### 問題3: 版本不兼容
**解決方案**: 
1. 檢查Python版本與輪子文件匹配
2. 使用虛擬環境隔離依賴
3. 考慮使用Docker容器
