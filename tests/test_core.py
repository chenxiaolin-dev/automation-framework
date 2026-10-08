"""底座模块自测：配置加载（${ENV.KEY}）/ 脱敏 / 数据工厂 / 输出目录。"""
from __future__ import annotations

import re

import pytest

from core.config.loader import ConfigError, _subst_env
from core.data.factory import call_fake, fake
from core.logging.redaction import redact
from core.paths import OutputLayout


# ---------------- 配置加载 ----------------

def test_subst_env_replaces(monkeypatch):
    monkeypatch.setenv("AF_CFG_KEY", "v1")
    assert _subst_env({"a": "${ENV.AF_CFG_KEY}", "b": ["x${ENV.AF_CFG_KEY}y"]}) == \
        {"a": "v1", "b": ["xv1y"]}


def test_subst_env_missing_raises():
    with pytest.raises(ConfigError):
        _subst_env("${ENV.AF_SURELY_MISSING_KEY_XYZ}")


def test_subst_env_keeps_other_placeholders():
    # 非 ENV 占位符（如 ${fake.name}）不由配置层处理，原样保留
    assert _subst_env({"url": "http://<被测服务地址>", "v": "${fake.name}"}) == \
        {"url": "http://<被测服务地址>", "v": "${fake.name}"}


# ---------------- 脱敏 ----------------

def test_redact_masks_sensitive_keys():
    out = redact({"mobile": "13800000000", "password": "p@ss", "Authorization": "Bearer x",
                  "nested": {"token": "t", "plain": "ok"}, "list": [{"secret": 1}]})
    assert out["mobile"] == "******"
    assert out["password"] == "******"
    assert out["Authorization"] == "******"
    assert out["nested"]["token"] == "******"
    assert out["nested"]["plain"] == "ok"
    assert out["list"][0]["secret"] == "******"


def test_redact_keeps_normal_values():
    assert redact({"name": "张三", "age": 18}) == {"name": "张三", "age": 18}


# ---------------- 数据工厂 / 隔离 ----------------

def test_fake_singleton():
    assert fake() is fake()


def test_call_fake_unknown_method_raises_valueerror():
    with pytest.raises(ValueError):
        call_fake("no_such_method_xyz")


def test_call_fake_phone_matches_cn_mobile():
    assert re.fullmatch(r"1\d{10}", str(call_fake("phone_number")))


def test_unique_data_is_unique():
    from core.data.isolation import unique_value
    values = {unique_value("u") for _ in range(50)}
    assert len(values) == 50


# ---------------- 输出目录 ----------------

def test_output_layout_dirs():
    layout = OutputLayout("project_a", "test", "api", run_id="20260101_000000")
    layout.ensure()
    assert layout.run_dir.name == "20260101_000000"
    assert layout.run_dir.is_dir() and layout.cases_dir.is_dir()
    assert "project_a" in str(layout.allure_results) and layout.allure_results.name == "allure-results"
