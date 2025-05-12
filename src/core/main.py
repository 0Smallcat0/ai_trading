"""
主流程入口模組

此模組是整個交易系統的入口點，負責協調各個模組的運作，
實現完整的交易流程，從資料獲取到交易執行。

主要功能：
- 系統初始化
- 模組協調
- 主流程控制
"""

from . import logger as trade_logger
from .executor import place_orders
from .risk_control import filter_signals
from .event_monitor import start as start_event_monitor
from .logger import record
from .backtest import run_backtest
from .portfolio import optimize
from .strategy import generate_signals
from .features import compute_features
from .data_ingest import load_data, update_data
import time
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("main.log"), logging.StreamHandler()],
)
logger = logging.getLogger("main")

# 導入各個模組


def parse_args():
    """
    解析命令行參數

    Returns:
        argparse.Namespace: 解析後的參數
    """
    parser = argparse.ArgumentParser(description="自動交易系統")

    # 模式參數
    parser.add_argument(
        "--mode",
        type=str,
        default="backtest",
        choices=["backtest", "paper", "live"],
        help="交易模式：backtest（回測）、paper（模擬交易）、live（實盤交易）",
    )

    # 資料參數
    parser.add_argument(
        "--start-date", type=str, default=None, help="開始日期，格式：YYYY-MM-DD"
    )
    parser.add_argument(
        "--end-date", type=str, default=None, help="結束日期，格式：YYYY-MM-DD"
    )
    parser.add_argument("--update-data", action="store_true", help="是否更新資料")

    # 策略參數
    parser.add_argument(
        "--strategy",
        type=str,
        default="moving_average_cross",
        choices=[
            "moving_average_cross",
            "rsi",
            "machine_learning",
            "trade_point_decision",
            "continuous_trading_signal",
            "triple_barrier",
            "fixed_time_horizon",
        ],
        help="交易策略",
    )
    parser.add_argument("--short-window", type=int, default=5, help="短期窗口大小")
    parser.add_argument("--long-window", type=int, default=20, help="長期窗口大小")
    parser.add_argument("--rsi-window", type=int, default=14, help="RSI 窗口大小")
    parser.add_argument("--rsi-overbought", type=int, default=70, help="RSI 超買閾值")
    parser.add_argument("--rsi-oversold", type=int, default=30, help="RSI 超賣閾值")

    # 投資組合參數
    parser.add_argument(
        "--portfolio",
        type=str,
        default="equal_weight",
        choices=["equal_weight", "mean_variance", "risk_parity"],
        help="投資組合策略",
    )
    parser.add_argument("--risk-aversion", type=float, default=1.0, help="風險厭惡係數")

    # 風險控制參數
    parser.add_argument(
        "--max-position-size", type=float, default=0.1, help="最大部位大小"
    )
    parser.add_argument(
        "--max-portfolio-risk", type=float, default=0.02, help="最大投資組合風險"
    )
    parser.add_argument("--stop-loss", type=float, default=0.05, help="停損百分比")
    parser.add_argument("--stop-profit", type=float, default=0.1, help="停利百分比")

    # 回測參數
    parser.add_argument(
        "--initial-capital", type=float, default=1000000, help="初始資金"
    )
    parser.add_argument(
        "--transaction-cost", type=float, default=0.001425, help="交易成本"
    )
    parser.add_argument("--slippage", type=float, default=0.001, help="滑價")
    parser.add_argument("--tax", type=float, default=0.003, help="交易稅")

    # 執行參數
    parser.add_argument("--interval", type=int, default=60, help="執行間隔（秒）")

    return parser.parse_args()


def init_system(args):
    """
    初始化系統

    Args:
        args (argparse.Namespace): 命令行參數

    Returns:
        dict: 系統配置
    """
    # 解析日期
    start_date = (
        datetime.strptime(args.start_date, "%Y-%m-%d").date()
        if args.start_date
        else None
    )
    end_date = (
        datetime.strptime(args.end_date, "%Y-%m-%d").date()
        if args.end_date
        else datetime.now().date()
    )

    # 系統配置
    config = {
        "mode": args.mode,
        "start_date": start_date,
        "end_date": end_date,
        "update_data": args.update_data,
        "strategy": {
            "name": args.strategy,
            "params": {
                "short_window": args.short_window,
                "long_window": args.long_window,
                "rsi_window": args.rsi_window,
                "rsi_overbought": args.rsi_overbought,
                "rsi_oversold": args.rsi_oversold,
            },
        },
        "portfolio": {
            "name": args.portfolio,
            "params": {"risk_aversion": args.risk_aversion},
        },
        "risk_control": {
            "max_position_size": args.max_position_size,
            "max_portfolio_risk": args.max_portfolio_risk,
            "stop_loss": args.stop_loss,
            "stop_profit": args.stop_profit,
        },
        "backtest": {
            "initial_capital": args.initial_capital,
            "transaction_cost": args.transaction_cost,
            "slippage": args.slippage,
            "tax": args.tax,
        },
        "execution": {"interval": args.interval},
    }

    return config


