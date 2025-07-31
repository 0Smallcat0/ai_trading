"""
命令行參數解析模組

此模組負責處理命令行參數的定義和解析，包括：
- 參數定義和配置
- 參數解析和驗證
- 幫助信息生成

主要功能：
- 定義所有支援的命令行參數
- 解析命令行輸入
- 提供參數驗證和錯誤處理

Example:
    >>> from src.core.argument_parser import create_argument_parser, parse_arguments
    >>> parser = create_argument_parser()
    >>> args = parse_arguments(parser)
    >>> print(args.mode)
"""

import argparse
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def create_argument_parser() -> argparse.ArgumentParser:
    """創建命令行參數解析器.

    Returns:
        argparse.ArgumentParser: 配置好的參數解析器

    Example:
        >>> parser = create_argument_parser()
        >>> args = parser.parse_args(['--mode', 'backtest'])
        >>> print(args.mode)
        'backtest'
    """
    parser = argparse.ArgumentParser(
        description="自動交易系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  %(prog)s --mode backtest --start-date 2023-01-01 --end-date 2023-12-31
  %(prog)s --mode paper --strategy ma_cross
  %(prog)s --mode live --broker ib
        """
    )

    # 添加各類參數
    _add_mode_arguments(parser)
    _add_data_arguments(parser)
    _add_strategy_arguments(parser)
    _add_portfolio_arguments(parser)
    _add_backtest_arguments(parser)
    _add_risk_control_arguments(parser)
    _add_execution_arguments(parser)
    _add_broker_arguments(parser)
    _add_logging_arguments(parser)

    return parser


def _add_mode_arguments(parser: argparse.ArgumentParser) -> None:
    """添加模式相關參數.

    Args:
        parser: 參數解析器
    """
    parser.add_argument(
        "--mode",
        type=str,
        default="backtest",
        choices=["backtest", "paper", "live"],
        help="交易模式：backtest（回測）、paper（模擬交易）、live（實盤交易）",
    )


def _add_data_arguments(parser: argparse.ArgumentParser) -> None:
    """添加資料相關參數.

    Args:
        parser: 參數解析器
    """
    parser.add_argument(
        "--start-date", 
        type=str, 
        default=None, 
        help="開始日期，格式：YYYY-MM-DD"
    )
    parser.add_argument(
        "--end-date", 
        type=str, 
        default=None, 
        help="結束日期，格式：YYYY-MM-DD"
    )
    parser.add_argument(
        "--update-data",
        action="store_true",
        help="是否更新資料"
    )


def _add_strategy_arguments(parser: argparse.ArgumentParser) -> None:
    """添加策略相關參數.

    Args:
        parser: 參數解析器
    """
    parser.add_argument(
        "--strategy",
        type=str,
        default="ma_cross",
        help="交易策略名稱"
    )
    parser.add_argument(
        "--strategy-params",
        type=str,
        default="{}",
        help="策略參數（JSON 格式）"
    )


def _add_portfolio_arguments(parser: argparse.ArgumentParser) -> None:
    """添加投資組合相關參數.

    Args:
        parser: 參數解析器
    """
    parser.add_argument(
        "--portfolio",
        type=str,
        default="equal_weight",
        help="投資組合策略"
    )
    parser.add_argument(
        "--portfolio-params",
        type=str,
        default="{}",
        help="投資組合參數（JSON 格式）"
    )


def _add_backtest_arguments(parser: argparse.ArgumentParser) -> None:
    """添加回測相關參數.

    Args:
        parser: 參數解析器
    """
    parser.add_argument(
        "--initial-capital",
        type=float,
        default=1000000.0,
        help="初始資金"
    )
    parser.add_argument(
        "--transaction-cost",
        type=float,
        default=0.001425,
        help="交易成本"
    )
    parser.add_argument(
        "--slippage",
        type=float,
        default=0.0005,
        help="滑點"
    )
    parser.add_argument(
        "--tax",
        type=float,
        default=0.003,
        help="稅費"
    )


def _add_risk_control_arguments(parser: argparse.ArgumentParser) -> None:
    """添加風險控制相關參數.

    Args:
        parser: 參數解析器
    """
    parser.add_argument(
        "--max-position-size",
        type=float,
        default=0.1,
        help="最大持倉比例"
    )
    parser.add_argument(
        "--max-portfolio-risk",
        type=float,
        default=0.02,
        help="最大投資組合風險"
    )
    parser.add_argument(
        "--stop-loss",
        type=float,
        default=0.05,
        help="停損比例"
    )
    parser.add_argument(
        "--stop-profit",
        type=float,
        default=0.15,
        help="停利比例"
    )


def _add_execution_arguments(parser: argparse.ArgumentParser) -> None:
    """添加執行相關參數.

    Args:
        parser: 參數解析器
    """
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="執行間隔（秒）"
    )


def _add_broker_arguments(parser: argparse.ArgumentParser) -> None:
    """添加券商相關參數.

    Args:
        parser: 參數解析器
    """
    parser.add_argument(
        "--broker",
        type=str,
        default="simulator",
        choices=["simulator", "ib", "shioaji", "futu"],
        help="券商選擇"
    )


def _add_logging_arguments(parser: argparse.ArgumentParser) -> None:
    """添加日誌相關參數.

    Args:
        parser: 參數解析器
    """
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日誌級別"
    )


def parse_arguments(
    parser: argparse.ArgumentParser, 
    args: Optional[List[str]] = None
) -> argparse.Namespace:
    """解析命令行參數.

    Args:
        parser: 參數解析器
        args: 要解析的參數列表，None 表示使用 sys.argv

    Returns:
        argparse.Namespace: 解析後的參數物件

    Raises:
        SystemExit: 當參數解析失敗或使用 --help 時

    Example:
        >>> parser = create_argument_parser()
        >>> args = parse_arguments(parser, ['--mode', 'backtest'])
        >>> print(args.mode)
        'backtest'
    """
    try:
        parsed_args = parser.parse_args(args)
        logger.debug("命令行參數解析成功: %s", parsed_args)
        return parsed_args
    except SystemExit as e:
        logger.info("參數解析結束，退出碼: %d", e.code)
        raise
    except Exception as e:
        logger.error("參數解析失敗: %s", e, exc_info=True)
        raise


def parse_args() -> argparse.Namespace:
    """解析命令行參數的便捷函數.

    Returns:
        argparse.Namespace: 解析後的參數物件，包含所有命令行選項

    Raises:
        SystemExit: 當參數解析失敗或使用 --help 時

    Example:
        >>> args = parse_args()
        >>> print(args.mode)
        'backtest'
    """
    parser = create_argument_parser()
    return parse_arguments(parser)


def get_argument_help(parser: argparse.ArgumentParser) -> str:
    """獲取參數幫助信息.

    Args:
        parser: 參數解析器

    Returns:
        str: 格式化的幫助信息

    Example:
        >>> parser = create_argument_parser()
        >>> help_text = get_argument_help(parser)
        >>> print(help_text)
    """
    return parser.format_help()


def validate_argument_combinations(args: argparse.Namespace) -> bool:
    """驗證參數組合的有效性.

    Args:
        args: 解析後的參數物件

    Returns:
        bool: 參數組合是否有效

    Raises:
        ValueError: 當參數組合無效時

    Example:
        >>> args = parse_args()
        >>> is_valid = validate_argument_combinations(args)
        >>> print(f"參數組合有效: {is_valid}")
    """
    # 檢查日期參數組合
    if args.start_date and not args.end_date:
        raise ValueError("指定開始日期時必須同時指定結束日期")
    
    if args.end_date and not args.start_date:
        raise ValueError("指定結束日期時必須同時指定開始日期")
    
    # 檢查實盤交易模式的特殊要求
    if args.mode == "live" and args.broker == "simulator":
        raise ValueError("實盤交易模式不能使用模擬券商")
    
    # 檢查數值範圍
    if args.initial_capital <= 0:
        raise ValueError("初始資金必須大於 0")
    
    if not 0 <= args.max_position_size <= 1:
        raise ValueError("最大持倉比例必須在 0-1 之間")
    
    if not 0 <= args.max_portfolio_risk <= 1:
        raise ValueError("最大投資組合風險必須在 0-1 之間")
    
    if args.interval <= 0:
        raise ValueError("執行間隔必須大於 0")
    
    logger.info("參數組合驗證通過")
    return True
