"""Faker 单例（zh_CN，懒加载）+ 安全调用入口。"""
from __future__ import annotations

from faker import Faker

_instance: Faker | None = None


def fake() -> Faker:
    global _instance
    if _instance is None:
        _instance = Faker("zh_CN")
    return _instance


def call_fake(method: str):
    """按方法名调用 Faker 生成随机值；方法不存在抛 ValueError（解析阶段即失败）。"""
    f = fake()
    if method.startswith("_") or not hasattr(f, method):
        raise ValueError(f"Faker 不存在方法: {method}（${{fake.{method}}}）")
    return getattr(f, method)()
