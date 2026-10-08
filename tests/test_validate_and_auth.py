"""断言类型与鉴权模块的离线自测。"""
from __future__ import annotations

import httpx
import pytest

from engines.api.assertions import apply_op, apply_check, get_response_value
from engines.api.auth import AuthError, apply_api_auth
from engines.api.client import ApiClient


def resp(status=200, body=None, headers=None):
    return httpx.Response(status, json=body if body is not None else {"code": 0, "data": {"id": 1, "tags": ["a", "b"]}},
                          headers=headers or {"Content-Type": "application/json"},
                          request=httpx.Request("GET", "http://mock.local/x"))


# ---------------- 检查路径 ----------------

def test_get_value_status_code_and_headers_and_json():
    r = resp()
    assert get_response_value(r, "status_code") == 200
    assert get_response_value(r, "headers.Content-Type") == "application/json"
    assert get_response_value(r, "json")["code"] == 0
    assert get_response_value(r, "json.data.id") == 1
    assert get_response_value(r, "json.data.tags[1]") == "b"


# ---------------- 20 种断言类型 ----------------

@pytest.mark.parametrize("op,actual,expect", [
    ("eq", 1, 1), ("ne", 1, 2), ("contains", "hello", "ell"), ("not_contains", "hello", "xyz"),
    ("exists", None, None), ("not_empty", "x", None), ("regex", "abc123", r"\d+"),
    ("in", "a", ["a", "b"]), ("gt", 5, 3), ("ge", 3, 3), ("lt", 1, 3), ("le", 3, 3),
    ("len_eq", [1, 2], 2), ("len_gt", [1, 2, 3], 2), ("len_lt", [1], 2),
    ("type", "s", "str"), ("type", 1, "int"), ("is_true", 1, None), ("is_false", 0, None),
])
def test_apply_op_pass(op, actual, expect):
    apply_op(actual, op, expect, label="t")


@pytest.mark.parametrize("op,actual,expect", [
    ("eq", 1, 2), ("ne", 1, 1), ("contains", "hello", "zzz"), ("not_contains", "hello", "ell"),
    ("not_empty", "", None), ("regex", "abc", r"^\d+$"), ("in", "c", ["a", "b"]),
    ("gt", 1, 3), ("len_eq", [1], 2), ("type", "s", "int"), ("type", True, "int"),
    ("is_true", 0, None), ("is_false", 1, None),
])
def test_apply_op_fail(op, actual, expect):
    with pytest.raises(AssertionError):
        apply_op(actual, op, expect, label="t")


def test_exists_and_not_exists_semantics():
    apply_op(None, "exists", None, label="t", exists=True)
    with pytest.raises(AssertionError):
        apply_op(None, "exists", None, label="t", exists=False)
    apply_check(resp(), "json.no.such.path", "not_exists", None)
    with pytest.raises(AssertionError):
        apply_check(resp(), "json.no.such.path", "exists", None)


def test_unknown_op_raises_valueerror():
    with pytest.raises(ValueError, match="未知断言类型"):
        apply_op(1, "no_such_op", None, label="t")


# ---------------- 鉴权 ----------------

def _auth_client(handler) -> ApiClient:
    return ApiClient(base_url="http://mock.local", transport=httpx.MockTransport(handler))


def login_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/login":
        query = dict(request.url.params)
        body = __import__("json").loads(request.content or b"{}")
        mobile = body.get("mobile") or query.get("mobile")
        if mobile == "13800000000":
            return httpx.Response(200, json={"code": 0, "data": "TOKEN_OK"})
        return httpx.Response(200, json={"code": 1001, "message": "密码错误"})
    return httpx.Response(200, json={"seen": request.headers.get("token", "")})


def test_auth_login_success_sets_custom_header():
    client = _auth_client(login_handler)
    ctx = {}
    apply_api_auth(client, {
        "type": "login",
        "request": {"method": "POST", "path": "/login", "params": {"mobile": "13800000000", "password": "x"}},
        "token_path": "json.data", "header_name": "token", "token_prefix": "",
    }, context=ctx)
    assert ctx["auth_token"] == "TOKEN_OK"
    r = client.get("/anything")
    assert r.json()["seen"] == "TOKEN_OK"
    client.close()


def test_auth_login_failure_raises_autherror():
    client = _auth_client(login_handler)
    with pytest.raises(AuthError):
        apply_api_auth(client, {
            "type": "login",
            "request": {"method": "POST", "path": "/login", "params": {"mobile": "wrong", "password": "x"}},
            "token_path": "json.data",
        })
    client.close()


def test_auth_bearer_and_unknown_type():
    client = _auth_client(login_handler)
    apply_api_auth(client, {"type": "bearer", "token": "xyz"})
    assert client._client.headers["Authorization"] == "Bearer xyz"
    with pytest.raises(AuthError):
        apply_api_auth(client, {"type": "no_such"})
    client.close()
