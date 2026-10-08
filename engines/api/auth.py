"""API 鉴权：bearer（静态 token）与 login（登录换取 token）两种模式。

login 模式的请求体支持三种写法（与 YAML 用例 request 保持一致）：
  params -> query string；json -> application/json；data -> application/x-www-form-urlencoded（表单）
"""
from __future__ import annotations

from engines.api.assertions import get_response_value


class AuthError(RuntimeError):
    """登录/鉴权失败（明确异常，便于定位配置问题）。"""


def apply_api_auth(client, auth_config: dict | None, context: dict | None = None) -> None:
    """按 projects/{project}/config/{env}.yaml 的 api.auth 配置为客户端写入鉴权头。"""
    if not auth_config:
        return
    auth_type = auth_config.get("type")

    if auth_type == "bearer":
        token = auth_config.get("token")
        if not token:
            raise AuthError("bearer 模式缺少 token 配置")
        client.set_header(auth_config.get("header_name", "Authorization"), f"Bearer {token}")
        if context is not None:
            context["auth_token"] = token
        return

    if auth_type == "login":
        req = auth_config.get("request") or {}
        if not req.get("path"):
            raise AuthError("login 模式缺少 request.path 配置")
        resp = client.request(str(req.get("method", "POST")).upper(), req["path"],
                              params=req.get("params"), json=req.get("json"),
                              data=req.get("data"), headers=req.get("headers"),
                              name="登录鉴权")
        if resp.status_code != 200:
            raise AuthError(f"登录接口返回 HTTP {resp.status_code}: {resp.text[:200]}")
        token_path = auth_config.get("token_path", "json.data")
        try:
            token = get_response_value(resp, token_path)
        except Exception as e:
            raise AuthError(f"token 提取失败（token_path={token_path}）: {e}") from e
        if not token:
            raise AuthError(f"token 提取结果为空（token_path={token_path}）")
        header_name = auth_config.get("header_name", "Authorization")
        prefix = auth_config.get("token_prefix", "")
        client.set_header(header_name, f"{prefix}{token}" if prefix else str(token))
        if context is not None:
            context["auth_token"] = token
        return

    raise AuthError(f"不支持的鉴权类型: {auth_type}（支持 bearer / login）")
