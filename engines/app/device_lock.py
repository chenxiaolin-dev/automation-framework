"""设备互斥锁：多进程/多线程并发时，同一台设备串行使用（基于目录锁实现）。"""
from __future__ import annotations

import contextlib
import os
import tempfile
import time
from pathlib import Path


@contextlib.contextmanager
def device_lock(device_id: str, timeout: float = 300, poll: float = 0.5):
    lock_dir = Path(tempfile.gettempdir()) / "af_device_locks" / device_id.replace("/", "_")
    deadline = time.time() + timeout
    while True:
        try:
            os.makedirs(lock_dir)
            break
        except FileExistsError:
            if time.time() > deadline:
                raise TimeoutError(f"获取设备锁超时: {device_id}")
            time.sleep(poll)
    try:
        yield
    finally:
        try:
            os.rmdir(lock_dir)
        except OSError:
            pass
