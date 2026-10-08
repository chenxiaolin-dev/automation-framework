"""日志脱敏：敏感字段（密码/token/鉴权头等）统一掩码后才能进入日志与 Allure 附件。"""
from __future__ import annotations

import re

SENSITIVE_KEY = re.compile(
    r"(password|passwd|pwd|token|authorization|secret|api[_-]?key|credential|mobile)", re.I)
MASK = "******"


def redact(value):
    """递归掩码 dict 中键名命中敏感规则的值；list 逐项处理；其他类型原样返回。"""
    if isinstance(value, dict):
        return {k: (MASK if SENSITIVE_KEY.search(str(k)) else redact(v))
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


def redact_headers(headers) -> dict:
    return redact(dict(headers or {}))
