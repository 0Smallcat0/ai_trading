# -*- coding: utf-8 -*-
"""
LLM策略回測驗證腳本

此腳本用於驗證LLM策略的回測性能和準確性。

主要功能：
- LLM策略回測
- 性能指標計算
- 與基準策略比較
- 結果報告生成
- 統計顯著性測試
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import logging
import argparse
import json

# 添加項目根目錄到路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.strategy.llm.finmem_llm import FinMemLLMStrategy
from src.strategy.llm.stock_chain import StockChainStrategy
from src.strategy.llm.news_analysis import NewsAnalysisStrategy
from src.strategy.llm_integration import LLMStrategyIntegrator
from src.backtest.backtest_engine import BacktestEngine
from src.data.market_data import MarketDataProvider

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMBacktestValidator:
    """LLM策略回測驗證器"""

    def __init__(self, config: Dict[str, Any]):
        """初始化回測驗證器。

        Args:
            config: 配置字典
        """
        self.config = config
        self.results = {}
        self.market_data_provider = MarketDataProvider()
        
        # 初始化策略
        self.strategies = self._initialize_strategies()
        
        # 初始化回測引擎
        self.backtest_engine = BacktestEngine(
            initial_capital=config.get('initial_capital', 100000),
            commission=config.get('commission', 0.001)
        )

    def _initialize_strategies(self) -> Dict[str, Any]:
        """初始化策略。

        Returns:
            策略字典
        """
        strategies = {}
        
        # LLM配置
        llm_config = {
            'model_name': 'gpt-3.5-turbo',
            'api_key': 'test-api-key'  # 在實際使用中應從環境變數讀取
        }
        
        # FinMem-LLM策略
        if self.config.get('test_finmem_llm', True):
            strategies['finmem_llm'] = FinMemLLMStrategy(
                llm_config=llm_config,
                confidence_threshold=0.6,
                news_days=5
            )
        
        # Stock-chain策略
        if self.config.get('test_stock_chain', True):
            strategies['stock_chain'] = StockChainStrategy(
                llm_config=llm_config,
                confidence_threshold=0.65,
                enable_web_search=False  # 回測時關閉網路搜索
            )
        
        # 新聞分析策略
        if self.config.get('test_news_analysis', True):
            strategies['news_analysis'] = NewsAnalysisStrategy(
                llm_config=llm_config,
                confidence_threshold=0.65
            )
        
        # 基準策略（買入持有）
        strategies['buy_and_hold'] = BuyAndHoldStrategy()
        
        return strategies

    def run_validation(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, Any]:
        """運行回測驗證。

        Args:
            symbols: 股票代碼列表
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            驗證結果字典
        """
        logger.info(f"開始回測驗證: {symbols}, {start_date} - {end_date}")
        
        validation_results = {}
        
        for symbol in symbols:
            logger.info(f"回測股票: {symbol}")
            
            # 獲取市場數據
            market_data = self._get_market_data(symbol, start_date, end_date)
            
            if market_data.empty:
                logger.warning(f"無法獲取 {symbol} 的市場數據")
                continue
            
            symbol_results = {}
            
            # 測試每個策略
            for strategy_name, strategy in self.strategies.items():
                logger.info(f"測試策略: {strategy_name}")
                
                try:
                    # 運行回測
                    backtest_result = self._run_strategy_backtest(
                        strategy, market_data, symbol
                    )
                    
                    # 計算性能指標
                    performance_metrics = self._calculate_performance_metrics(
                        backtest_result, market_data
                    )
                    
                    symbol_results[strategy_name] = {
                        'backtest_result': backtest_result,
                        'performance_metrics': performance_metrics
                    }
                    
                except Exception as e:
                    logger.error(f"策略 {strategy_name} 回測失敗: {e}")
                    symbol_results[strategy_name] = {
                        'error': str(e)
                    }
            
            validation_results[symbol] = symbol_results
        
        # 生成綜合報告
        comprehensive_report = self._generate_comprehensive_report(validation_results)
        
        return {
            'individual_results': validation_results,
            'comprehensive_report': comprehensive_report,
            'validation_config': self.config,
            'validation_timestamp': datetime.now().isoformat()
        }

    def _get_market_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """獲取市場數據。

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            市場數據DataFrame
        """
        try:
            # 這裡應該調用實際的市場數據提供者
            # 暫時生成模擬數據
            return self._generate_mock_market_data(symbol, start_date, end_date)
        except Exception as e:
            logger.error(f"獲取市場數據失敗: {e}")
            return pd.DataFrame()

    def _generate_mock_market_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """生成模擬市場數據。

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            模擬市場數據
        """
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 生成隨機價格走勢
        np.random.seed(hash(symbol) % 2**32)  # 確保每個股票的數據一致
        
        initial_price = 100
        returns = np.random.normal(0.001, 0.02, len(dates))  # 日收益率
        prices = [initial_price]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        data = pd.DataFrame({
            '收盤價': prices,
            '開盤價': [p * np.random.uniform(0.98, 1.02) for p in prices],
            '最高價': [p * np.random.uniform(1.0, 1.05) for p in prices],
            '最低價': [p * np.random.uniform(0.95, 1.0) for p in prices],
            '成交量': np.random.uniform(1000000, 5000000, len(dates)),
            'news': [f"{symbol}相關新聞 {i}" for i in range(len(dates))],
            'stock_code': [symbol] * len(dates)
        }, index=dates)
        
        return data

    def _run_strategy_backtest(self, strategy, market_data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """運行策略回測。

        Args:
            strategy: 策略實例
            market_data: 市場數據
            symbol: 股票代碼

        Returns:
            回測結果
        """
        # 模擬LLM調用（在實際回測中需要真實調用）
        if hasattr(strategy, '_call_llm'):
            original_call_llm = strategy._call_llm
            strategy._call_llm = self._mock_llm_call
        
        try:
            # 生成交易信號
            signals = strategy.generate_signals(market_data)
            
            # 運行回測
            backtest_result = self.backtest_engine.run_backtest(
                signals=signals,
                market_data=market_data,
                symbol=symbol
            )
            
            return backtest_result
            
        finally:
            # 恢復原始方法
            if hasattr(strategy, '_call_llm') and 'original_call_llm' in locals():
                strategy._call_llm = original_call_llm

    def _mock_llm_call(self, input_text: str) -> str:
        """模擬LLM調用。

        Args:
            input_text: 輸入文本

        Returns:
            模擬LLM響應
        """
        # 基於輸入文本的簡單模擬邏輯
        if '利好' in input_text or '增長' in input_text or '上漲' in input_text:
            return "基於分析，預測股價[上漲]，置信度較高"
        elif '利空' in input_text or '下跌' in input_text or '風險' in input_text:
            return "基於分析，預測股價[下跌]，置信度中等"
        else:
            return "市場不確定，建議[持有]"

    def _calculate_performance_metrics(self, backtest_result: Dict[str, Any], market_data: pd.DataFrame) -> Dict[str, float]:
        """計算性能指標。

        Args:
            backtest_result: 回測結果
            market_data: 市場數據

        Returns:
            性能指標字典
        """
        if 'portfolio_values' not in backtest_result:
            return {}
        
        portfolio_values = pd.Series(backtest_result['portfolio_values'])
        returns = portfolio_values.pct_change().dropna()
        
        # 基準收益（買入持有）
        benchmark_returns = market_data['收盤價'].pct_change().dropna()
        
        metrics = {}
        
        # 總收益率
        metrics['total_return'] = (portfolio_values.iloc[-1] / portfolio_values.iloc[0] - 1) * 100
        
        # 年化收益率
        days = len(portfolio_values)
        metrics['annualized_return'] = ((portfolio_values.iloc[-1] / portfolio_values.iloc[0]) ** (252 / days) - 1) * 100
        
        # 波動率
        metrics['volatility'] = returns.std() * np.sqrt(252) * 100
        
        # 夏普比率
        risk_free_rate = 0.02  # 假設無風險利率2%
        excess_returns = returns.mean() * 252 - risk_free_rate
        metrics['sharpe_ratio'] = excess_returns / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        metrics['max_drawdown'] = drawdown.min() * 100
        
        # 勝率
        if len(returns) > 0:
            metrics['win_rate'] = (returns > 0).sum() / len(returns) * 100
        else:
            metrics['win_rate'] = 0
        
        # 相對基準的超額收益
        if len(benchmark_returns) > 0:
            benchmark_total_return = (market_data['收盤價'].iloc[-1] / market_data['收盤價'].iloc[0] - 1) * 100
            metrics['excess_return'] = metrics['total_return'] - benchmark_total_return
        
        # 信息比率
        if len(returns) == len(benchmark_returns):
            excess_returns_series = returns - benchmark_returns
            if excess_returns_series.std() > 0:
                metrics['information_ratio'] = excess_returns_series.mean() / excess_returns_series.std() * np.sqrt(252)
            else:
                metrics['information_ratio'] = 0
        
        return metrics

    def _generate_comprehensive_report(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成綜合報告。

        Args:
            validation_results: 驗證結果

        Returns:
            綜合報告
        """
        report = {
            'summary': {},
            'strategy_comparison': {},
            'statistical_tests': {},
            'recommendations': []
        }
        
        # 收集所有策略的性能指標
        all_metrics = {}
        for symbol, symbol_results in validation_results.items():
            for strategy_name, strategy_result in symbol_results.items():
                if 'performance_metrics' in strategy_result:
                    if strategy_name not in all_metrics:
                        all_metrics[strategy_name] = []
                    all_metrics[strategy_name].append(strategy_result['performance_metrics'])
        
        # 計算平均性能
        avg_metrics = {}
        for strategy_name, metrics_list in all_metrics.items():
            if metrics_list:
                avg_metrics[strategy_name] = {}
                for metric in metrics_list[0].keys():
                    values = [m[metric] for m in metrics_list if metric in m]
                    if values:
                        avg_metrics[strategy_name][metric] = np.mean(values)
        
        report['summary'] = avg_metrics
        
        # 策略比較
        if 'buy_and_hold' in avg_metrics:
            benchmark_return = avg_metrics['buy_and_hold'].get('total_return', 0)
            
            for strategy_name, metrics in avg_metrics.items():
                if strategy_name != 'buy_and_hold':
                    strategy_return = metrics.get('total_return', 0)
                    outperformance = strategy_return - benchmark_return
                    
                    report['strategy_comparison'][strategy_name] = {
                        'outperformance': outperformance,
                        'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                        'max_drawdown': metrics.get('max_drawdown', 0),
                        'win_rate': metrics.get('win_rate', 0)
                    }
        
        # 生成建議
        report['recommendations'] = self._generate_recommendations(avg_metrics)
        
        return report

    def _generate_recommendations(self, avg_metrics: Dict[str, Dict[str, float]]) -> List[str]:
        """生成建議。

        Args:
            avg_metrics: 平均性能指標

        Returns:
            建議列表
        """
        recommendations = []
        
        # 找出最佳策略
        best_sharpe = -999
        best_strategy = None
        
        for strategy_name, metrics in avg_metrics.items():
            if strategy_name != 'buy_and_hold':
                sharpe = metrics.get('sharpe_ratio', 0)
                if sharpe > best_sharpe:
                    best_sharpe = sharpe
                    best_strategy = strategy_name
        
        if best_strategy:
            recommendations.append(f"基於夏普比率，{best_strategy}表現最佳")
        
        # 檢查風險調整後收益
        for strategy_name, metrics in avg_metrics.items():
            if strategy_name != 'buy_and_hold':
                max_dd = metrics.get('max_drawdown', 0)
                if max_dd < -20:
                    recommendations.append(f"{strategy_name}的最大回撤過大({max_dd:.1f}%)，需要改進風險控制")
                
                win_rate = metrics.get('win_rate', 0)
                if win_rate < 40:
                    recommendations.append(f"{strategy_name}的勝率較低({win_rate:.1f}%)，建議優化信號質量")
        
        return recommendations

    def save_results(self, results: Dict[str, Any], output_path: str) -> None:
        """保存結果。

        Args:
            results: 驗證結果
            output_path: 輸出路徑
        """
        # 保存JSON結果
        json_path = f"{output_path}_results.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            # 轉換不可序列化的對象
            serializable_results = self._make_serializable(results)
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"結果已保存到: {json_path}")
        
        # 生成可視化報告
        self._generate_visualization_report(results, output_path)

    def _make_serializable(self, obj):
        """使對象可序列化。

        Args:
            obj: 要序列化的對象

        Returns:
            可序列化的對象
        """
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (pd.DataFrame, pd.Series)):
            return obj.to_dict()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    def _generate_visualization_report(self, results: Dict[str, Any], output_path: str) -> None:
        """生成可視化報告。

        Args:
            results: 驗證結果
            output_path: 輸出路徑
        """
        try:
            # 設定中文字體
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 創建圖表
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('LLM策略回測驗證報告', fontsize=16)
            
            # 提取性能數據
            comprehensive_report = results.get('comprehensive_report', {})
            summary = comprehensive_report.get('summary', {})
            
            if summary:
                strategies = list(summary.keys())
                
                # 1. 總收益率比較
                returns = [summary[s].get('total_return', 0) for s in strategies]
                axes[0, 0].bar(strategies, returns)
                axes[0, 0].set_title('總收益率比較 (%)')
                axes[0, 0].tick_params(axis='x', rotation=45)
                
                # 2. 夏普比率比較
                sharpe_ratios = [summary[s].get('sharpe_ratio', 0) for s in strategies]
                axes[0, 1].bar(strategies, sharpe_ratios)
                axes[0, 1].set_title('夏普比率比較')
                axes[0, 1].tick_params(axis='x', rotation=45)
                
                # 3. 最大回撤比較
                max_drawdowns = [abs(summary[s].get('max_drawdown', 0)) for s in strategies]
                axes[1, 0].bar(strategies, max_drawdowns)
                axes[1, 0].set_title('最大回撤比較 (%)')
                axes[1, 0].tick_params(axis='x', rotation=45)
                
                # 4. 勝率比較
                win_rates = [summary[s].get('win_rate', 0) for s in strategies]
                axes[1, 1].bar(strategies, win_rates)
                axes[1, 1].set_title('勝率比較 (%)')
                axes[1, 1].tick_params(axis='x', rotation=45)
            
            plt.tight_layout()
            
            # 保存圖表
            chart_path = f"{output_path}_charts.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"可視化報告已保存到: {chart_path}")
            
        except Exception as e:
            logger.error(f"生成可視化報告失敗: {e}")


