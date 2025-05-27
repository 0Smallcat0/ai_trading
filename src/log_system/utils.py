"""
日誌工具模組

此模組提供日誌系統的工具函數。
"""

import functools
import inspect
import logging
import time
import traceback
from typing import Any, Callable, List, Optional, TypeVar, cast

from src.log_system.config import LogCategory, log_with_context

# 類型變量
T = TypeVar("T")


def log_function_call(
    logger: logging.Logger,
    level: int = logging.INFO,
    log_args: bool = True,
    log_result: bool = True,
    log_execution_time: bool = True,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    記錄函數調用的裝飾器

    Args:
        logger: 日誌記錄器
        level: 日誌級別
        log_args: 是否記錄參數
        log_result: 是否記錄結果
        log_execution_time: 是否記錄執行時間
        category: 日誌類別
        tags: 標籤

    Returns:
        Callable: 裝飾器
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        """
        decorator

        Args:
            func:

        Returns:
            Callable[...]:
        """

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            """
            wrapper


            Returns:
                T:
            """
            func_name = func.__name__
            module_name = func.__module__
            qualname = func.__qualname__

            # 記錄開始信息
            start_msg = f"開始執行函數: {qualname}"
            start_time = time.time()

            # 準備上下文數據
            context_data = {
                "function": {
                    "name": func_name,
                    "module": module_name,
                    "qualname": qualname,
                }
            }

            # 記錄參數
            if log_args:
                # 獲取參數名稱
                sig = inspect.signature(func)
                param_names = list(sig.parameters.keys())

                # 處理位置參數
                args_dict = {}
                for i, arg in enumerate(args):
                    if i < len(param_names):
                        args_dict[param_names[i]] = _safe_repr(arg)
                    else:
                        args_dict[f"arg{i}"] = _safe_repr(arg)

                # 處理關鍵字參數
                kwargs_dict = {k: _safe_repr(v) for k, v in kwargs.items()}

                # 添加到上下文
                context_data["args"] = args_dict
                context_data["kwargs"] = kwargs_dict

            # 記錄開始信息
            log_with_context(
                logger=logger,
                level=level,
                msg=start_msg,
                category=category or LogCategory.SYSTEM,
                tags=tags,
                context=context_data,
            )

            try:
                # 執行函數
                result = func(*args, **kwargs)

                # 計算執行時間
                end_time = time.time()
                execution_time = end_time - start_time

                # 準備結果數據
                result_data = {}
                if log_result:
                    result_data["result"] = _safe_repr(result)
                if log_execution_time:
                    result_data["execution_time"] = execution_time

                # 記錄結束信息
                end_msg = f"結束執行函數: {qualname}"
                if log_execution_time:
                    end_msg += f" (執行時間: {execution_time:.6f}秒)"

                log_with_context(
                    logger=logger,
                    level=level,
                    msg=end_msg,
                    category=category or LogCategory.SYSTEM,
                    tags=tags,
                    context=context_data,
                    data=result_data,
                )

                return result
            except Exception as e:
                # 計算執行時間
                end_time = time.time()
                execution_time = end_time - start_time

                # 準備異常數據
                error_data = {
                    "exception": {
                        "type": type(e).__name__,
                        "message": str(e),
                        "traceback": traceback.format_exc(),
                    }
                }
                if log_execution_time:
                    error_data["execution_time"] = execution_time

                # 記錄異常信息
                error_msg = f"函數執行異常: {qualname} - {type(e).__name__}: {str(e)}"
                if log_execution_time:
                    error_msg += f" (執行時間: {execution_time:.6f}秒)"

                log_with_context(
                    logger=logger,
                    level=logging.ERROR,
                    msg=error_msg,
                    category=category or LogCategory.ERROR,
                    tags=tags,
                    context=context_data,
                    data=error_data,
                    exc_info=e,
                )

                # 重新拋出異常
                raise

        return cast(Callable[..., T], wrapper)

    return decorator


def log_method_call(
    level: int = logging.INFO,
    log_args: bool = True,
    log_result: bool = True,
    log_execution_time: bool = True,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    記錄方法調用的裝飾器

    Args:
        level: 日誌級別
        log_args: 是否記錄參數
        log_result: 是否記錄結果
        log_execution_time: 是否記錄執行時間
        category: 日誌類別
        tags: 標籤

    Returns:
        Callable: 裝飾器
    """

    def decorator(method: Callable[..., T]) -> Callable[..., T]:
        """
        decorator

        Args:
            method:

        Returns:
            Callable[...]:
        """

        @functools.wraps(method)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> T:
            """
            wrapper

            Args:
                self:

            Returns:
                T:
            """
            method_name = method.__name__
            class_name = self.__class__.__name__
            module_name = self.__class__.__module__
            qualname = f"{class_name}.{method_name}"

            # 獲取日誌記錄器
            logger = getattr(self, "logger", logging.getLogger(module_name))

            # 記錄開始信息
            start_msg = f"開始執行方法: {qualname}"
            start_time = time.time()

            # 準備上下文數據
            context_data = {
                "method": {
                    "name": method_name,
                    "class": class_name,
                    "module": module_name,
                    "qualname": qualname,
                }
            }

            # 記錄參數
            if log_args:
                # 獲取參數名稱
                sig = inspect.signature(method)
                param_names = list(sig.parameters.keys())

                # 處理位置參數
                args_dict = {}
                for i, arg in enumerate(args):
                    if i + 1 < len(param_names):  # +1 是因為第一個參數是 self
                        args_dict[param_names[i + 1]] = _safe_repr(arg)
                    else:
                        args_dict[f"arg{i}"] = _safe_repr(arg)

                # 處理關鍵字參數
                kwargs_dict = {k: _safe_repr(v) for k, v in kwargs.items()}

                # 添加到上下文
                context_data["args"] = args_dict
                context_data["kwargs"] = kwargs_dict

            # 記錄開始信息
            log_with_context(
                logger=logger,
                level=level,
                msg=start_msg,
                category=category or LogCategory.SYSTEM,
                tags=tags,
                context=context_data,
            )

            try:
                # 執行方法
                result = method(self, *args, **kwargs)

                # 計算執行時間
                end_time = time.time()
                execution_time = end_time - start_time

                # 準備結果數據
                result_data = {}
                if log_result:
                    result_data["result"] = _safe_repr(result)
                if log_execution_time:
                    result_data["execution_time"] = execution_time

                # 記錄結束信息
                end_msg = f"結束執行方法: {qualname}"
                if log_execution_time:
                    end_msg += f" (執行時間: {execution_time:.6f}秒)"

                log_with_context(
                    logger=logger,
                    level=level,
                    msg=end_msg,
                    category=category or LogCategory.SYSTEM,
                    tags=tags,
                    context=context_data,
                    data=result_data,
                )

                return result
            except Exception as e:
                # 計算執行時間
                end_time = time.time()
                execution_time = end_time - start_time

                # 準備異常數據
                error_data = {
                    "exception": {
                        "type": type(e).__name__,
                        "message": str(e),
                        "traceback": traceback.format_exc(),
                    }
                }
                if log_execution_time:
                    error_data["execution_time"] = execution_time

                # 記錄異常信息
                error_msg = f"方法執行異常: {qualname} - {type(e).__name__}: {str(e)}"
                if log_execution_time:
                    error_msg += f" (執行時間: {execution_time:.6f}秒)"

                log_with_context(
                    logger=logger,
                    level=logging.ERROR,
                    msg=error_msg,
                    category=category or LogCategory.ERROR,
                    tags=tags,
                    context=context_data,
                    data=error_data,
                    exc_info=e,
                )

                # 重新拋出異常
                raise

        return cast(Callable[..., T], wrapper)

    return decorator


def _safe_repr(obj: Any) -> Any:
    """
    安全地表示對象

    Args:
        obj: 對象

    Returns:
        Any: 安全表示
    """
    try:
        # 處理基本類型
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj

        # 處理列表和元組
        if isinstance(obj, (list, tuple)):
            return [_safe_repr(item) for item in obj]

        # 處理字典
        if isinstance(obj, dict):
            return {str(k): _safe_repr(v) for k, v in obj.items()}

        # 處理集合
        if isinstance(obj, set):
            return [_safe_repr(item) for item in obj]

        # 處理其他類型
        return str(obj)
    except Exception:
        return "<無法表示的對象>"
