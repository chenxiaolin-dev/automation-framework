"""运行上下文 + YAML 配置加载（支持 ${ENV.KEY} 占位替换为环境变量）。"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from core.paths import OutputLayout, ROOT

ENV_VAR_PATTERN = re.compile(r"\$\{ENV\.([A-Za-z_][A-Za-z0-9_]*)\}")

#: 生产环境名关键字（按 _ / - 分词后匹配，避免 "product" 之类被误判为生产环境）
PROD_ENV_TOKENS = frozenset({"prod", "production", "preprod"})


def is_prod_env(env: str) -> bool:
    """判断环境名是否属于生产环境。

    按 ``_`` / ``-`` 分词后做整词匹配，因此 ``prod``、``production``、``env_prod``、
    ``prod_cn``、``pre-prod`` 都会被识别为生产环境；而 ``product_test`` 这类
    含 "prod" 子串但非独立词的环境名不会误判。
    """
    tokens = re.split(r"[^A-Za-z0-9]+", str(env or "").strip().lower())
    return any(tok in PROD_ENV_TOKENS for tok in tokens if tok)


class ConfigError(RuntimeError):
    pass


@dataclass
class RuntimeContext:
    """一次 pytest 会话的运行上下文（pytest_configure 构建后挂到 config 上）。"""

    project: str
    env: str
    test_type: str
    log_level: str
    run_id: str
    config: dict
    output: OutputLayout

    @property
    def api_conf(self) -> dict:
        return self.config.get("api") or {}


def project_dir(project: str) -> Path:
    p = ROOT / "projects" / project
    if not p.is_dir():
        raise ConfigError(f"被测项目不存在: {p}")
    return p


def _subst_env(node):
    """递归把 ${ENV.KEY} 替换为操作系统环境变量，未设置直接报错。"""
    if isinstance(node, dict):
        return {k: _subst_env(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_subst_env(v) for v in node]
    if isinstance(node, str):
        def repl(m: "re.Match") -> str:
            key = m.group(1)
            if key not in os.environ:
                raise ConfigError(f"环境变量未设置: ENV.{key}（配置中出现 ${{ENV.{key}}}）")
            return os.environ[key]
        return ENV_VAR_PATTERN.sub(repl, node)
    return node


def load_project_config(project: str, env: str) -> dict:
    """加载 projects/{project}/config/{env}.yaml 并做环境变量替换。"""
    path = project_dir(project) / "config" / f"{env}.yaml"
    if not path.is_file():
        raise ConfigError(f"环境配置不存在: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return _subst_env(data)


def build_runtime_context(project: str, env: str, test_type: str,
                          log_level: str = "INFO") -> RuntimeContext:
    config = load_project_config(project, env)
    output = OutputLayout(project, env, test_type)
    return RuntimeContext(project=project, env=env, test_type=test_type,
                          log_level=log_level, run_id=output.run_id,
                          config=config, output=output)
