"""YAML 用例扫描器：递归发现 *_cases.yaml，展开 data_matrix，按 depends_on 拓扑排序。"""
from __future__ import annotations

import copy
import itertools
from pathlib import Path

import yaml


def _expand_matrix(case: dict) -> list[dict]:
    """data_matrix 笛卡尔积展开：API_001 -> API_001_1 / API_001_2 / ..."""
    matrix = case.pop("data_matrix", None) or {}
    if not matrix:
        return [case]
    keys = list(matrix.keys())
    expanded = []
    for idx, combo in enumerate(itertools.product(*(matrix[k] for k in keys)), start=1):
        c = copy.deepcopy(case)
        c["id"] = f"{case['id']}_{idx}"
        c["_matrix"] = dict(zip(keys, combo))
        expanded.append(c)
    return expanded


def _topo_sort(cases: list[dict]) -> list[dict]:
    """按 depends_on 拓扑排序（被依赖用例先执行）；缺依赖/循环依赖直接报错。"""
    by_id = {c["id"]: c for c in cases}
    if len(by_id) != len(cases):
        dupes = [cid for cid in by_id if sum(1 for c in cases if c["id"] == cid) > 1]
        raise ValueError(f"用例 ID 重复: {dupes}")
    order: list[dict] = []
    state: dict[str, str] = {}

    def visit(case: dict) -> None:
        cid = case["id"]
        if state.get(cid) == "done":
            return
        if state.get(cid) == "visiting":
            raise ValueError(f"depends_on 存在循环依赖: {cid}")
        state[cid] = "visiting"
        for dep in case.get("depends_on") or []:
            if dep not in by_id:
                raise ValueError(f"用例 {cid} 依赖的用例不存在: {dep}")
            visit(by_id[dep])
        state[cid] = "done"
        order.append(case)

    for c in cases:
        visit(c)
    return order


#: 用例 YAML 的扫描根目录（相对项目目录）。
#: data/api 是历史约定；api/cases 与 pytest 入口 test_yaml_cases.py 同目录，便于就近维护。
CASE_SCAN_ROOTS = ("data/api", "api/cases")


def discover_yaml_cases(project_dir) -> tuple[list[dict], list[str]]:
    """递归扫描用例根目录下的 **/*_cases.yaml，返回 (cases, ids)。

    扫描根见 CASE_SCAN_ROOTS（默认 data/api 与 api/cases，二者并存且按路径去重）。
    """
    files: list[Path] = []
    seen: set[Path] = set()
    for root in CASE_SCAN_ROOTS:
        data_dir = Path(project_dir) / Path(root)
        if not data_dir.is_dir():
            continue
        for f in sorted(data_dir.rglob("*_cases.yaml")):
            key = f.resolve()
            if key not in seen:
                seen.add(key)
                files.append(f)
    cases: list[dict] = []
    for f in files:
        doc = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        meta = doc.get("meta") or {}
        file_vars = doc.get("variables") or {}
        for raw in doc.get("test_cases") or []:
            if not raw.get("id"):
                raise ValueError(f"{f.name} 存在缺少 id 的用例: {raw.get('title')}")
            case = copy.deepcopy(raw)
            case.setdefault("module", meta.get("module", "API"))
            case["_variables"] = file_vars
            case["_meta"] = meta
            cases.extend(_expand_matrix(case))
    cases = _topo_sort(cases)
    return cases, [c["id"] for c in cases]
