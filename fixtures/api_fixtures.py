"""API 引擎夹具：会话级 api_client（登录一次全共享）+ api_context（跨用例共享变量）。"""
from __future__ import annotations

import pytest

from core.data import cleanup
from engines.api.auth import apply_api_auth
from engines.api.client import ApiClient


@pytest.fixture(scope="session")
def api_context() -> dict:
    """跨用例共享变量字典：extract 提取 / auth_token 都存在这里。"""
    return {}


@pytest.fixture(scope="session")
def api_client(request, runtime_ctx, api_context):
    """会话级 API 客户端：创建 -> 登录鉴权一次 -> 整个会话共享（token 自动随请求发出）。

    结束时：执行注册的数据清理回调，再关闭客户端。
    """
    cfg = runtime_ctx.api_conf
    client = ApiClient(base_url=cfg.get("base_url", ""),
                       timeout=float(cfg.get("timeout", 10)),
                       headers=cfg.get("headers") or None)
    try:
        apply_api_auth(client, cfg.get("auth"), context=api_context)
        yield client
    finally:
        cleanup.run_all()
        client.close()
