"""测试数据隔离：生成跨用例/跨进程不重复的数据值，避免并行执行数据污染。"""
from __future__ import annotations

import itertools
import time

from core.data.factory import fake

_counter = itertools.count(1)


def unique_value(prefix: str = "data") -> str:
    """唯一测试数据值：前缀_时间戳_序号_随机数。"""
    return (f"{prefix}_{time.strftime('%Y%m%d%H%M%S')}"
            f"_{next(_counter)}_{fake().random_int(100, 999)}")
