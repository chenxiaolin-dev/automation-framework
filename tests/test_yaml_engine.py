"""框架自身离线测试：变量解析 / data_matrix / depends_on / 引擎端到端（MockTransport）。"""
from __future__ import annotations

import json

import httpx
import jsonschema
import pytest

from engines.api import yaml_runner as yr
from engines.api.case_loader import _expand_matrix, _topo_sort, discover_yaml_cases
from engines.api.client import ApiClient


def make_client(handler) -> ApiClient:
    return ApiClient(base_url="http://mock.local", transport=httpx.MockTransport(handler))


def echo_handler(request: httpx.Request) -> httpx.Response:
    """模拟服务：/login 发 token；/get 回显 query 与 header；/post 回显 body。"""
    if request.url.path == "/login":
        return httpx.Response(200, json={"code": 0, "data": {"token": "T123"}})
    if request.url.path == "/get":
        return httpx.Response(200, json={"args": dict(request.url.params),
                                         "token_header": request.headers.get("token", ""),
                                         "origin": "1.2.3.4"})
    if request.url.path == "/post":
        return httpx.Response(200, json={"json": json.loads(request.content or b"{}")})
    if request.url.path == "/delete":
        return httpx.Response(200, json={"code": 0})
    return httpx.Response(404, json={"code": 404})


# ---------------- 变量解析 ----------------

def test_resolve_fake_and_concat():
    out = yr.resolve_value("某路${fake.building_number}号", [])
    assert out.startswith("某路") and out.endswith("号") and out != "某路${fake.building_number}号"


def test_resolve_unknown_var_raises():
    with pytest.raises(yr.CaseError):
        yr.resolve_value("${not_defined_anywhere}", [{}, {}])


def test_resolve_unknown_fake_method_raises_valueerror():
    with pytest.raises(ValueError):
        yr.resolve_value("${fake.no_such_method_xyz}", [])


def test_resolve_env_var(monkeypatch):
    monkeypatch.setenv("AF_TEST_TOKEN_X", "abc123")
    assert yr.resolve_value("${ENV.AF_TEST_TOKEN_X}", []) == "abc123"


def test_resolve_env_var_missing_raises():
    with pytest.raises(yr.CaseError):
        yr.resolve_value("${ENV.AF_SURELY_NOT_SET_XYZ}", [])


def test_resolve_preserves_type_for_full_match():
    assert yr.resolve_value("${val}", [{"val": 42}]) == 42


# ---------------- data_matrix / depends_on ----------------

def test_matrix_expansion_ids():
    case = {"id": "API_X_001", "title": "t", "data_matrix": {"a": [1, 2], "b": ["x"]}}
    expanded = _expand_matrix(dict(case))
    assert [c["id"] for c in expanded] == ["API_X_001_1", "API_X_001_2"]
    assert expanded[0]["_matrix"] == {"a": 1, "b": "x"}
    assert expanded[1]["_matrix"] == {"a": 2, "b": "x"}


def test_topo_sort_orders_dependencies_first():
    cases = [{"id": "C", "depends_on": ["B"]}, {"id": "A"}, {"id": "B", "depends_on": ["A"]}]
    assert [c["id"] for c in _topo_sort(cases)] == ["A", "B", "C"]


def test_topo_sort_cycle_raises():
    cases = [{"id": "A", "depends_on": ["B"]}, {"id": "B", "depends_on": ["A"]}]
    with pytest.raises(ValueError, match="循环依赖"):
        _topo_sort(cases)


def test_topo_sort_missing_dep_raises():
    with pytest.raises(ValueError, match="不存在"):
        _topo_sort([{"id": "A", "depends_on": ["GHOST"]}])


def test_discover_from_tmp_project(tmp_path):
    data = tmp_path / "data" / "api"
    data.mkdir(parents=True)
    (data / "x_cases.yaml").write_text(
        "meta: {module: '演示'}\n"
        "test_cases:\n"
        "  - id: A_001\n    title: t1\n    request: {path: /get}\n"
        "  - id: A_002\n    title: t2\n    depends_on: [A_001]\n    request: {path: /get}\n",
        encoding="utf-8")
    cases, ids = discover_yaml_cases(tmp_path)
    assert ids == ["A_001", "A_002"]
    assert cases[0]["module"] == "演示"


# ---------------- 引擎端到端 ----------------

def test_runner_e2e_validate_extract_depends():
    client = make_client(echo_handler)
    ctx = {}
    yr.run_case(client, {
        "id": "T_001", "title": "登录提取", "level": "p0",
        "request": {"method": "POST", "path": "/login", "json": {"u": "x"}},
        "validate": [{"check": "status_code", "assert": "eq", "expect": 200},
                     {"check": "json.code", "assert": "eq", "expect": 0}],
        "extract": {"token": "json.data.token"},
    }, ctx)
    assert ctx["token"] == "T123"

    # 模拟鉴权头注入后，再发起依赖用例
    client.set_header("token", ctx["token"])
    yr.run_case(client, {
        "id": "T_002", "title": "用上游 token 回显", "level": "p1",
        "depends_on": ["T_001"],
        "request": {"path": "/get", "params": {"t": "${token}"}},
        "validate": [{"check": "json.token_header", "assert": "eq", "expect": "T123"}],
    }, ctx)


def test_runner_setup_teardown_and_assert_action():
    client = make_client(echo_handler)
    ctx = {}
    yr.run_case(client, {
        "id": "T_003", "title": "setup/teardown", "level": "p1",
        "setup": [{"action": "set", "name": "marker", "value": "m1"},
                  {"action": "log", "message": "准备 ${marker}"},
                  {"action": "request", "name": "前置删除",
                   "request": {"method": "POST", "path": "/delete"},
                   "validate": [{"check": "status_code", "assert": "eq", "expect": 200}]}],
        "request": {"path": "/get", "params": {"m": "${marker}"}},
        "validate": [{"check": "json.args.m", "assert": "eq", "expect": "m1"}],
        "teardown": [{"action": "assert", "check": "context.marker", "assert": "eq", "expect": "m1"},
                     {"action": "wait", "seconds": 0}],
    }, ctx)


def test_runner_schema_fail():
    client = make_client(echo_handler)
    with pytest.raises(jsonschema.ValidationError):
        yr.run_case(client, {
            "id": "T_004", "title": "schema 不匹配", "level": "p2",
            "request": {"path": "/get"},
            "schema": {"type": "object", "required": ["no_such_field"]},
        }, {})


def test_runner_meta_default_method():
    """request 未写 method 时取 meta.default_method。"""
    client = make_client(echo_handler)
    resp = yr.run_case(client, {
        "id": "T_005", "title": "默认 POST", "level": "p2",
        "_meta": {"default_method": "POST"},
        "request": {"path": "/post", "json": {"a": 1}},
        "validate": [{"check": "json.json.a", "assert": "eq", "expect": 1}],
    }, {})
    assert resp.status_code == 200
