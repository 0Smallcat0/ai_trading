# -*- coding: utf-8 -*-
"""
壓力測試模組

此模組提供各種壓力測試功能，包括：
- 市場崩盤模擬
- 流動性危機模擬
- 波動率衝擊模擬
- 相關性變化模擬
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

from src.config import LOG_LEVEL, RESULTS_DIR
from src.backtest.backtrader_integration import BacktestEngine

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class StressTester:
    """
    壓力測試器

    提供各種壓力測試功能。
    """
    
    def __init__(
        self,
        data: pd.DataFrame,
        backtest_func: Callable,
        output_dir: Optional[str] = None
    ):
        """
        初始化壓力測試器

        Args:
            data (pd.DataFrame): 原始資料
            backtest_func (Callable): 回測函數，接受資料，返回回測結果
            output_dir (Optional[str]): 輸出目錄
        """
        self.data = data.copy()
        self.backtest_func = backtest_func
        self.output_dir = output_dir or os.path.join(RESULTS_DIR, "stress_test", datetime.now().strftime("%Y%m%d%H%M%S"))
        
        # 創建輸出目錄
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 基準回測結果
        self.baseline_result = None

    def run_baseline(self) -> Dict[str, Any]:
        """
        執行基準回測

        Returns:
            Dict[str, Any]: 基準回測結果
        """
        # 執行基準回測
        self.baseline_result = self.backtest_func(self.data)
        
        return self.baseline_result

    def simulate_market_crash(
        self,
        crash_period: Tuple[str, str],
        crash_percentage: float = -0.2,
        recovery_period: Optional[Tuple[str, str]] = None,
        recovery_percentage: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        模擬市場崩盤

        Args:
            crash_period (Tuple[str, str]): 崩盤期間，格式為 (開始日期, 結束日期)
            crash_percentage (float): 崩盤幅度，負數表示下跌
            recovery_period (Optional[Tuple[str, str]]): 復甦期間，格式為 (開始日期, 結束日期)
            recovery_percentage (Optional[float]): 復甦幅度，正數表示上漲

        Returns:
            Dict[str, Any]: 壓力測試結果
        """
        # 複製原始資料
        stress_data = self.data.copy()
        
        # 確保日期欄位為 datetime 類型
        if "date" in stress_data.columns:
            stress_data["date"] = pd.to_datetime(stress_data["date"])
        
        # 模擬崩盤
        crash_start, crash_end = pd.to_datetime(crash_period[0]), pd.to_datetime(crash_period[1])
        crash_mask = (stress_data["date"] >= crash_start) & (stress_data["date"] <= crash_end)
        
        # 計算每日崩盤幅度
        crash_days = (crash_end - crash_start).days + 1
        daily_crash = (1 + crash_percentage) ** (1 / crash_days) - 1
        
        # 應用崩盤幅度
        for col in ["open", "high", "low", "close"]:
            if col in stress_data.columns:
                # 獲取崩盤前的最後一個價格
                last_price_before_crash = stress_data.loc[~crash_mask & (stress_data["date"] < crash_start), col].iloc[-1]
                
                # 生成崩盤期間的價格序列
                crash_prices = []
                current_price = last_price_before_crash
                
                for i in range(crash_days):
                    current_price = current_price * (1 + daily_crash)
                    crash_prices.append(current_price)
                
                # 應用崩盤價格
                stress_data.loc[crash_mask, col] = crash_prices
        
        # 模擬復甦
        if recovery_period is not None and recovery_percentage is not None:
            recovery_start, recovery_end = pd.to_datetime(recovery_period[0]), pd.to_datetime(recovery_period[1])
            recovery_mask = (stress_data["date"] >= recovery_start) & (stress_data["date"] <= recovery_end)
            
            # 計算每日復甦幅度
            recovery_days = (recovery_end - recovery_start).days + 1
            daily_recovery = (1 + recovery_percentage) ** (1 / recovery_days) - 1
            
            # 應用復甦幅度
            for col in ["open", "high", "low", "close"]:
                if col in stress_data.columns:
                    # 獲取復甦前的最後一個價格
                    last_price_before_recovery = stress_data.loc[~recovery_mask & (stress_data["date"] < recovery_start), col].iloc[-1]
                    
                    # 生成復甦期間的價格序列
                    recovery_prices = []
                    current_price = last_price_before_recovery
                    
                    for i in range(recovery_days):
                        current_price = current_price * (1 + daily_recovery)
                        recovery_prices.append(current_price)
                    
                    # 應用復甦價格
                    stress_data.loc[recovery_mask, col] = recovery_prices
        
        # 執行壓力測試
        stress_result = self.backtest_func(stress_data)
        
        # 保存壓力測試資料
        stress_data.to_csv(os.path.join(self.output_dir, "market_crash_data.csv"), index=False)
        
        # 繪製價格對比圖
        self._plot_price_comparison(
            self.data,
            stress_data,
            "市場崩盤模擬",
            os.path.join(self.output_dir, "market_crash_comparison.png")
        )
        
        return stress_result

    def simulate_liquidity_crisis(
        self,
        crisis_period: Tuple[str, str],
        volume_reduction: float = 0.8,
        slippage_increase: float = 5.0,
        spread_increase: float = 3.0
    ) -> Dict[str, Any]:
        """
        模擬流動性危機

        Args:
            crisis_period (Tuple[str, str]): 危機期間，格式為 (開始日期, 結束日期)
            volume_reduction (float): 成交量減少比例，範圍 [0, 1]
            slippage_increase (float): 滑價增加倍數
            spread_increase (float): 價差增加倍數

        Returns:
            Dict[str, Any]: 壓力測試結果
        """
        # 複製原始資料
        stress_data = self.data.copy()
        
        # 確保日期欄位為 datetime 類型
        if "date" in stress_data.columns:
            stress_data["date"] = pd.to_datetime(stress_data["date"])
        
        # 模擬流動性危機
        crisis_start, crisis_end = pd.to_datetime(crisis_period[0]), pd.to_datetime(crisis_period[1])
        crisis_mask = (stress_data["date"] >= crisis_start) & (stress_data["date"] <= crisis_end)
        
        # 減少成交量
        if "volume" in stress_data.columns:
            stress_data.loc[crisis_mask, "volume"] = stress_data.loc[crisis_mask, "volume"] * (1 - volume_reduction)
        
        # 增加價差（通過調整 high 和 low）
        if "high" in stress_data.columns and "low" in stress_data.columns:
            # 計算原始價差
            original_spread = stress_data["high"] - stress_data["low"]
            
            # 計算新價差
            new_spread = original_spread * spread_increase
            
            # 調整 high 和 low
            spread_diff = (new_spread - original_spread) / 2
            stress_data.loc[crisis_mask, "high"] = stress_data.loc[crisis_mask, "high"] + spread_diff[crisis_mask]
            stress_data.loc[crisis_mask, "low"] = stress_data.loc[crisis_mask, "low"] - spread_diff[crisis_mask]
        
        # 執行壓力測試（需要在回測函數中處理滑價增加）
        stress_result = self.backtest_func(stress_data, slippage_multiplier=slippage_increase)
        
        # 保存壓力測試資料
        stress_data.to_csv(os.path.join(self.output_dir, "liquidity_crisis_data.csv"), index=False)
        
        # 繪製成交量對比圖
        if "volume" in stress_data.columns:
            self._plot_volume_comparison(
                self.data,
                stress_data,
                "流動性危機模擬",
                os.path.join(self.output_dir, "liquidity_crisis_comparison.png")
            )
        
        return stress_result

    def simulate_volatility_shock(
        self,
        shock_period: Tuple[str, str],
        volatility_multiplier: float = 3.0
    ) -> Dict[str, Any]:
        """
        模擬波動率衝擊

        Args:
            shock_period (Tuple[str, str]): 衝擊期間，格式為 (開始日期, 結束日期)
            volatility_multiplier (float): 波動率增加倍數

        Returns:
            Dict[str, Any]: 壓力測試結果
        """
        # 複製原始資料
        stress_data = self.data.copy()
        
        # 確保日期欄位為 datetime 類型
        if "date" in stress_data.columns:
            stress_data["date"] = pd.to_datetime(stress_data["date"])
        
        # 模擬波動率衝擊
        shock_start, shock_end = pd.to_datetime(shock_period[0]), pd.to_datetime(shock_period[1])
        shock_mask = (stress_data["date"] >= shock_start) & (stress_data["date"] <= shock_end)
        
        # 計算每日收益率
        if "close" in stress_data.columns:
            stress_data["return"] = stress_data["close"].pct_change()
            
            # 獲取衝擊期間的收益率
            shock_returns = stress_data.loc[shock_mask, "return"]
            
            # 計算衝擊期間的平均收益率和標準差
            mean_return = shock_returns.mean()
            std_return = shock_returns.std()
            
            # 生成新的收益率（保持平均值不變，增加標準差）
            new_std_return = std_return * volatility_multiplier
            new_returns = np.random.normal(mean_return, new_std_return, len(shock_returns))
            
            # 應用新的收益率
            stress_data.loc[shock_mask, "return"] = new_returns
            
            # 重新計算價格
            last_price_before_shock = stress_data.loc[~shock_mask & (stress_data["date"] < shock_start), "close"].iloc[-1]
            
            # 計算累積收益率
            cum_returns = (1 + stress_data.loc[shock_mask, "return"]).cumprod()
            
            # 計算新價格
            new_prices = last_price_before_shock * cum_returns
            
            # 應用新價格
            stress_data.loc[shock_mask, "close"] = new_prices
            
            # 調整 open, high, low
            if "open" in stress_data.columns and "high" in stress_data.columns and "low" in stress_data.columns:
                # 計算與收盤價的比例
                open_ratio = stress_data.loc[shock_mask, "open"] / stress_data.loc[shock_mask, "close"].shift(1)
                high_ratio = stress_data.loc[shock_mask, "high"] / stress_data.loc[shock_mask, "close"]
                low_ratio = stress_data.loc[shock_mask, "low"] / stress_data.loc[shock_mask, "close"]
                
                # 應用比例計算新價格
                stress_data.loc[shock_mask, "open"] = stress_data.loc[shock_mask, "close"].shift(1) * open_ratio
                stress_data.loc[shock_mask, "high"] = stress_data.loc[shock_mask, "close"] * high_ratio
                stress_data.loc[shock_mask, "low"] = stress_data.loc[shock_mask, "close"] * low_ratio
        
        # 執行壓力測試
        stress_result = self.backtest_func(stress_data)
        
        # 保存壓力測試資料
        stress_data.to_csv(os.path.join(self.output_dir, "volatility_shock_data.csv"), index=False)
        
        # 繪製波動率對比圖
        self._plot_volatility_comparison(
            self.data,
            stress_data,
            "波動率衝擊模擬",
            os.path.join(self.output_dir, "volatility_shock_comparison.png")
        )
        
        return stress_result

    def simulate_correlation_change(
        self,
        assets: List[str],
        change_period: Tuple[str, str],
        new_correlation: float
    ) -> Dict[str, Any]:
        """
        模擬相關性變化

        Args:
            assets (List[str]): 資產列表
            change_period (Tuple[str, str]): 變化期間，格式為 (開始日期, 結束日期)
            new_correlation (float): 新的相關係數，範圍 [-1, 1]

        Returns:
            Dict[str, Any]: 壓力測試結果
        """
        # 檢查資產數量
        if len(assets) < 2:
            logger.error("至少需要兩個資產才能模擬相關性變化")
            raise ValueError("至少需要兩個資產才能模擬相關性變化")
        
        # 複製原始資料
        stress_data = self.data.copy()
        
        # 確保日期欄位為 datetime 類型
        if "date" in stress_data.columns:
            stress_data["date"] = pd.to_datetime(stress_data["date"])
        
        # 模擬相關性變化
        change_start, change_end = pd.to_datetime(change_period[0]), pd.to_datetime(change_period[1])
        change_mask = (stress_data["date"] >= change_start) & (stress_data["date"] <= change_end)
        
        # 獲取資產價格
        asset_prices = {}
        for asset in assets:
            if f"{asset}_close" in stress_data.columns:
                asset_prices[asset] = stress_data[f"{asset}_close"]
            elif "symbol" in stress_data.columns and "close" in stress_data.columns:
                asset_data = stress_data[stress_data["symbol"] == asset]
                asset_prices[asset] = asset_data["close"]
            else:
                logger.error(f"找不到資產 {asset} 的價格資料")
                raise ValueError(f"找不到資產 {asset} 的價格資料")
        
        # 計算資產收益率
        asset_returns = {}
        for asset, prices in asset_prices.items():
            asset_returns[asset] = prices.pct_change()
        
        # 獲取變化期間的收益率
        change_returns = {}
        for asset, returns in asset_returns.items():
            change_returns[asset] = returns[change_mask]
        
        # 計算原始相關係數
        returns_df = pd.DataFrame(change_returns)
        original_corr = returns_df.corr()
        
        # 生成新的收益率（保持邊際分佈不變，改變相關性）
        # 使用 Cholesky 分解
        n_assets = len(assets)
        n_days = len(change_returns[assets[0]])
        
        # 計算目標相關係數矩陣
        target_corr = np.ones((n_assets, n_assets)) * new_correlation
        np.fill_diagonal(target_corr, 1.0)
        
        # 計算標準差
        std_devs = np.array([change_returns[asset].std() for asset in assets])
        
        # 計算目標協方差矩陣
        target_cov = np.outer(std_devs, std_devs) * target_corr
        
        # Cholesky 分解
        L = np.linalg.cholesky(target_cov)
        
        # 生成獨立的標準正態隨機變數
        Z = np.random.normal(0, 1, (n_days, n_assets))
        
        # 生成相關的標準正態隨機變數
        X = Z @ L.T
        
        # 轉換為原始分佈
        new_returns = {}
        for i, asset in enumerate(assets):
            # 計算平均收益率
            mean_return = change_returns[asset].mean()
            
            # 生成新的收益率
            new_returns[asset] = X[:, i] * std_devs[i] + mean_return
        
        # 應用新的收益率
        for i, asset in enumerate(assets):
            # 獲取變化前的最後一個價格
            last_price_before_change = asset_prices[asset][~change_mask & (stress_data["date"] < change_start)].iloc[-1]
            
            # 計算累積收益率
            cum_returns = (1 + pd.Series(new_returns[asset])).cumprod()
            
            # 計算新價格
            new_prices = last_price_before_change * cum_returns
            
            # 應用新價格
            if f"{asset}_close" in stress_data.columns:
                stress_data.loc[change_mask, f"{asset}_close"] = new_prices.values
            elif "symbol" in stress_data.columns and "close" in stress_data.columns:
                stress_data.loc[change_mask & (stress_data["symbol"] == asset), "close"] = new_prices.values
        
        # 執行壓力測試
        stress_result = self.backtest_func(stress_data)
        
        # 保存壓力測試資料
        stress_data.to_csv(os.path.join(self.output_dir, "correlation_change_data.csv"), index=False)
        
        # 繪製相關性對比圖
        self._plot_correlation_comparison(
            self.data,
            stress_data,
            assets,
            change_period,
            "相關性變化模擬",
            os.path.join(self.output_dir, "correlation_change_comparison.png")
        )
        
        return stress_result

    def _plot_price_comparison(
        self,
        original_data: pd.DataFrame,
        stress_data: pd.DataFrame,
        title: str,
        filename: str
    ) -> None:
        """
        繪製價格對比圖

        Args:
            original_data (pd.DataFrame): 原始資料
            stress_data (pd.DataFrame): 壓力測試資料
            title (str): 圖表標題
            filename (str): 檔案名稱
        """
        plt.figure(figsize=(12, 6))
        
        # 繪製原始價格
        if "date" in original_data.columns and "close" in original_data.columns:
            plt.plot(original_data["date"], original_data["close"], label="原始價格")
        
        # 繪製壓力測試價格
        if "date" in stress_data.columns and "close" in stress_data.columns:
            plt.plot(stress_data["date"], stress_data["close"], label="壓力測試價格", alpha=0.7)
        
        # 設定圖表
        plt.title(title)
        plt.xlabel("日期")
        plt.ylabel("價格")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        
        # 保存圖表
        plt.savefig(filename)
        plt.close()

    def _plot_volume_comparison(
        self,
        original_data: pd.DataFrame,
        stress_data: pd.DataFrame,
        title: str,
        filename: str
    ) -> None:
        """
        繪製成交量對比圖

        Args:
            original_data (pd.DataFrame): 原始資料
            stress_data (pd.DataFrame): 壓力測試資料
            title (str): 圖表標題
            filename (str): 檔案名稱
        """
        plt.figure(figsize=(12, 6))
        
        # 繪製原始成交量
        if "date" in original_data.columns and "volume" in original_data.columns:
            plt.plot(original_data["date"], original_data["volume"], label="原始成交量")
        
        # 繪製壓力測試成交量
        if "date" in stress_data.columns and "volume" in stress_data.columns:
            plt.plot(stress_data["date"], stress_data["volume"], label="壓力測試成交量", alpha=0.7)
        
        # 設定圖表
        plt.title(title)
        plt.xlabel("日期")
        plt.ylabel("成交量")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        
        # 保存圖表
        plt.savefig(filename)
        plt.close()

    def _plot_volatility_comparison(
        self,
        original_data: pd.DataFrame,
        stress_data: pd.DataFrame,
        title: str,
        filename: str,
        window: int = 20
    ) -> None:
        """
        繪製波動率對比圖

        Args:
            original_data (pd.DataFrame): 原始資料
            stress_data (pd.DataFrame): 壓力測試資料
            title (str): 圖表標題
            filename (str): 檔案名稱
            window (int): 波動率計算窗口
        """
        plt.figure(figsize=(12, 6))
        
        # 計算原始波動率
        if "close" in original_data.columns:
            original_returns = original_data["close"].pct_change()
            original_volatility = original_returns.rolling(window=window).std() * np.sqrt(252)
            
            # 繪製原始波動率
            if "date" in original_data.columns:
                plt.plot(original_data["date"], original_volatility, label="原始波動率")
        
        # 計算壓力測試波動率
        if "close" in stress_data.columns:
            stress_returns = stress_data["close"].pct_change()
            stress_volatility = stress_returns.rolling(window=window).std() * np.sqrt(252)
            
            # 繪製壓力測試波動率
            if "date" in stress_data.columns:
                plt.plot(stress_data["date"], stress_volatility, label="壓力測試波動率", alpha=0.7)
        
        # 設定圖表
        plt.title(title)
        plt.xlabel("日期")
        plt.ylabel("年化波動率")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        
        # 保存圖表
        plt.savefig(filename)
        plt.close()

    def _plot_correlation_comparison(
        self,
        original_data: pd.DataFrame,
        stress_data: pd.DataFrame,
        assets: List[str],
        change_period: Tuple[str, str],
        title: str,
        filename: str
    ) -> None:
        """
        繪製相關性對比圖

        Args:
            original_data (pd.DataFrame): 原始資料
            stress_data (pd.DataFrame): 壓力測試資料
            assets (List[str]): 資產列表
            change_period (Tuple[str, str]): 變化期間
            title (str): 圖表標題
            filename (str): 檔案名稱
        """
        # 創建子圖
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))
        
        # 獲取變化期間
        change_start, change_end = pd.to_datetime(change_period[0]), pd.to_datetime(change_period[1])
        
        # 獲取原始資料中的變化期間
        original_change_mask = (original_data["date"] >= change_start) & (original_data["date"] <= change_end)
        original_change_data = original_data[original_change_mask]
        
        # 獲取壓力測試資料中的變化期間
        stress_change_mask = (stress_data["date"] >= change_start) & (stress_data["date"] <= change_end)
        stress_change_data = stress_data[stress_change_mask]
        
        # 計算原始相關係數
        original_returns = {}
        for asset in assets:
            if f"{asset}_close" in original_change_data.columns:
                original_returns[asset] = original_change_data[f"{asset}_close"].pct_change().dropna()
            elif "symbol" in original_change_data.columns and "close" in original_change_data.columns:
                asset_data = original_change_data[original_change_data["symbol"] == asset]
                original_returns[asset] = asset_data["close"].pct_change().dropna()
        
        original_returns_df = pd.DataFrame(original_returns)
        original_corr = original_returns_df.corr()
        
        # 計算壓力測試相關係數
        stress_returns = {}
        for asset in assets:
            if f"{asset}_close" in stress_change_data.columns:
                stress_returns[asset] = stress_change_data[f"{asset}_close"].pct_change().dropna()
            elif "symbol" in stress_change_data.columns and "close" in stress_change_data.columns:
                asset_data = stress_change_data[stress_change_data["symbol"] == asset]
                stress_returns[asset] = asset_data["close"].pct_change().dropna()
        
        stress_returns_df = pd.DataFrame(stress_returns)
        stress_corr = stress_returns_df.corr()
        
        # 繪製原始相關係數熱圖
        sns.heatmap(original_corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1, ax=axes[0])
        axes[0].set_title("原始相關係數")
        
        # 繪製壓力測試相關係數熱圖
        sns.heatmap(stress_corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1, ax=axes[1])
        axes[1].set_title("壓力測試相關係數")
        
        # 設定圖表
        plt.suptitle(title)
        plt.tight_layout()
        
        # 保存圖表
        plt.savefig(filename)
        plt.close()
