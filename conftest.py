"""pytest 全局入口。

pytest_configure：RuntimeContext 构建（pytest 参数 > AF_* 环境变量 > 默认值）、
配置加载（${ENV.KEY} 替换）、输出目录、双层日志、Allure 元数据、生产环境保护。
pytest_collection_modifyitems：按 --project 过滤、按 --type 过滤、YAML 用例 level/tags 自动映射 marker。
pytest_runtest_makereport：失败自动挂载 run.log / case log / API 最近请求响应。
"""
from __future__ import annotations

import os
import importlib.util

import allure  # noqa: F401  确保依赖存在
import pytest
from loguru import logger

from core.config.loader import RuntimeContext, build_runtime_context
from core.logging.logger import add_case_sink, remove_case_sink, setup_run_logging
from core.reporting.allure_attach import attach_failure_evidence
from core.reporting.allure_metadata import write_allure_metadata

pytest_plugins = [
    "fixtures.api_fixtures",
    "fixtures.web_fixtures",
    "fixtures.app_fixtures",
    "fixtures.mini_program_fixtures",
    "fixtures.data_fixtures",
]

TYPE_MARKERS = ("api", "web_ui", "app", "mini_program")
PROD_ALIASES = ("prod", "production")


def _option_or_env(config, option_name: str, env_key: str, default: str) -> str:
    return os.environ.get(env_key) or config.getoption(option_name) or default


def pytest_addoption(parser):
    group = parser.getgroup("automation-framework")
    group.addoption("--project", action="store", default="project_a",
                    help="被测项目名（projects/ 下的目录名），也可用环境变量 AF_PROJECT")
    group.addoption("--env", action="store", default="test",
                    help="运行环境（config/ 下的 yaml 名），也可用环境变量 AF_ENV")
    group.addoption("--type", action="store", default="all",
                    choices=["api", "web_ui", "app", "mini_program", "all"],
                    help="测试方向过滤，也可用环境变量 AF_TEST_TYPE")
    group.addoption("--allow-prod", action="store_true", default=False,
                    help="允许在生产环境执行（还需配置 safety.allow_prod_execution: true）")


def _export_auth_env(ctx) -> None:
    """把 config/{env}.yaml 的 api.auth.request.data 导出成 TEST_* 环境变量。

    用例里用 ${ENV.TEST_MOBILE} / ${ENV.TEST_PASSWORD} 引用即可，账号密码不必写进用例文件
    （见 docs/用例编写规范.md 第五节）。CI 若已预设同名环境变量，以 CI 的为准。
    """
    data = (((ctx.config.get("api") or {}).get("auth") or {}).get("request") or {}).get("data") or {}
    for key, value in data.items():
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            os.environ.setdefault(f"TEST_{str(key).upper()}", str(value))
    if data:
        logger.debug(f"[auth-env] 已从 api.auth 导出: {sorted(f'TEST_{k.upper()}' for k in data)}")


def pytest_configure(config):
    ctx = build_runtime_context(
        project=_option_or_env(config, "--project", "AF_PROJECT", "project_a"),
        env=_option_or_env(config, "--env", "AF_ENV", "test"),
        test_type=_option_or_env(config, "--type", "AF_TEST_TYPE", "all"),
        log_level=_option_or_env(config, "--log-level", "AF_LOG_LEVEL", "INFO"),
    )
    _export_auth_env(ctx)

    # 直接跑 pytest（不经 scripts/run.py）时给 allure-pytest 一个默认结果目录，
    # 否则一条 *-result.json 都不写，Allure 报告会是 0 条用例（??? ）。
    # 用户显式传了 --alluredir 则尊重用户的选择。
    if getattr(config.option, "allure_report_dir", None) is None \
            and importlib.util.find_spec("allure_pytest") is not None:
        config.option.allure_report_dir = str(ctx.output.allure_results)
        config.option.clean_alluredir = True  # 直接 pytest 跑时避免跨执行累加旧结果

    # ---- 生产环境保护：--allow-prod 与配置开关缺一不可 ----
    if ctx.env in PROD_ALIASES:
        allowed = (config.getoption("--allow-prod")
                   and (ctx.config.get("safety") or {}).get("allow_prod_execution") is True)
        if not allowed:
            raise pytest.UsageError(
                "[生产环境保护] --env=prod 被拒绝：需要 1) 命令行同时传入 --allow-prod；"
                "2) 配置文件中 safety.allow_prod_execution: true。")

    ctx.output.ensure()
    setup_run_logging(ctx)
    write_allure_metadata(ctx)

    config._af_ctx = ctx  # 供夹具与 hook 取用


def pytest_collection_modifyitems(config, items):
    ctx: RuntimeContext = config._af_ctx
    project_prefix = f"projects/{ctx.project}/".replace("\\", "/")

    selected, deselected = [], []
    for item in items:
        nodeid = item.nodeid.replace("\\", "/")
        if nodeid.startswith("tests/"):  # 框架自身测试不受项目过滤影响
            selected.append(item)
            continue
        if not nodeid.startswith(project_prefix):
            deselected.append(item)
            continue
        if ctx.test_type != "all" and not any(m.name in TYPE_MARKERS for m in item.iter_markers()):
            item.add_marker(pytest.mark.skip(reason=f"--type={ctx.test_type}：用例未标记任何测试方向"))
        selected.append(item)
        _auto_mark_yaml_case(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = selected


def _auto_mark_yaml_case(item) -> None:
    """YAML 用例按 level(p0/p1/p2) 和 tags 自动添加 pytest marker。"""
    callspec = getattr(item, "callspec", None)
    case = callspec.params.get("case") if callspec else None
    if not isinstance(case, dict):
        return
    level = str(case.get("level", "")).lower()
    if level in ("p0", "p1", "p2"):
        item.add_marker(getattr(pytest.mark, level))
    for tag in case.get("tags") or []:
        item.add_marker(getattr(pytest.mark, str(tag)))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed:
        try:
            attach_failure_evidence(item)
        except Exception as e:  # noqa: BLE001 附件失败不影响用例结果
            logger.warning(f"失败归因附件挂载异常: {e}")


@pytest.fixture(autouse=True)
def _case_logging(request):
    """按用例隔离日志：每条用例独立的 case log 文件 + 日志上下文（worker/case）。"""
    ctx = request.config._af_ctx
    nodeid = request.node.nodeid
    sink_id = add_case_sink(ctx, nodeid)
    short = nodeid.split("::")[-1] if "::" in nodeid else nodeid
    with logger.contextualize(case=short, worker=os.environ.get("PYTEST_XDIST_WORKER", "0")):
        yield
    remove_case_sink(sink_id)


@pytest.fixture(scope="session")
def runtime_ctx(request) -> RuntimeContext:
    """运行上下文（配置、输出目录等）。"""
    return request.config._af_ctx
