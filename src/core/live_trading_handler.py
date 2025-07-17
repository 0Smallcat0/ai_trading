"""
即時交易處理器模組

此模組負責處理模擬交易和實盤交易的共用邏輯，包括：
- 即時資料載入和更新
- 事件監控管理
- 交易主循環控制
- 錯誤處理和恢復

主要功能：
- 執行模擬交易模式
- 執行實盤交易模式
- 管理交易主循環
- 處理中斷和錯誤恢復

Example:
    >>> from src.core.live_trading_handler import run_paper_mode, run_live_mode
    >>> config = {"mode": "paper", "execution": {"interval": 60}, ...}
    >>> run_paper_mode(config)
"""

import logging
import time
from typing import Dict, Any, Optional

from .data_ingest import load_data, update_data
from .event_monitor import start as start_event_monitor
from .trading_cycle_executor import execute_trading_cycle, validate_trading_cycle_config

logger = logging.getLogger(__name__)


def initialize_trading_data() -> None:
    """初始化交易資料.

    Raises:
        RuntimeError: 當資料初始化失敗時

    Example:
        >>> initialize_trading_data()
        >>> print("交易資料初始化完成")
    """
    try:
        logger.info("載入初始資料...")
        load_data()
        
        logger.info("更新即時資料...")
        update_data()
        
        logger.info("交易資料初始化完成")
        
    except Exception as e:
        logger.error("初始化交易資料失敗: %s", e, exc_info=True)
        raise RuntimeError(f"初始化交易資料失敗: {e}") from e


def start_event_monitoring():
    """啟動事件監控.

    Returns:
        事件監控器物件

    Raises:
        RuntimeError: 當事件監控啟動失敗時

    Example:
        >>> event_monitor = start_event_monitoring()
        >>> print("事件監控已啟動")
    """
    try:
        logger.info("啟動事件監控...")
        event_monitor = start_event_monitor()
        logger.info("事件監控已啟動")
        return event_monitor
        
    except Exception as e:
        logger.error("啟動事件監控失敗: %s", e, exc_info=True)
        raise RuntimeError(f"啟動事件監控失敗: {e}") from e


def stop_event_monitoring(event_monitor) -> None:
    """停止事件監控.

    Args:
        event_monitor: 事件監控器物件

    Example:
        >>> event_monitor = start_event_monitoring()
        >>> stop_event_monitoring(event_monitor)
        >>> print("事件監控已停止")
    """
    try:
        if event_monitor:
            event_monitor.stop()
            logger.info("事件監控已停止")
    except Exception as e:
        logger.warning("停止事件監控時發生錯誤: %s", e)


def execute_trading_loop(config: Dict[str, Any], is_live_mode: bool = False) -> None:
    """執行交易主循環.

    Args:
        config: 系統配置字典
        is_live_mode: 是否為實盤交易模式

    Raises:
        RuntimeError: 當交易循環執行失敗時

    Example:
        >>> config = {"execution": {"interval": 60}, ...}
        >>> execute_trading_loop(config, is_live_mode=False)
    """
    interval = config["execution"]["interval"]
    mode_name = "實盤交易" if is_live_mode else "模擬交易"
    
    logger.info("進入%s主循環...", mode_name)
    
    try:
        while True:
            try:
                # 執行交易週期
                order_ids = execute_trading_cycle(config)
                
                if order_ids:
                    if is_live_mode:
                        logger.warning("🔴 實盤交易：執行了 %d 個訂單", len(order_ids))
                    else:
                        logger.info("本週期執行了 %d 個訂單", len(order_ids))

                # 等待下一次執行
                logger.debug("等待 %d 秒後執行下一週期", interval)
                time.sleep(interval)

            except KeyboardInterrupt:
                logger.info("收到中斷信號，停止%s", mode_name)
                break
            except Exception as e:
                logger.error("%s週期執行錯誤: %s", mode_name, e, exc_info=True)
                logger.info("等待 10 秒後重試...")
                time.sleep(10)
                
    except Exception as e:
        logger.error("%s主循環執行失敗: %s", mode_name, e, exc_info=True)
        raise RuntimeError(f"{mode_name}主循環執行失敗: {e}") from e


