"""统一断言工具：检查路径解析 + 20 种断言类型（validate / setup/teardown assert 共用）。"""
from __future__ import annotations

import re
from typing import Any

_TYPE_MAP = {"str": str, "int": int, "float": float, "list": list,
             "dict": dict, "bool": bool, "none": type(None), "null": type(None)}


def get_response_value(resp, path: str) -> Any:
    """检查路径：status_code / headers.Content-Type / json / json.data.token / json.data.items[0].id"""
    path = path.strip()
    if path == "status_code":
        return resp.status_code
    if path.startswith("headers."):
        return resp.headers.get(path[len("headers."):])
    if path == "json":
        return resp.json()
    if path.startswith("json."):
        return _walk(resp.json(), path[len("json."):])
    raise ValueError(f"不支持的检查路径: {path}")


def _walk(node: Any, path: str) -> Any:
    for tok in re.findall(r"[^\.\[\]]+|\[\d+\]", path):
        if tok.startswith("[") and tok.endswith("]"):
            node = node[int(tok[1:-1])]
        elif isinstance(node, dict) and tok in node:
            node = node[tok]
        else:
            raise KeyError(f"路径不存在: {path}（断在 '{tok}'）")
    return node


def _fail(label: str, op: str, expect, actual, extra: str = ""):
    raise AssertionError(f"断言失败 [{label}] {op}: 期望 {expect!r}, 实际 {actual!r}{extra}")


def apply_op(actual, op: str, expect, label: str, exists: bool = True) -> None:
    """单条断言求值（供响应 validate 与 setup/teardown 的 context 断言共用）。"""
    op = (op or "eq").lower()
    if op == "exists":
        if not exists:
            _fail(label, op, expect, actual, "（路径不存在）")
        return
    if op == "not_exists":
        if exists:
            _fail(label, op, expect, actual, "（路径存在）")
        return
    if not exists:
        _fail(label, op, expect, actual, "（路径不存在）")

    if op == "eq":
        if not actual == expect:
            _fail(label, op, expect, actual)
    elif op == "ne":
        if not actual != expect:
            _fail(label, op, expect, actual)
    elif op == "contains":
        if expect not in actual:
            _fail(label, op, expect, actual)
    elif op == "not_contains":
        if expect in actual:
            _fail(label, op, expect, actual)
    elif op == "not_empty":
        if actual is None or actual == "" or (hasattr(actual, "__len__") and len(actual) == 0):
            _fail(label, op, expect, actual)
    elif op == "regex":
        if not re.search(str(expect), str(actual)):
            _fail(label, op, expect, actual)
    elif op == "in":
        if actual not in expect:
            _fail(label, op, expect, actual)
    elif op in ("gt", "ge", "lt", "le"):
        try:
            ok = {"gt": actual > expect, "ge": actual >= expect,
                  "lt": actual < expect, "le": actual <= expect}[op]
        except TypeError as e:
            _fail(label, op, expect, actual, f"（不可比较: {e}）")
        if not ok:
            _fail(label, op, expect, actual)
    elif op == "len_eq":
        if not len(actual) == expect:
            _fail(label, op, expect, len(actual))
    elif op == "len_gt":
        if not len(actual) > expect:
            _fail(label, op, expect, len(actual))
    elif op == "len_lt":
        if not len(actual) < expect:
            _fail(label, op, expect, len(actual))
    elif op == "type":
        t = _TYPE_MAP.get(str(expect).lower())
        if t is None:
            raise ValueError(f"未知类型名: {expect}")
        if t is int and isinstance(actual, bool):
            _fail(label, op, expect, type(actual).__name__)
        if not isinstance(actual, t):
            _fail(label, op, expect, type(actual).__name__)
    elif op == "is_true":
        if not actual:
            _fail(label, op, expect, actual)
    elif op == "is_false":
        if actual:
            _fail(label, op, expect, actual)
    else:
        raise ValueError(f"未知断言类型: {op}")


def apply_check(resp, path: str, op: str, expect) -> None:
    """对响应执行一条 validate 规则。"""
    exists = True
    try:
        actual = get_response_value(resp, path)
    except Exception:  # noqa: BLE001 路径缺失交给 exists/not_exists 语义处理
        actual, exists = None, False
    apply_op(actual, op, expect, label=path, exists=exists)
