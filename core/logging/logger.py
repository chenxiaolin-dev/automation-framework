"""日志初始化：run.log（全局）+ case log（按用例隔离），上下文带 worker/case/nodeid。"""
from __future__ import annotations

import os
import re
import sys

from loguru import logger

from core.logging.redaction import redact

_ready = False
_CASE_ID_SAFE = re.compile(r"[^A-Za-z0-9_\-\.]+")


def sanitize_case_id(nodeid: str) -> str:
    """把 nodeid 转成安全文件名。"""
    return _CASE_ID_SAFE.sub("_", nodeid.replace("::", "__"))[:150]


def setup_run_logging(ctx) -> None:
    """会话级初始化：控制台 + run.log 双输出。全局只执行一次。"""
    global _ready
    if _ready:
        return
    worker = os.environ.get("PYTEST_XDIST_WORKER", "0")
    logger.configure(extra={"case": "-", "worker": worker})
    logger.remove()
    logger.add(
        sys.stderr,
        level=ctx.log_level,
        format=("<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | "
                "[w{extra[worker]}] {extra[case]} - <level>{message}</level>"),
    )
    logger.add(
        ctx.output.run_dir / "run.log",
        level="DEBUG",
        encoding="utf-8",
        rotation="20 MB",
        retention="10 days",
        format=("{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <7} | [w{extra[worker]}] "
                "{extra[case]} | {name}:{function} - {message}"),
    )
    _ready = True
    logger.info(f"run_id={ctx.run_id} project={ctx.project} env={ctx.env} "
                f"type={ctx.test_type} log_dir={ctx.output.run_dir}")


def add_case_sink(ctx, nodeid: str) -> int:
    """为单条用例挂一个独立日志 sink（outputs/.../cases/<nodeid>.log）。"""
    path = ctx.output.cases_dir / f"{sanitize_case_id(nodeid)}.log"
    return logger.add(
        path,
        level="DEBUG",
        encoding="utf-8",
        format="{time:HH:mm:ss.SSS} | {level: <7} | {name} - {message}",
    )


def remove_case_sink(sink_id: int) -> None:
    try:
        logger.remove(sink_id)
    except ValueError:
        pass


def log_redacted(message: str, payload) -> None:
    logger.info(f"{message}: {redact(payload)}")