def validate_live_trading_config(config: Dict[str, Any]) -> None:
    """驗證即時交易配置.

    Args:
        config: 系統配置字典

    Raises:
        ValueError: 當配置參數不正確時

    Example:
        >>> config = {"execution": {"interval": 60, "broker": "ib"}, ...}
        >>> validate_live_trading_config(config)  # 不會拋出異常
    """
    # 驗證基本交易週期配置
    validate_trading_cycle_config(config)
    
    # 驗證執行配置
    if "execution" not in config:
        raise ValueError("即時交易配置缺少執行配置")
    
    execution_config = config["execution"]
    
    if "interval" not in execution_config:
        raise ValueError("執行配置缺少間隔設定")
    
    if execution_config["interval"] <= 0:
        raise ValueError("執行間隔必須大於 0")
    
    if "broker" not in execution_config:
        raise ValueError("執行配置缺少券商設定")


def run_paper_mode(config: Dict[str, Any]) -> None:
    """執行模擬交易模式.

    Args:
        config: 系統配置字典

    Raises:
        ValueError: 當配置參數不正確時
        RuntimeError: 當模擬交易執行失敗時

    Example:
        >>> config = {"mode": "paper", "execution": {"interval": 60}, ...}
        >>> run_paper_mode(config)
    """
    logger.info("開始模擬交易模式")

    try:
        # 驗證配置
        validate_live_trading_config(config)

        # 初始化資料
        initialize_trading_data()

        # 啟動事件監控
        event_monitor = start_event_monitoring()

        try:
            # 執行交易主循環
            execute_trading_loop(config, is_live_mode=False)
            
        finally:
            # 停止事件監控
            stop_event_monitoring(event_monitor)

    except (ValueError, RuntimeError):
        raise
    except Exception as e:
        logger.error("模擬交易模式啟動失敗: %s", e, exc_info=True)
        raise RuntimeError(f"模擬交易啟動失敗: {e}") from e

    logger.info("模擬交易模式結束")


def run_live_mode(config: Dict[str, Any]) -> None:
    """執行實盤交易模式.

    Args:
        config: 系統配置字典

    Raises:
        ValueError: 當配置參數不正確時
        RuntimeError: 當實盤交易執行失敗時

    Warning:
        實盤交易涉及真實資金，請確保充分測試後再使用

    Example:
        >>> config = {"mode": "live", "execution": {"broker": "ib"}, ...}
        >>> run_live_mode(config)
    """
    logger.warning("⚠️  開始實盤交易模式 - 涉及真實資金！")

    try:
        # 驗證配置
        validate_live_trading_config(config)
        
        # 額外的實盤交易驗證
        execution_config = config["execution"]
        if execution_config.get("broker") == "simulator":
            raise ValueError("實盤交易模式不能使用模擬券商")

        # 初始化資料
        initialize_trading_data()

        # 啟動事件監控
        event_monitor = start_event_monitoring()

        try:
            # 執行交易主循環
            execute_trading_loop(config, is_live_mode=True)
            
        finally:
            # 停止事件監控
            stop_event_monitoring(event_monitor)

    except (ValueError, RuntimeError):
        raise
    except Exception as e:
        logger.error("實盤交易模式啟動失敗: %s", e, exc_info=True)
        raise RuntimeError(f"實盤交易啟動失敗: {e}") from e

    logger.warning("實盤交易模式結束")


def get_trading_mode_status(config: Dict[str, Any]) -> Dict[str, Any]:
    """獲取交易模式狀態.

    Args:
        config: 系統配置字典

    Returns:
        Dict[str, Any]: 交易模式狀態資訊

    Example:
        >>> config = {"mode": "paper", ...}
        >>> status = get_trading_mode_status(config)
        >>> print(f"交易模式: {status['mode']}")
    """
    mode = config.get("mode", "unknown")
    execution_config = config.get("execution", {})
    
    return {
        "mode": mode,
        "broker": execution_config.get("broker", "unknown"),
        "interval": execution_config.get("interval", 0),
        "is_live_mode": mode == "live",
        "status": "ready",
    }


def create_trading_session_info(config: Dict[str, Any]) -> Dict[str, Any]:
    """創建交易會話資訊.

    Args:
        config: 系統配置字典

    Returns:
        Dict[str, Any]: 交易會話資訊

    Example:
        >>> config = {"mode": "paper", ...}
        >>> session_info = create_trading_session_info(config)
        >>> print(f"會話 ID: {session_info['session_id']}")
    """
    import uuid
    from datetime import datetime
    
    return {
        "session_id": str(uuid.uuid4()),
        "start_time": datetime.now(),
        "mode": config.get("mode", "unknown"),
        "broker": config.get("execution", {}).get("broker", "unknown"),
        "strategy": config.get("strategy", {}).get("name", "unknown"),
        "status": "initialized",
    }