def run_backtest_mode(config):
    """
    執行回測模式

    Args:
        config (dict): 系統配置

    Returns:
        dict: 回測結果
    """
    logger.info("開始回測模式")

    # 載入資料
    logger.info("載入資料")
    load_data(config["start_date"], config["end_date"])

    # 更新資料
    if config["update_data"]:
        logger.info("更新資料")
        update_data(config["start_date"], config["end_date"])

    # 計算特徵
    logger.info("計算特徵")
    features = compute_features(config["start_date"], config["end_date"])

    # 生成訊號
    logger.info("生成訊號")
    signals = generate_signals(
        features, config["strategy"]["name"], **config["strategy"]["params"]
    )

    # 最佳化投資組合
    logger.info("最佳化投資組合")
    weights = optimize(
        signals, config["portfolio"]["name"], **config["portfolio"]["params"]
    )

    # 執行回測
    logger.info("執行回測")
    results = run_backtest(
        signals,
        weights,
        config["start_date"],
        config["end_date"],
        config["backtest"]["initial_capital"],
        config["backtest"]["transaction_cost"],
        config["backtest"]["slippage"],
        config["backtest"]["tax"],
    )

    # 記錄結果
    logger.info("記錄結果")
    report = record(results)

    logger.info("回測完成")

    return results, report


def run_paper_mode(config):
    """
    執行模擬交易模式

    Args:
        config (dict): 系統配置
    """
    logger.info("開始模擬交易模式")

    # 載入資料
    logger.info("載入資料")
    load_data()

    # 更新資料
    logger.info("更新資料")
    update_data()

    # 啟動事件監控
    logger.info("啟動事件監控")
    event_monitor = start_event_monitor()

    # 主循環
    while True:
        try:
            # 計算特徵
            logger.info("計算特徵")
            features = compute_features()

            # 生成訊號
            logger.info("生成訊號")
            signals = generate_signals(
                features, config["strategy"]["name"], **config["strategy"]["params"]
            )

            # 最佳化投資組合
            logger.info("最佳化投資組合")
            weights = optimize(
                signals, config["portfolio"]["name"], **config["portfolio"]["params"]
            )

            # 風險控制
            logger.info("風險控制")
            portfolio_value = config["backtest"][
                "initial_capital"
            ]  # 這裡簡化了，實際上應該從帳戶中獲取
            filtered_signals = filter_signals(
                signals,
                portfolio_value,
                max_position_size=config["risk_control"]["max_position_size"],
                max_portfolio_risk=config["risk_control"]["max_portfolio_risk"],
                stop_loss_pct=config["risk_control"]["stop_loss"],
                stop_profit_pct=config["risk_control"]["stop_profit"],
            )

            # 生成訂單
            logger.info("生成訂單")
            orders = []
            for (stock_id, date), row in filtered_signals.iterrows():
                if row.get("buy_signal", 0) == 1:
                    # 買入訂單
                    orders.append(
                        {
                            "stock_id": stock_id,
                            "action": "buy",
                            "quantity": 1000,  # 這裡簡化了，實際上應該根據權重計算
                            "order_type": "market",
                        }
                    )
                elif row.get("sell_signal", 0) == 1:
                    # 賣出訂單
                    orders.append(
                        {
                            "stock_id": stock_id,
                            "action": "sell",
                            "quantity": 1000,  # 這裡簡化了，實際上應該根據持倉計算
                            "order_type": "market",
                        }
                    )

            # 執行訂單
            if orders:
                logger.info(f"執行 {len(orders)} 個訂單")
                order_ids = place_orders(orders)
                logger.info(f"訂單 ID: {order_ids}")

            # 等待下一次執行
            logger.info(f"等待 {config['execution']['interval']} 秒")
            time.sleep(config["execution"]["interval"])

        except KeyboardInterrupt:
            logger.info("使用者中斷執行")
            break
        except Exception as e:
            logger.error(f"執行過程中發生錯誤: {e}")
            time.sleep(10)

    # 停止事件監控
    event_monitor.stop()

    logger.info("模擬交易結束")