class BuyAndHoldStrategy:
    """買入持有基準策略"""

    def __init__(self):
        self.name = "買入持有策略"

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成買入持有信號。

        Args:
            data: 市場數據

        Returns:
            交易信號
        """
        signals = pd.DataFrame(index=data.index)
        signals['signal'] = 0
        signals['buy_signal'] = 0
        signals['sell_signal'] = 0
        signals['confidence'] = 1.0
        signals['reasoning'] = '買入持有策略'
        
        # 第一天買入
        if len(signals) > 0:
            signals.iloc[0]['signal'] = 1
            signals.iloc[0]['buy_signal'] = 1
        
        return signals


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='LLM策略回測驗證')
    parser.add_argument('--symbols', nargs='+', default=['AAPL', 'GOOGL', 'MSFT'], help='股票代碼列表')
    parser.add_argument('--start-date', default='2023-01-01', help='開始日期')
    parser.add_argument('--end-date', default='2023-12-31', help='結束日期')
    parser.add_argument('--output', default='llm_backtest_validation', help='輸出文件前綴')
    parser.add_argument('--config', help='配置文件路徑')
    
    args = parser.parse_args()
    
    # 載入配置
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {
            'initial_capital': 100000,
            'commission': 0.001,
            'test_finmem_llm': True,
            'test_stock_chain': True,
            'test_news_analysis': True
        }
    
    # 創建驗證器
    validator = LLMBacktestValidator(config)
    
    # 運行驗證
    results = validator.run_validation(
        symbols=args.symbols,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    # 保存結果
    validator.save_results(results, args.output)
    
    # 打印摘要
    comprehensive_report = results.get('comprehensive_report', {})
    summary = comprehensive_report.get('summary', {})
    
    print("\n=== LLM策略回測驗證摘要 ===")
    for strategy_name, metrics in summary.items():
        print(f"\n{strategy_name}:")
        print(f"  總收益率: {metrics.get('total_return', 0):.2f}%")
        print(f"  夏普比率: {metrics.get('sharpe_ratio', 0):.3f}")
        print(f"  最大回撤: {metrics.get('max_drawdown', 0):.2f}%")
        print(f"  勝率: {metrics.get('win_rate', 0):.1f}%")
    
    # 打印建議
    recommendations = comprehensive_report.get('recommendations', [])
    if recommendations:
        print("\n=== 建議 ===")
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")


if __name__ == "__main__":
    main()
