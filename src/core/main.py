"""
主流程入口模組

此模組是整個交易系統的入口點，負責協調各個模組的運作，
實現完整的交易流程，從資料獲取到交易執行。

主要功能：
- 系統初始化和配置管理
- 模式選擇和執行協調
- 主流程控制和錯誤處理

Example:
    >>> from src.core.main import main
    >>> main()  # 使用命令行參數執行
    
    或者直接調用：
    >>> from src.core.main import run_trading_system
    >>> run_trading_system(mode="backtest", start_date="2023-01-01")
"""

import logging
from typing import Dict, Any, Optional

from dotenv import load_dotenv

from . import logger as trade_logger
from .backtest import run_backtest
# 更新導入：使用推薦的配置管理系統
try:
    from ..utils.config_manager import create_default_config_manager
    from .config_validator import validate_config
    # 為了向後相容，創建包裝函數
    def parse_args():
        """向後相容的參數解析函數"""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--mode', default='backtest', help='運行模式')
        return parser.parse_args()

    def init_system(args):
        """向後相容的系統初始化函數"""
        config_manager = create_default_config_manager()
        return {'mode': args.mode, 'config_manager': config_manager}

except ImportError:
    # 向後相容：如果新模組不存在，使用舊模組
    from .config_manager import parse_args, init_system, validate_config
from .data_ingest import load_data
from .event_monitor import start as start_event_monitor
from .executor import place_orders
from .features import compute_features
from .mode_handlers import run_backtest_mode, run_paper_mode, run_live_mode
from .portfolio import optimize
from .risk_control import filter_signals
from ..strategy.utils import generate_signals

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("main.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def run_trading_system(
    mode: str = "backtest",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """運行交易系統的主要函數.

    Args:
        mode: 交易模式，可選 'backtest', 'paper', 'live'
        start_date: 開始日期，格式 YYYY-MM-DD
        end_date: 結束日期，格式 YYYY-MM-DD
        **kwargs: 其他配置參數

    Returns:
        Optional[Dict[str, Any]]: 回測模式返回結果，其他模式返回 None

    Raises:
        ValueError: 當配置參數不正確時
        RuntimeError: 當系統執行失敗時

    Example:
        >>> result = run_trading_system(
        ...     mode="backtest",
        ...     start_date="2023-01-01",
        ...     end_date="2023-12-31"
        ... )
        >>> print(f"總收益率: {result['report']['returns']['total_return']:.2%}")
    """
    logger.info("🚀 啟動 AI 交易系統 - 模式: %s", mode.upper())

    try:
        # 構建配置
        config = {
            "mode": mode,
            "start_date": start_date,
            "end_date": end_date,
            **kwargs
        }

        # 驗證配置
        if not _validate_basic_config(config):
            raise ValueError("配置驗證失敗")

        # 根據模式執行
        if mode == "backtest":
            results, report = run_backtest_mode(config)
            _print_backtest_results(report)
            return {"results": results, "report": report}
        
        elif mode == "paper":
            run_paper_mode(config)
            return None
        
        elif mode == "live":
            logger.warning("⚠️  即將啟動實盤交易模式！")
            run_live_mode(config)
            return None
        
        else:
            raise ValueError(f"不支援的交易模式: {mode}")

    except KeyboardInterrupt:
        logger.info("收到中斷信號，系統正在安全關閉...")
        return None
    except Exception as e:
        logger.error("交易系統執行失敗: %s", e, exc_info=True)
        raise RuntimeError(f"系統執行失敗: {e}") from e
    finally:
        logger.info("交易系統已關閉")


def _validate_basic_config(config: Dict[str, Any]) -> bool:
    """驗證基本配置.

    Args:
        config: 配置字典

    Returns:
        bool: 配置是否有效
    """
    required_keys = ["mode"]
    
    for key in required_keys:
        if key not in config:
            logger.error("缺少必要配置項: %s", key)
            return False
    
    if config["mode"] not in ["backtest", "paper", "live"]:
        logger.error("不支援的交易模式: %s", config["mode"])
        return False
    
    return True


def _print_backtest_results(report: Dict[str, Any]) -> None:
    """打印回測結果.

    Args:
        report: 回測報告字典
    """
    try:
        print("\n" + "="*50)
        print("📊 回測結果摘要")
        print("="*50)
        
        returns = report.get("returns", {})
        risk = report.get("risk", {})
        trade = report.get("trade", {})
        
        print(f"💰 總收益率: {returns.get('total_return', 0):.2%}")
        print(f"📈 年化收益率: {returns.get('annual_return', 0):.2%}")
        print(f"📊 夏普比率: {risk.get('sharpe_ratio', 0):.2f}")
        print(f"📉 最大回撤: {risk.get('max_drawdown', 0):.2%}")
        print(f"🎯 勝率: {trade.get('win_rate', 0):.2%}")
        print(f"💡 盈虧比: {trade.get('profit_loss_ratio', 0):.2f}")
        print("="*50 + "\n")
        
    except Exception as e:
        logger.warning("打印回測結果時發生錯誤: %s", e)


def main() -> int:
    """主函數，處理命令行參數並執行交易系統.

    Returns:
        int: 退出碼，0 表示成功，1 表示失敗

    Example:
        >>> exit_code = main()
        >>> print(f"程序退出碼: {exit_code}")
    """
    try:
        # 解析命令行參數
        args = parse_args()
        logger.info("命令行參數解析完成")

        # 初始化系統配置
        config = init_system(args)
        logger.info("系統配置初始化完成")

        # 驗證配置
        validate_config(config)
        logger.info("配置驗證通過")

        # 執行交易系統
        result = None
        if config["mode"] == "backtest":
            results, report = run_backtest_mode(config)
            _print_backtest_results(report)
            result = {"results": results, "report": report}
        
        elif config["mode"] == "paper":
            run_paper_mode(config)
        
        elif config["mode"] == "live":
            logger.warning("⚠️  即將啟動實盤交易模式！")
            run_live_mode(config)
        
        else:
            logger.error("不支援的交易模式: %s", config["mode"])
            return 1

        logger.info("✅ 交易系統執行完成")
        return 0

    except KeyboardInterrupt:
        logger.info("收到中斷信號，程序正在退出...")
        return 0
    except Exception as e:
        logger.error("程序執行失敗: %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
