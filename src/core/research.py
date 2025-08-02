# %% [markdown]
# # 策略研究與因子測試
#
# 本筆記本用於研究交易策略和測試因子效力。

import sys

import matplotlib.pyplot as plt
import numpy as np

# %%
# 導入必要的庫
import pandas as pd
import seaborn as sns
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import TimeSeriesSplit
from statsmodels.tsa.stattools import adfuller

# 添加專案根目錄到路徑
sys.path.append("..")

# 設定繪圖風格
plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("Set2")

# %% [markdown]
# ## 1. 線性回歸測試
#
# 此函數用於測試因子與報酬之間的線性關係，返回 t 統計量和 p 值。


# %%
def linear_regression_test(feature, returns):
    """
    測試因子與報酬之間的線性關係

    Args:
        feature (pandas.Series or numpy.ndarray): 因子值
        returns (pandas.Series or numpy.ndarray): 報酬率

    Returns:
        tuple: (t_stat, p_value) t 統計量和 p 值
    """
    # 確保輸入為 numpy 數組
    if isinstance(feature, pd.Series):
        feature = feature.values
    if isinstance(returns, pd.Series):
        returns = returns.values

    # 移除 NaN 值
    mask = ~np.isnan(feature) & ~np.isnan(returns)
    feature = feature[mask]
    returns = returns[mask]

    if len(feature) == 0:
        return np.nan, np.nan

    # 添加常數項
    X = np.column_stack([np.ones(len(feature)), feature])

    # 計算回歸係數
    try:
        beta = np.linalg.inv(X.T @ X) @ X.T @ returns
    except np.linalg.LinAlgError:
        return np.nan, np.nan

    # 計算殘差
    residuals = returns - X @ beta

    # 計算標準誤差
    n = len(feature)
    k = X.shape[1]
    sigma_squared = np.sum(residuals**2) / (n - k)
    var_beta = sigma_squared * np.linalg.inv(X.T @ X)
    se_beta = np.sqrt(np.diag(var_beta))

    # 計算 t 統計量和 p 值
    t_stat = beta[1] / se_beta[1]
    p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - k))

    return t_stat, p_value


# 測試函數
np.random.seed(42)
test_feature = np.random.randn(100)
test_returns = 0.5 * test_feature + 0.1 + np.random.randn(100) * 0.2
t_stat, p_value = linear_regression_test(test_feature, test_returns)
print(f"t 統計量: {t_stat:.4f}, p 值: {p_value:.4f}")

# %% [markdown]
# ## 2. 隨機漫步測試
#
# 此函數用於測試價格序列是否為隨機漫步，使用 Augmented Dickey-Fuller 測試。


# %%
def random_walk_test(prices):
    """
    測試價格序列是否為隨機漫步

    Args:
        prices (pandas.Series or numpy.ndarray): 價格序列

    Returns:
        bool: 如果 p 值小於 0.05，則拒絕隨機漫步假設，返回 False；否則返回 True
    """
    # 確保輸入為 pandas Series
    if isinstance(prices, np.ndarray):
        prices = pd.Series(prices)

    # 移除 NaN 值
    prices = prices.dropna()

    if len(prices) < 20:
        print("警告: 價格序列太短，無法進行可靠的測試")
        return None

    # 進行 Augmented Dickey-Fuller 測試
    result = adfuller(prices)

    # 獲取 p 值
    p_value = result[1]

    # 輸出測試結果
    print(f"ADF 統計量: {result[0]:.4f}")
    print(f"p 值: {p_value:.4f}")
    print(f"臨界值:")
    for key, value in result[4].items():
        print(f"\t{key}: {value:.4f}")

    # 判斷是否為隨機漫步
    is_random_walk = p_value > 0.05
    if is_random_walk:
        print("無法拒絕隨機漫步假設，價格序列可能是隨機漫步")
    else:
        print("拒絕隨機漫步假設，價格序列可能不是隨機漫步")

    return is_random_walk


# 測試函數
np.random.seed(42)
# 生成隨機漫步序列
random_walk = np.cumsum(np.random.randn(1000))
# 生成非隨機漫步序列
mean_reverting = np.random.randn(1000) * 0.2 + np.sin(np.linspace(0, 10, 1000))

print("測試隨機漫步序列:")
is_random_walk1 = random_walk_test(random_walk)
print("\n測試非隨機漫步序列:")
is_random_walk2 = random_walk_test(mean_reverting)

# %% [markdown]
# ## 3. 交叉驗證
#
# 此函數用於對策略進行交叉驗證，評估策略的穩定性。


