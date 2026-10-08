"""数据类夹具：清理注册表 + 数据隔离 + Faker + 可选数据库。"""
from __future__ import annotations

import pytest

from core.data import cleanup, isolation
from core.data.factory import fake


@pytest.fixture(scope="session")
def cleanup_registry():
    """注册清理回调：cleanup_registry.register(fn)，会话结束统一执行。"""
    return cleanup


@pytest.fixture()
def unique_data():
    """唯一测试数据值生成器（跨用例/跨进程不重复）。"""
    return isolation.unique_value


@pytest.fixture()
def faker_cn():
    """Faker(zh_CN) 实例。"""
    return fake()


@pytest.fixture(scope="session")
def db(runtime_ctx):
    """可选数据库校验客户端：需配置 db: 段并安装 pymysql。"""
    pytest.importorskip("pymysql", reason="未安装 pymysql")
    from core.data.database import DB

    conf = runtime_ctx.config.get("db") or {}
    if not conf:
        pytest.skip("配置缺少 db 段")
    conn = DB(conf)
    yield conn
    conn.close()
