#!/usr/bin/env python3
"""
TA-LIB整合準備腳本
檢查系統環境並準備TA-LIB技術指標庫的整合
"""

import sys
import subprocess
import platform
from pathlib import Path

def check_system_requirements():
    """檢查系統需求"""
    print("🔍 檢查系統需求...")
    
    # 檢查Python版本
    python_version = sys.version_info
    print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 8):
        print("⚠️ 建議使用Python 3.8或更高版本")
    else:
        print("✅ Python版本符合要求")
    
    # 檢查操作系統
    os_name = platform.system()
    print(f"操作系統: {os_name}")
    
    if os_name == "Windows":
        print("💡 Windows系統需要Visual Studio Build Tools")
        print("   下載地址: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
    
    return True

def check_existing_packages():
    """檢查現有套件"""
    print("\n🔍 檢查現有套件...")
    
    required_packages = [
        'numpy', 'pandas', 'streamlit', 'yfinance', 'requests', 'sqlalchemy'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}: 已安裝")
        except ImportError:
            print(f"❌ {package}: 未安裝")
            missing_packages.append(package)
    
    # 檢查TA-LIB
    try:
        import talib
        print(f"✅ TA-Lib: 已安裝 (版本: {talib.__version__})")
        return True, missing_packages
    except ImportError:
        print("❌ TA-Lib: 未安裝")
        return False, missing_packages

def create_talib_installation_guide():
    """創建TA-LIB安裝指南"""
    print("\n📝 創建TA-LIB安裝指南...")
    
    guide_content = """# TA-LIB安裝指南

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
"""
    
    guide_path = Path("docs/TA-LIB安裝指南.md")
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print(f"✅ 安裝指南已創建: {guide_path}")

def create_indicators_module_structure():
    """創建技術指標模組結構"""
    print("\n🏗️ 創建技術指標模組結構...")
    
    # 創建目錄結構
    indicators_dir = Path("src/indicators")
    indicators_dir.mkdir(exist_ok=True)
    
    # 創建__init__.py
    init_file = indicators_dir / "__init__.py"
    init_content = '''"""
技術指標模組
提供基於TA-LIB的技術指標計算功能
"""

from .basic_indicators import BasicIndicators
from .advanced_indicators import AdvancedIndicators
from .custom_indicators import CustomIndicators

__all__ = ['BasicIndicators', 'AdvancedIndicators', 'CustomIndicators']
'''
    
    with open(init_file, 'w', encoding='utf-8') as f:
        f.write(init_content)
    
    # 創建基礎指標模組
    basic_file = indicators_dir / "basic_indicators.py"
    basic_content = '''"""
基礎技術指標
包含常用的技術指標計算
"""

import numpy as np
import pandas as pd

class BasicIndicators:
    """基礎技術指標類"""
    
    @staticmethod
    def sma(data: pd.Series, period: int = 20) -> pd.Series:
        """簡單移動平均線"""
        try:
            import talib
            return pd.Series(talib.SMA(data.values, timeperiod=period), index=data.index)
        except ImportError:
            # 備用實現
            return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int = 20) -> pd.Series:
        """指數移動平均線"""
        try:
            import talib
            return pd.Series(talib.EMA(data.values, timeperiod=period), index=data.index)
        except ImportError:
            # 備用實現
            return data.ewm(span=period).mean()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """相對強弱指標"""
        try:
            import talib
            return pd.Series(talib.RSI(data.values, timeperiod=period), index=data.index)
        except ImportError:
            # 備用實現
            delta = data.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
        """MACD指標"""
        try:
            import talib
            macd, signal_line, histogram = talib.MACD(data.values, 
                                                     fastperiod=fast, 
                                                     slowperiod=slow, 
                                                     signalperiod=signal)
            return {
                'macd': pd.Series(macd, index=data.index),
                'signal': pd.Series(signal_line, index=data.index),
                'histogram': pd.Series(histogram, index=data.index)
            }
        except ImportError:
            # 備用實現
            ema_fast = data.ewm(span=fast).mean()
            ema_slow = data.ewm(span=slow).mean()
            macd = ema_fast - ema_slow
            signal_line = macd.ewm(span=signal).mean()
            histogram = macd - signal_line
            return {
                'macd': macd,
                'signal': signal_line,
                'histogram': histogram
            }
'''
    
    with open(basic_file, 'w', encoding='utf-8') as f:
        f.write(basic_content)
    
    print(f"✅ 技術指標模組結構已創建: {indicators_dir}")

def create_integration_test():
    """創建整合測試腳本"""
    print("\n🧪 創建整合測試腳本...")
    
    test_file = Path("tests/test_talib_integration.py")
    test_content = '''"""
TA-LIB整合測試
"""

import pytest
import numpy as np
import pandas as pd
from src.indicators.basic_indicators import BasicIndicators

class TestTALibIntegration:
    """TA-LIB整合測試類"""
    
    def setup_method(self):
        """設置測試數據"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
        self.test_data = pd.Series(prices, index=dates)
    
    def test_sma_calculation(self):
        """測試SMA計算"""
        sma = BasicIndicators.sma(self.test_data, period=20)
        
        assert isinstance(sma, pd.Series)
        assert len(sma) == len(self.test_data)
        assert not sma.iloc[-1] != sma.iloc[-1]  # 檢查不是NaN
    
    def test_ema_calculation(self):
        """測試EMA計算"""
        ema = BasicIndicators.ema(self.test_data, period=20)
        
        assert isinstance(ema, pd.Series)
        assert len(ema) == len(self.test_data)
    
    def test_rsi_calculation(self):
        """測試RSI計算"""
        rsi = BasicIndicators.rsi(self.test_data, period=14)
        
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(self.test_data)
        # RSI應該在0-100之間
        valid_rsi = rsi.dropna()
        assert all(0 <= val <= 100 for val in valid_rsi)
    
    def test_macd_calculation(self):
        """測試MACD計算"""
        macd_result = BasicIndicators.macd(self.test_data)
        
        assert isinstance(macd_result, dict)
        assert 'macd' in macd_result
        assert 'signal' in macd_result
        assert 'histogram' in macd_result
        
        for key, series in macd_result.items():
            assert isinstance(series, pd.Series)
            assert len(series) == len(self.test_data)

if __name__ == "__main__":
    # 簡單測試運行
    test = TestTALibIntegration()
    test.setup_method()
    
    try:
        test.test_sma_calculation()
        print("✅ SMA測試通過")
        
        test.test_ema_calculation()
        print("✅ EMA測試通過")
        
        test.test_rsi_calculation()
        print("✅ RSI測試通過")
        
        test.test_macd_calculation()
        print("✅ MACD測試通過")
        
        print("🎉 所有測試通過!")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
'''
    
    test_file.parent.mkdir(exist_ok=True)
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print(f"✅ 整合測試已創建: {test_file}")

def main():
    """主函數"""
    print("🚀 開始TA-LIB整合準備...")
    print("=" * 60)
    
    # 1. 檢查系統需求
    check_system_requirements()
    
    # 2. 檢查現有套件
    talib_installed, missing_packages = check_existing_packages()
    
    # 3. 創建安裝指南
    create_talib_installation_guide()
    
    # 4. 創建模組結構
    create_indicators_module_structure()
    
    # 5. 創建整合測試
    create_integration_test()
    
    # 總結
    print("\n" + "=" * 60)
    print("📋 準備工作總結")
    print("=" * 60)
    print(f"TA-LIB狀態: {'✅ 已安裝' if talib_installed else '❌ 未安裝'}")
    
    if missing_packages:
        print(f"缺少套件: {', '.join(missing_packages)}")
    
    print("\n💡 下一步行動:")
    if not talib_installed:
        print("   1. 參考 docs/TA-LIB安裝指南.md 安裝TA-LIB")
        print("   2. 運行 python tests/test_talib_integration.py 測試")
    else:
        print("   1. 運行 python tests/test_talib_integration.py 測試")
        print("   2. 開始開發技術指標功能")
    
    print("   3. 整合到現有策略系統")
    print("   4. 添加到Web UI界面")

if __name__ == "__main__":
    main()