def run_live_mode(config):
    """
    執行實盤交易模式

    Args:
        config (dict): 系統配置
    """
    logger.info("開始實盤交易模式")

    # 載入資料
    logger.info("載入資料")
    load_data()

    # 更新資料
    logger.info("更新資料")
    update_data()

    # 啟動事件監控
    logger.info("啟動事件監控")
    event_monitor = start_event_monitor()

    # 主循環
    while True:
        try:
            # 計算特徵
            logger.info("計算特徵")
            features = compute_features()

            # 生成訊號
            logger.info("生成訊號")
            signals = generate_signals(
                features, config["strategy"]["name"], **config["strategy"]["params"]
            )

            # 最佳化投資組合
            logger.info("最佳化投資組合")
            weights = optimize(
                signals, config["portfolio"]["name"], **config["portfolio"]["params"]
            )

            # 風險控制
            logger.info("風險控制")
            portfolio_value = config["backtest"][
                "initial_capital"
            ]  # 這裡簡化了，實際上應該從帳戶中獲取
            filtered_signals = filter_signals(
                signals,
                portfolio_value,
                max_position_size=config["risk_control"]["max_position_size"],
                max_portfolio_risk=config["risk_control"]["max_portfolio_risk"],
                stop_loss_pct=config["risk_control"]["stop_loss"],
                stop_profit_pct=config["risk_control"]["stop_profit"],
            )

            # 生成訂單
            logger.info("生成訂單")
            orders = []
            for (stock_id, date), row in filtered_signals.iterrows():
                if row.get("buy_signal", 0) == 1:
                    # 買入訂單
                    orders.append(
                        {
                            "stock_id": stock_id,
                            "action": "buy",
                            "quantity": 1000,  # 這裡簡化了，實際上應該根據權重計算
                            "order_type": "market",
                        }
                    )
                elif row.get("sell_signal", 0) == 1:
                    # 賣出訂單
                    orders.append(
                        {
                            "stock_id": stock_id,
                            "action": "sell",
                            "quantity": 1000,  # 這裡簡化了，實際上應該根據持倉計算
                            "order_type": "market",
                        }
                    )

            # 執行訂單
            if orders:
                logger.info(f"執行 {len(orders)} 個訂單")
                order_ids = place_orders(orders)
                logger.info(f"訂單 ID: {order_ids}")

            # 等待下一次執行
            logger.info(f"等待 {config['execution']['interval']} 秒")
            time.sleep(config["execution"]["interval"])

        except KeyboardInterrupt:
            logger.info("使用者中斷執行")
            break
        except Exception as e:
            logger.error(f"執行過程中發生錯誤: {e}")
            time.sleep(10)

    # 停止事件監控
    event_monitor.stop()

    logger.info("實盤交易結束")


def main():
    """主函數"""
    # 解析命令行參數
    args = parse_args()

    # 初始化系統
    config = init_system(args)

    # 根據模式執行不同的流程
    if config["mode"] == "backtest":
        results, report = run_backtest_mode(config)

        # 輸出回測結果
        print("\n===== 回測結果 =====")
        print(f"總收益率: {report['returns']['total_return']:.2%}")
        print(f"年化收益率: {report['returns']['annual_return']:.2%}")
        print(f"夏普比率: {report['risk']['sharpe_ratio']:.2f}")
        print(f"最大回撤: {report['risk']['max_drawdown']:.2%}")
        print(f"勝率: {report['trade']['win_rate']:.2%}")
        print(f"盈虧比: {report['trade']['profit_loss_ratio']:.2f}")
        print("====================\n")

    elif config["mode"] == "paper":
        run_paper_mode(config)
    elif config["mode"] == "live":
        run_live_mode(config)
    else:
        logger.error(f"不支援的模式: {config['mode']}")


if __name__ == "__main__":
    try:
        logger.info("開始執行自動交易系統")

        # 載入資料
        logger.info("載入資料中...")
        data = load_data()
        logger.info("資料載入完成")

        # 計算特徵
        logger.info("計算特徵中...")
        feats = compute_features(data)
        logger.info("特徵計算完成")

        # 生成交易訊號
        logger.info("生成交易訊號中...")
        signals = generate_signals(feats)
        logger.info("交易訊號生成完成")

        # 計算投資組合權重
        logger.info("計算投資組合權重中...")
        weights = optimize(signals)
        logger.info("投資組合權重計算完成")

        # 執行回測
        logger.info("執行回測中...")
        results = run_backtest(signals, weights, commission_rate=0.001, slippage=0.0005)
        logger.info("回測完成")

        # 風險控制
        logger.info("執行風險控制中...")
        orders = filter_signals(signals, results["equity_curve"][-1])
        logger.info(f"風險控制完成，生成 {len(orders)} 個訂單")

        # 執行訂單
        logger.info("執行訂單中...")
        place_orders(orders)
        logger.info("訂單執行完成")

        # 啟動事件監控
        logger.info("啟動事件監控...")
        start_event_monitor()
        logger.info("事件監控已啟動")

        # 分析績效
        logger.info("分析交易績效中...")
        trade_logger.analyze_performance(results, orders)
        logger.info("績效分析完成")

        logger.info("自動交易系統執行完成")
    except Exception as e:
        logger.error(f"執行過程中發生錯誤: {e}", exc_info=True)
