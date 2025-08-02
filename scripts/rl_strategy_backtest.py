#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RL 策略回測驗證腳本

此腳本對強化學習策略進行回測驗證，包括：
- 不同 RL 算法的性能比較
- 歷史數據回測驗證
- 多股票投資組合測試
- 性能指標計算和分析

使用方法：
    python scripts/rl_strategy_backtest.py

輸出：
- RL 策略回測報告
- 性能比較圖表
- 策略評估結果
"""

import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategies.adapters import RLStrategyAdapter


class RLStrategyBacktester:
    """RL 策略回測器"""
    
    def __init__(self):
        """初始化回測器"""
        self.results = {
            'timestamp': datetime.now(),
            'algorithms': [],
            'performance_metrics': {},
            'backtest_results': {},
            'comparison_data': {},
            'summary': {}
        }
    
    def create_test_data(self, symbol: str = "TEST", days: int = 252) -> pd.DataFrame:
        """創建測試數據。
        
        Args:
            symbol: 股票代碼
            days: 數據天數
            
        Returns:
            測試數據框架
        """
        dates = pd.date_range(start='2023-01-01', periods=days)
        
        # 生成模擬價格數據
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, days)
        prices = 100 * np.exp(np.cumsum(returns))
        
        return pd.DataFrame({
            'symbol': symbol,
            'date': dates,
            'close': prices,
            'open': prices * (1 + np.random.normal(0, 0.005, days)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.01, days))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.01, days))),
            'volume': np.random.randint(1000, 10000, days)
        })
    
    def run_single_strategy_backtest(self, algorithm: str, data: pd.DataFrame) -> Dict[str, Any]:
        """運行單一策略回測。
        
        Args:
            algorithm: RL 算法名稱
            data: 測試數據
            
        Returns:
            回測結果
        """
        try:
            print(f"🧪 測試 {algorithm} 策略...")
            
            # 創建策略適配器
            adapter = RLStrategyAdapter(
                algorithm=algorithm,
                environment_config={'initial_balance': 100000}
            )
            
            # 記錄開始時間
            start_time = time.time()
            
            # 生成交易訊號
            signals = adapter.generate_signals(data)
            
            # 記錄執行時間
            execution_time = time.time() - start_time
            
            # 計算性能指標
            metrics = self._calculate_performance_metrics(data, signals)
            metrics['execution_time'] = execution_time
            metrics['algorithm'] = algorithm
            
            print(f"  ✅ {algorithm} 策略測試完成 (執行時間: {execution_time:.2f}s)")
            return {
                'algorithm': algorithm,
                'signals': signals,
                'metrics': metrics,
                'execution_time': execution_time
            }
            
        except Exception as e:
            print(f"  ❌ {algorithm} 策略測試失敗: {e}")
            return {
                'algorithm': algorithm,
                'error': str(e),
                'metrics': {},
                'execution_time': 0
            }
    
    def _calculate_performance_metrics(self, data: pd.DataFrame, signals: pd.DataFrame) -> Dict[str, float]:
        """計算性能指標。
        
        Args:
            data: 價格數據
            signals: 交易訊號
            
        Returns:
            性能指標字典
        """
        try:
            # 計算策略收益
            returns = data['close'].pct_change().fillna(0)
            strategy_returns = returns * signals['signal'].shift(1).fillna(0)
            
            # 計算累積收益
            cumulative_returns = (1 + strategy_returns).cumprod()
            total_return = cumulative_returns.iloc[-1] - 1
            
            # 計算年化收益率
            trading_days = len(data)
            annual_return = (1 + total_return) ** (252 / trading_days) - 1
            
            # 計算波動率
            volatility = strategy_returns.std() * np.sqrt(252)
            
            # 計算夏普比率
            sharpe_ratio = annual_return / volatility if volatility > 0 else 0
            
            # 計算最大回撤
            rolling_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # 計算勝率
            win_rate = (strategy_returns > 0).mean()
            
            # 計算交易次數
            trade_signals = signals['buy_signal'] + signals['sell_signal']
            total_trades = trade_signals.sum()
            
            return {
                'total_return': total_return,
                'annual_return': annual_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'total_trades': int(total_trades),
                'avg_return_per_trade': total_return / max(total_trades, 1)
            }
            
        except Exception as e:
            print(f"計算性能指標失敗: {e}")
            return {
                'total_return': 0.0,
                'annual_return': 0.0,
                'volatility': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'total_trades': 0,
                'avg_return_per_trade': 0.0
            }
    
    def run_multi_algorithm_comparison(self, algorithms: List[str], data: pd.DataFrame) -> Dict[str, Any]:
        """運行多算法比較測試。
        
        Args:
            algorithms: RL 算法列表
            data: 測試數據
            
        Returns:
            比較結果
        """
        print("🔄 開始多算法比較測試...")
        
        comparison_results = {}
        performance_summary = []
        
        for algorithm in algorithms:
            result = self.run_single_strategy_backtest(algorithm, data)
            comparison_results[algorithm] = result
            
            if 'metrics' in result and result['metrics']:
                performance_summary.append(result['metrics'])
        
        # 創建性能比較表
        if performance_summary:
            comparison_df = pd.DataFrame(performance_summary)
            comparison_df = comparison_df.set_index('algorithm')
            
            print("\n📊 算法性能比較:")
            print(comparison_df.round(4))
            
            # 找出最佳算法
            best_algorithm = comparison_df['sharpe_ratio'].idxmax()
            print(f"\n🏆 最佳算法: {best_algorithm} (夏普比率: {comparison_df.loc[best_algorithm, 'sharpe_ratio']:.4f})")
        
        return {
            'results': comparison_results,
            'comparison_table': comparison_df if performance_summary else pd.DataFrame(),
            'best_algorithm': best_algorithm if performance_summary else None
        }
    
    def run_multi_stock_test(self, algorithms: List[str], symbols: List[str]) -> Dict[str, Any]:
        """運行多股票測試。
        
        Args:
            algorithms: RL 算法列表
            symbols: 股票代碼列表
            
        Returns:
            多股票測試結果
        """
        print("📈 開始多股票測試...")
        
        multi_stock_results = {}
        
        for symbol in symbols:
            print(f"\n測試股票: {symbol}")
            
            # 創建該股票的測試數據
            stock_data = self.create_test_data(symbol=symbol, days=252)
            
            # 測試所有算法
            stock_results = {}
            for algorithm in algorithms:
                result = self.run_single_strategy_backtest(algorithm, stock_data)
                stock_results[algorithm] = result
            
            multi_stock_results[symbol] = stock_results
        
        # 計算跨股票平均性能
        avg_performance = self._calculate_average_performance(multi_stock_results, algorithms)
        
        return {
            'stock_results': multi_stock_results,
            'average_performance': avg_performance
        }
    
    def _calculate_average_performance(self, multi_stock_results: Dict, algorithms: List[str]) -> pd.DataFrame:
        """計算跨股票平均性能。
        
        Args:
            multi_stock_results: 多股票結果
            algorithms: 算法列表
            
        Returns:
            平均性能數據框架
        """
        performance_data = []
        
        for algorithm in algorithms:
            algorithm_metrics = []
            
            for symbol, stock_results in multi_stock_results.items():
                if algorithm in stock_results and 'metrics' in stock_results[algorithm]:
                    metrics = stock_results[algorithm]['metrics']
                    if metrics:  # 確保 metrics 不為空
                        algorithm_metrics.append(metrics)
            
            if algorithm_metrics:
                # 計算平均值
                avg_metrics = {}
                for key in algorithm_metrics[0].keys():
                    if key != 'algorithm':
                        values = [m[key] for m in algorithm_metrics if key in m and isinstance(m[key], (int, float))]
                        avg_metrics[key] = np.mean(values) if values else 0.0
                
                avg_metrics['algorithm'] = algorithm
                performance_data.append(avg_metrics)
        
        return pd.DataFrame(performance_data).set_index('algorithm') if performance_data else pd.DataFrame()
    
    def generate_performance_report(self, results: Dict[str, Any]) -> str:
        """生成性能報告。
        
        Args:
            results: 測試結果
            
        Returns:
            報告內容
        """
        report = []
        report.append("# RL 策略回測驗證報告")
        report.append(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 單一算法結果
        if 'single_algorithm' in results:
            report.append("## 單一算法測試結果")
            for algo, result in results['single_algorithm'].items():
                if 'metrics' in result and result['metrics']:
                    metrics = result['metrics']
                    report.append(f"### {algo}")
                    report.append(f"- 總收益率: {metrics.get('total_return', 0):.2%}")
                    report.append(f"- 年化收益率: {metrics.get('annual_return', 0):.2%}")
                    report.append(f"- 夏普比率: {metrics.get('sharpe_ratio', 0):.4f}")
                    report.append(f"- 最大回撤: {metrics.get('max_drawdown', 0):.2%}")
                    report.append(f"- 勝率: {metrics.get('win_rate', 0):.2%}")
                    report.append(f"- 執行時間: {result.get('execution_time', 0):.2f}s")
                    report.append("")
        
        # 多算法比較
        if 'multi_algorithm' in results and 'best_algorithm' in results['multi_algorithm']:
            report.append("## 多算法比較結果")
            best_algo = results['multi_algorithm']['best_algorithm']
            report.append(f"**最佳算法**: {best_algo}")
            report.append("")
        
        # 多股票測試
        if 'multi_stock' in results:
            report.append("## 多股票測試結果")
            avg_perf = results['multi_stock']['average_performance']
            if not avg_perf.empty:
                report.append("### 平均性能表現")
                for algo in avg_perf.index:
                    report.append(f"**{algo}**:")
                    report.append(f"- 平均收益率: {avg_perf.loc[algo, 'total_return']:.2%}")
                    report.append(f"- 平均夏普比率: {avg_perf.loc[algo, 'sharpe_ratio']:.4f}")
                    report.append("")
        
        return "\n".join(report)
    
    def run_comprehensive_backtest(self) -> Dict[str, Any]:
        """運行綜合回測。
        
        Returns:
            綜合回測結果
        """
        print("🚀 開始 RL 策略綜合回測驗證")
        print("=" * 60)
        
        # 測試算法列表
        algorithms = ['PPO', 'DQN', 'SAC']
        
        # 創建測試數據
        test_data = self.create_test_data(days=252)
        
        results = {}
        
        # 1. 多算法比較測試
        results['multi_algorithm'] = self.run_multi_algorithm_comparison(algorithms, test_data)
        
        # 2. 多股票測試
        test_symbols = ['STOCK_A', 'STOCK_B', 'STOCK_C']
        results['multi_stock'] = self.run_multi_stock_test(algorithms, test_symbols)
        
        # 3. 性能測試
        print("\n⚡ 性能測試...")
        performance_results = self._run_performance_test(algorithms[0], test_data)
        results['performance'] = performance_results
        
        # 生成報告
        report = self.generate_performance_report(results)
        
        # 保存報告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"rl_strategy_backtest_report_{timestamp}.md"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\n📄 回測報告已保存到: {report_file}")
        except Exception as e:
            print(f"保存報告失敗: {e}")
        
        return results
    
    def _run_performance_test(self, algorithm: str, data: pd.DataFrame) -> Dict[str, Any]:
        """運行性能測試。
        
        Args:
            algorithm: 測試算法
            data: 測試數據
            
        Returns:
            性能測試結果
        """
        try:
            adapter = RLStrategyAdapter(algorithm=algorithm)
            
            # 測試多次執行的平均時間
            execution_times = []
            for i in range(5):
                start_time = time.time()
                signals = adapter.generate_signals(data)
                execution_time = time.time() - start_time
                execution_times.append(execution_time)
            
            avg_execution_time = np.mean(execution_times)
            throughput = len(data) / avg_execution_time  # 數據點/秒
            
            print(f"  平均執行時間: {avg_execution_time:.3f}s")
            print(f"  處理速度: {throughput:.1f} 數據點/秒")
            
            return {
                'algorithm': algorithm,
                'avg_execution_time': avg_execution_time,
                'throughput': throughput,
                'data_points': len(data),
                'test_runs': len(execution_times)
            }
            
        except Exception as e:
            print(f"性能測試失敗: {e}")
            return {'error': str(e)}


def main():
    """主函數"""
    backtester = RLStrategyBacktester()
    
    try:
        results = backtester.run_comprehensive_backtest()
        
        print("\n" + "=" * 60)
        print("📊 RL 策略回測驗證完成")
        print("=" * 60)
        
        # 顯示總結
        if 'multi_algorithm' in results and 'best_algorithm' in results['multi_algorithm']:
            best_algo = results['multi_algorithm']['best_algorithm']
            print(f"🏆 最佳算法: {best_algo}")
        
        if 'performance' in results and 'throughput' in results['performance']:
            throughput = results['performance']['throughput']
            print(f"⚡ 處理速度: {throughput:.1f} 數據點/秒")
        
        print("✅ 所有測試完成！")
        
    except KeyboardInterrupt:
        print("\n測試被用戶中斷")
    except Exception as e:
        print(f"\n測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