# %%
def cross_validation(strategy_fn, data, folds=5):
    """
    對策略進行交叉驗證

    Args:
        strategy_fn (function): 策略函數，接受 data 參數，返回訊號
        data (pandas.DataFrame): 輸入資料
        folds (int): 折數

    Returns:
        dict: 包含每折的績效指標
    """
    # 確保資料按時間排序
    if isinstance(data.index, pd.MultiIndex):
        # 如果是多重索引，假設第二個索引是日期
        data = data.sort_index(level=1)
    else:
        # 否則假設索引是日期
        data = data.sort_index()

    # 使用時間序列交叉驗證
    tscv = TimeSeriesSplit(n_splits=folds)

    results = []

    for train_idx, test_idx in tscv.split(data):
        # 分割資料
        train_data = data.iloc[train_idx]
        test_data = data.iloc[test_idx]

        # 生成訊號
        signals = strategy_fn(train_data)

        # 在測試集上評估策略
        if isinstance(signals, pd.DataFrame) and "signal" in signals.columns:
            # 修正：只選取 signals 與 test_data.index 的交集
            common_idx = signals.index.intersection(test_data.index)
            if len(common_idx) == 0:
                print("警告: 測試集日期不在訓練訊號索引中，略過本折。")
                results.append(
                    {
                        "total_return": np.nan,
                        "sharpe_ratio": np.nan,
                        "max_drawdown": np.nan,
                    }
                )
                continue
            test_signals = signals.loc[common_idx]
            test_data_fold = test_data.loc[common_idx]
            # 計算報酬率
            if "close" in test_data_fold.columns:
                price_col = "close"
            elif "Close" in test_data_fold.columns:
                price_col = "Close"
            else:
                price_col = test_data_fold.columns[0]  # 假設第一列是價格
            # 計算每日報酬率
            daily_returns = test_data_fold[price_col].pct_change()
            # 計算策略報酬率
            strategy_returns = daily_returns * test_signals["signal"].shift(1)
            # 計算累積報酬率
            cumulative_returns = (1 + strategy_returns).cumprod() - 1
            # 計算績效指標
            total_return = (
                cumulative_returns.iloc[-1] if len(cumulative_returns) > 0 else 0
            )
            sharpe_ratio = (
                strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
                if strategy_returns.std() > 0
                else 0
            )
            max_drawdown = (
                (cumulative_returns / cumulative_returns.cummax() - 1).min()
                if len(cumulative_returns) > 0
                else 0
            )
            results.append(
                {
                    "total_return": total_return,
                    "sharpe_ratio": sharpe_ratio,
                    "max_drawdown": max_drawdown,
                }
            )
        else:
            print("警告: 策略函數未返回包含 'signal' 列的 DataFrame")
            results.append(
                {"total_return": np.nan, "sharpe_ratio": np.nan, "max_drawdown": np.nan}
            )

    # 計算平均績效
    avg_results = {
        "total_return": np.mean([r["total_return"] for r in results]),
        "sharpe_ratio": np.mean([r["sharpe_ratio"] for r in results]),
        "max_drawdown": np.mean([r["max_drawdown"] for r in results]),
        "fold_results": results,
    }

    return avg_results


# 測試函數
def simple_ma_strategy(data):
    """簡單的移動平均策略"""
    if "close" in data.columns:
        price_col = "close"
    elif "Close" in data.columns:
        price_col = "Close"
    else:
        price_col = data.columns[0]

    # 計算短期和長期移動平均
    short_ma = data[price_col].rolling(window=5).mean()
    long_ma = data[price_col].rolling(window=20).mean()

    # 生成訊號
    signals = pd.DataFrame(index=data.index)
    signals["signal"] = 0
    signals.loc[short_ma > long_ma, "signal"] = 1
    signals.loc[short_ma < long_ma, "signal"] = -1

    return signals


# 生成測試資料
np.random.seed(42)
dates = pd.date_range(start="2020-01-01", periods=500, freq="D")
prices = pd.Series(np.cumsum(np.random.randn(500) * 0.1 + 0.01), index=dates)
test_data = pd.DataFrame({"close": prices})

# 進行交叉驗證
cv_results = cross_validation(simple_ma_strategy, test_data, folds=5)
print("交叉驗證結果:")
print(f"平均總報酬率: {cv_results['total_return']:.4f}")
print(f"平均夏普比率: {cv_results['sharpe_ratio']:.4f}")
print(f"平均最大回撤: {cv_results['max_drawdown']:.4f}")

# %% [markdown]
# ## 4. 滾動前進測試
#
# 此函數用於對策略進行滾動前進測試，模擬實際交易中的策略更新過程。


