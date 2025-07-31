"""
統一回測執行引擎

此模組整合了原本的回測執行邏輯，提供高效的回測計算核心。
支援多種回測模式和優化算法。
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BacktestEngine:
    """統一回測執行引擎
    
    提供高效的回測計算核心，支援：
    - 向量化回測計算
    - 多種訂單類型
    - 滑點和手續費模擬
    - 風險控制
    - 績效追蹤
    """

    def __init__(self):
        """初始化回測引擎"""
        self.reset()
        logger.info("回測引擎已初始化")

    def reset(self) -> None:
        """重置引擎狀態"""
        self.positions = {}
        self.cash = 0
        self.portfolio_value = 0
        self.trades = []
        self.daily_returns = []
        self.daily_values = []
        self.daily_positions = []

    def run_backtest(
        self,
        signals: pd.DataFrame,
        market_data: pd.DataFrame,
        initial_capital: float = 100000,
        commission: float = 0.001,
        slippage: float = 0.001,
        **kwargs
    ) -> Dict[str, Any]:
        """執行回測
        
        Args:
            signals: 交易訊號 DataFrame
            market_data: 市場數據 DataFrame
            initial_capital: 初始資金
            commission: 手續費率
            slippage: 滑點率
            **kwargs: 其他參數
            
        Returns:
            Dict[str, Any]: 回測結果
            
        Raises:
            ValueError: 當輸入數據無效時
            RuntimeError: 當回測執行失敗時
        """
        try:
            # 重置引擎狀態
            self.reset()
            self.cash = initial_capital
            self.portfolio_value = initial_capital
            
            # 驗證輸入數據
            self._validate_inputs(signals, market_data)
            
            # 對齊數據
            aligned_signals, aligned_prices = self._align_data(signals, market_data)
            
            # 執行逐日回測
            for date in aligned_signals.index:
                self._process_trading_day(
                    date, aligned_signals, aligned_prices, commission, slippage
                )
            
            # 生成回測結果
            results = self._generate_results(initial_capital)
            
            logger.info("回測執行完成")
            return results
            
        except Exception as e:
            logger.error("回測執行失敗: %s", e, exc_info=True)
            raise RuntimeError(f"回測執行失敗: {e}") from e

    def _validate_inputs(self, signals: pd.DataFrame, market_data: pd.DataFrame) -> None:
        """驗證輸入數據
        
        Args:
            signals: 交易訊號
            market_data: 市場數據
            
        Raises:
            ValueError: 當數據無效時
        """
        if signals.empty:
            raise ValueError("交易訊號不能為空")
        
        if market_data.empty:
            raise ValueError("市場數據不能為空")
        
        # 檢查必要的列
        required_signal_cols = ['symbol', 'signal', 'weight']
        missing_signal_cols = [col for col in required_signal_cols if col not in signals.columns]
        if missing_signal_cols:
            raise ValueError(f"交易訊號缺少必要列: {missing_signal_cols}")
        
        required_price_cols = ['symbol', 'close', 'volume']
        missing_price_cols = [col for col in required_price_cols if col not in market_data.columns]
        if missing_price_cols:
            raise ValueError(f"市場數據缺少必要列: {missing_price_cols}")

    def _align_data(self, signals: pd.DataFrame, market_data: pd.DataFrame) -> tuple:
        """對齊訊號和價格數據
        
        Args:
            signals: 交易訊號
            market_data: 市場數據
            
        Returns:
            tuple: (對齊的訊號, 對齊的價格)
        """
        # 確保索引為日期
        if not isinstance(signals.index, pd.DatetimeIndex):
            signals = signals.set_index('date') if 'date' in signals.columns else signals
        
        if not isinstance(market_data.index, pd.DatetimeIndex):
            market_data = market_data.set_index('date') if 'date' in market_data.columns else market_data
        
        # 找到共同的日期範圍
        common_dates = signals.index.intersection(market_data.index)
        
        if len(common_dates) == 0:
            raise ValueError("訊號和市場數據沒有共同的日期")
        
        # 對齊數據
        aligned_signals = signals.loc[common_dates]
        aligned_prices = market_data.loc[common_dates]
        
        return aligned_signals, aligned_prices

    def _process_trading_day(
        self,
        date: pd.Timestamp,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        commission: float,
        slippage: float
    ) -> None:
        """處理單個交易日
        
        Args:
            date: 交易日期
            signals: 交易訊號
            prices: 價格數據
            commission: 手續費率
            slippage: 滑點率
        """
        # 獲取當日訊號和價格
        day_signals = signals.loc[date] if date in signals.index else pd.DataFrame()
        day_prices = prices.loc[date] if date in prices.index else pd.DataFrame()
        
        if day_signals.empty or day_prices.empty:
            # 更新投資組合價值（使用當前價格）
            self._update_portfolio_value(date, day_prices)
            return
        
        # 處理交易訊號
        if isinstance(day_signals, pd.Series):
            day_signals = day_signals.to_frame().T
        
        if isinstance(day_prices, pd.Series):
            day_prices = day_prices.to_frame().T
        
        # 執行交易
        for _, signal_row in day_signals.iterrows():
            symbol = signal_row['symbol']
            signal = signal_row['signal']
            weight = signal_row.get('weight', 0)
            
            # 獲取價格
            price_row = day_prices[day_prices['symbol'] == symbol]
            if price_row.empty:
                continue
            
            price = price_row.iloc[0]['close']
            
            # 執行交易
            self._execute_trade(date, symbol, signal, weight, price, commission, slippage)
        
        # 更新投資組合價值
        self._update_portfolio_value(date, day_prices)

    def _execute_trade(
        self,
        date: pd.Timestamp,
        symbol: str,
        signal: float,
        weight: float,
        price: float,
        commission: float,
        slippage: float
    ) -> None:
        """執行交易
        
        Args:
            date: 交易日期
            symbol: 股票代碼
            signal: 交易訊號 (1=買入, -1=賣出, 0=持有)
            weight: 權重
            price: 價格
            commission: 手續費率
            slippage: 滑點率
        """
        current_position = self.positions.get(symbol, 0)
        
        # 計算目標倉位
        target_value = self.portfolio_value * weight if signal > 0 else 0
        target_shares = target_value / price if price > 0 else 0
        
        # 計算交易數量
        trade_shares = target_shares - current_position
        
        if abs(trade_shares) < 1:  # 忽略小額交易
            return
        
        # 應用滑點
        trade_price = price * (1 + slippage * np.sign(trade_shares))
        
        # 計算交易成本
        trade_value = abs(trade_shares * trade_price)
        trade_commission = trade_value * commission
        
        # 檢查資金是否足夠
        if trade_shares > 0:  # 買入
            total_cost = trade_value + trade_commission
            if total_cost > self.cash:
                # 調整交易數量
                available_cash = self.cash - trade_commission
                trade_shares = available_cash / trade_price
                trade_value = trade_shares * trade_price
        
        # 執行交易
        if abs(trade_shares) >= 1:
            # 更新現金
            self.cash -= trade_shares * trade_price + trade_commission
            
            # 更新倉位
            self.positions[symbol] = current_position + trade_shares
            
            # 記錄交易
            trade_record = {
                'date': date,
                'symbol': symbol,
                'shares': trade_shares,
                'price': trade_price,
                'value': trade_shares * trade_price,
                'commission': trade_commission,
                'signal': signal,
                'weight': weight
            }
            self.trades.append(trade_record)

    def _update_portfolio_value(self, date: pd.Timestamp, prices: pd.DataFrame) -> None:
        """更新投資組合價值
        
        Args:
            date: 日期
            prices: 價格數據
        """
        # 計算持倉價值
        position_value = 0
        current_positions = {}
        
        for symbol, shares in self.positions.items():
            if shares != 0:
                # 獲取當前價格
                price_row = prices[prices['symbol'] == symbol] if not prices.empty else pd.DataFrame()
                if not price_row.empty:
                    current_price = price_row.iloc[0]['close']
                    value = shares * current_price
                    position_value += value
                    current_positions[symbol] = {
                        'shares': shares,
                        'price': current_price,
                        'value': value
                    }
        
        # 更新總價值
        self.portfolio_value = self.cash + position_value
        
        # 記錄每日數據
        self.daily_values.append({
            'date': date,
            'cash': self.cash,
            'position_value': position_value,
            'total_value': self.portfolio_value
        })
        
        self.daily_positions.append({
            'date': date,
            'positions': current_positions.copy()
        })
        
        # 計算日收益率
        if len(self.daily_values) > 1:
            prev_value = self.daily_values[-2]['total_value']
            daily_return = (self.portfolio_value - prev_value) / prev_value
            self.daily_returns.append({
                'date': date,
                'return': daily_return
            })

    def _generate_results(self, initial_capital: float) -> Dict[str, Any]:
        """生成回測結果
        
        Args:
            initial_capital: 初始資金
            
        Returns:
            Dict[str, Any]: 回測結果
        """
        # 轉換為 DataFrame
        trades_df = pd.DataFrame(self.trades)
        daily_values_df = pd.DataFrame(self.daily_values)
        daily_returns_df = pd.DataFrame(self.daily_returns)
        daily_positions_df = pd.DataFrame(self.daily_positions)
        
        # 計算基本指標
        total_return = (self.portfolio_value - initial_capital) / initial_capital
        
        # 計算年化收益率
        if not daily_values_df.empty:
            days = (daily_values_df['date'].max() - daily_values_df['date'].min()).days
            annualized_return = (1 + total_return) ** (365 / max(days, 1)) - 1
        else:
            annualized_return = 0
        
        # 計算最大回撤
        if not daily_values_df.empty:
            cumulative_values = daily_values_df['total_value']
            peak = cumulative_values.expanding().max()
            drawdown = (cumulative_values - peak) / peak
            max_drawdown = drawdown.min()
        else:
            max_drawdown = 0
        
        # 計算夏普比率
        if not daily_returns_df.empty and len(daily_returns_df) > 1:
            returns = daily_returns_df['return']
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            'summary': {
                'initial_capital': initial_capital,
                'final_value': self.portfolio_value,
                'total_return': total_return,
                'annualized_return': annualized_return,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'total_trades': len(self.trades)
            },
            'trades': trades_df,
            'daily_values': daily_values_df,
            'daily_returns': daily_returns_df,
            'daily_positions': daily_positions_df,
            'final_positions': dict(self.positions)
        }
