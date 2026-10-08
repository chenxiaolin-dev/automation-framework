"""数据清理注册表：用例/夹具注册清理回调，会话结束统一执行（异常互不影响）。"""
from __future__ import annotations

from collections.abc import Callable

from loguru import logger

_callbacks: list[Callable] = []


def register(fn: Callable) -> Callable:
    _callbacks.append(fn)
    return fn


def run_all() -> None:
    """执行并清空全部清理回调（单个失败不影响其他）。"""
    while _callbacks:
        fn = _callbacks.pop()
        try:
            fn()
        except Exception as e:  # noqa: BLE001 清理失败不阻断
            logger.warning(f"数据清理失败: {fn.__name__} -> {e}")


def clear() -> None:
    _callbacks.clear()