# %%
def walk_forward_test(strategy_fn, data, window=60, step=20):
    """
    對策略進行滾動前進測試

    Args:
        strategy_fn (function): 策略函數，接受 data 參數，返回訊號
        data (pandas.DataFrame): 輸入資料
        window (int): 訓練窗口大小（天數）
        step (int): 步長（天數）

    Returns:
        dict: 包含測試結果
    """
    # 確保資料按時間排序
    if isinstance(data.index, pd.MultiIndex):
        # 如果是多重索引，假設第二個索引是日期
        data = data.sort_index(level=1)
    else:
        # 否則假設索引是日期
        data = data.sort_index()

    # 初始化結果
    all_signals = pd.DataFrame(index=data.index)
    all_signals["signal"] = 0

    # 確定價格列
    if "close" in data.columns:
        price_col = "close"
    elif "Close" in data.columns:
        price_col = "Close"
    else:
        price_col = data.columns[0]  # 假設第一列是價格

    # 滾動前進測試
    for i in range(0, len(data) - window, step):
        # 分割資料
        train_data = data.iloc[i : i + window]
        if i + window + step > len(data):
            test_data = data.iloc[i + window :]
        else:
            test_data = data.iloc[i + window : i + window + step]

        # 生成訊號
        signals = strategy_fn(train_data)

        # 在測試集上應用訊號
        if isinstance(signals, pd.DataFrame) and "signal" in signals.columns:
            # 修正：只選取 signals 與 test_data.index 的交集
            common_idx = signals.index.intersection(test_data.index)
            if not test_data.empty and len(common_idx) > 0:
                test_signals = signals.loc[common_idx]
                all_signals.loc[common_idx, "signal"] = test_signals["signal"]
            elif not test_data.empty:
                print(
                    f"警告: 測試集日期 {test_data.index[0]} ~ {test_data.index[-1]} 不在訓練訊號索引中，略過本段。"
                )
        else:
            print("警告: 策略函數未返回包含 'signal' 列的 DataFrame")

    # 計算報酬率
    daily_returns = data[price_col].pct_change()

    # 計算策略報酬率
    strategy_returns = daily_returns * all_signals["signal"].shift(1)

    # 計算累積報酬率
    cumulative_returns = (1 + strategy_returns).cumprod() - 1

    # 計算績效指標
    total_return = cumulative_returns.iloc[-1] if len(cumulative_returns) > 0 else 0
    sharpe_ratio = (
        strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
        if strategy_returns.std() > 0
        else 0
    )
    max_drawdown = (
        (cumulative_returns / cumulative_returns.cummax() - 1).min()
        if len(cumulative_returns) > 0
        else 0
    )

    # 繪製累積報酬率圖
    plt.figure(figsize=(12, 6))
    cumulative_returns.plot()
    plt.title("策略累積報酬率")
    plt.xlabel("日期")
    plt.ylabel("累積報酬率")
    plt.grid(True)
    plt.show()

    return {
        "total_return": total_return,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "signals": all_signals,
        "returns": strategy_returns,
        "cumulative_returns": cumulative_returns,
    }


# 測試函數
wf_results = walk_forward_test(simple_ma_strategy, test_data, window=60, step=20)
print("滾動前進測試結果:")
print(f"總報酬率: {wf_results['total_return']:.4f}")
print(f"夏普比率: {wf_results['sharpe_ratio']:.4f}")
print(f"最大回撤: {wf_results['max_drawdown']:.4f}")

# %% [markdown]
# ## 5. 因子效力報告
#
# 此函數用於生成因子效力報告，包含每個因子的回歸係數、p 值、IC、回測報酬。


# %%
def factor_efficacy_report(factors, returns, periods=[1, 5, 20]):
    """
    生成因子效力報告

    Args:
        factors (pandas.DataFrame): 因子資料，每一列為一個因子
        returns (pandas.Series): 報酬率
        periods (list): 評估期間（天數）

    Returns:
        pandas.DataFrame: 因子效力報告
    """
    # 初始化結果
    results = []

    # 對每個因子進行評估
    for factor_name in factors.columns:
        factor = factors[factor_name]

        # 計算 IC（信息係數）
        ic_values = {}
        for period in periods:
            # 計算未來 period 天的報酬率
            future_return = returns.shift(-period)

            # 計算相關係數
            ic = factor.corr(future_return)
            ic_values[f"IC_{period}d"] = ic

        # 進行線性回歸測試
        t_stats = {}
        p_values = {}
        for period in periods:
            # 計算未來 period 天的報酬率
            future_return = returns.shift(-period)

            # 進行線性回歸測試
            t_stat, p_value = linear_regression_test(factor, future_return)
            t_stats[f"t_stat_{period}d"] = t_stat
            p_values[f"p_value_{period}d"] = p_value

        # 進行回測
        backtest_returns = {}
        for period in periods:
            # 生成訊號
            signals = pd.DataFrame(index=factor.index)
            signals["signal"] = 0

            # 根據因子值生成訊號
            quantiles = factor.quantile([0.2, 0.8])
            signals.loc[factor > quantiles[0.8], "signal"] = 1  # 買入因子值高的股票
            signals.loc[factor < quantiles[0.2], "signal"] = -1  # 賣出因子值低的股票

            # 計算未來 period 天的報酬率
            future_return = returns.shift(-period)

            # 計算策略報酬率
            strategy_return = (signals["signal"] * future_return).mean()
            backtest_returns[f"return_{period}d"] = strategy_return

        # 合併結果
        factor_result = {
            "factor": factor_name,
            **ic_values,
            **t_stats,
            **p_values,
            **backtest_returns,
        }

        results.append(factor_result)

    # 轉換為 DataFrame
    report = pd.DataFrame(results)

    # 設定索引
    report = report.set_index("factor")

    return report


# 測試函數
np.random.seed(42)
# 生成測試資料
dates = pd.date_range(start="2020-01-01", periods=500, freq="D")
returns = pd.Series(np.random.randn(500) * 0.01, index=dates)

# 生成因子
factors = pd.DataFrame(index=dates)
factors["momentum"] = returns.rolling(window=20).mean()  # 動量因子
factors["volatility"] = returns.rolling(window=20).std()  # 波動率因子
factors["reversal"] = -returns.rolling(window=5).mean()  # 反轉因子

# 生成因子效力報告
report = factor_efficacy_report(factors, returns, periods=[1, 5, 20])
print("因子效力報告:")
print(report)

# 繪製因子效力熱圖
plt.figure(figsize=(12, 8))
sns.heatmap(report, annot=True, cmap="RdYlGn", center=0, fmt=".4f")
plt.title("因子效力報告")
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 6. 因子組合與優化
#
# 此函數用於組合多個因子，並優化因子權重。


# %%
def optimize_factor_weights(factors, returns, method="equal", periods=[1, 5, 20]):
    """
    優化因子權重

    Args:
        factors (pandas.DataFrame): 因子資料，每一列為一個因子
        returns (pandas.Series): 報酬率
        method (str): 優化方法，'equal'、'ic'、'regression'
        periods (list): 評估期間（天數）

    Returns:
        pandas.Series: 因子權重
    """
    # 初始化權重
    weights = pd.Series(index=factors.columns)

    if method == "equal":
        # 等權重
        weights[:] = 1 / len(factors.columns)

    elif method == "ic":
        # 根據 IC 值設定權重
        ic_values = {}
        for factor_name in factors.columns:
            factor = factors[factor_name]

            # 計算 IC（信息係數）
            ic_sum = 0
            for period in periods:
                # 計算未來 period 天的報酬率
                future_return = returns.shift(-period)

                # 計算相關係數
                ic = factor.corr(future_return)
                ic_sum += ic

            ic_values[factor_name] = ic_sum / len(periods)

        # 轉換為 Series
        ic_series = pd.Series(ic_values)

        # 處理負值
        ic_series = ic_series.abs()

        # 標準化權重
        weights = ic_series / ic_series.sum()

    elif method == "regression":
        # 使用線性回歸設定權重
        X = factors.copy()

        # 標準化因子
        for col in X.columns:
            X[col] = (X[col] - X[col].mean()) / X[col].std()

        # 計算未來報酬率
        y = returns.shift(-periods[0])

        # 移除 NaN 值
        mask = ~X.isna().any(axis=1) & ~y.isna()
        X = X[mask]
        y = y[mask]

        # 進行線性回歸
        model = LinearRegression()
        model.fit(X, y)

        # 獲取係數
        coef = model.coef_

        # 設定權重
        for i, factor_name in enumerate(factors.columns):
            weights[factor_name] = coef[i]

        # 處理負值
        weights = weights.abs()

        # 標準化權重
        weights = weights / weights.sum()

    return weights


# 測試函數
weights = optimize_factor_weights(factors, returns, method="ic", periods=[1, 5, 20])
print("因子權重:")
print(weights)

# 計算組合因子
combined_factor = pd.Series(0, index=factors.index)
for factor_name, weight in weights.items():
    # 標準化因子
    standardized_factor = (
        factors[factor_name] - factors[factor_name].mean()
    ) / factors[factor_name].std()
    combined_factor += standardized_factor * weight

# 評估組合因子
print("\n組合因子評估:")
for period in [1, 5, 20]:
    future_return = returns.shift(-period)
    ic = combined_factor.corr(future_return)
    print(f"{period} 天 IC: {ic:.4f}")

# %% [markdown]
# ## 7. 保存因子效力報告
#
# 將因子效力報告保存為 CSV 檔案。

# %%
# 保存因子效力報告
report.to_csv("../results/factor_efficacy_report.csv")
print("因子效力報告已保存至 '../results/factor_efficacy_report.csv'")
