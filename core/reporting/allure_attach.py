"""Allure 附件：用例失败时自动挂载 run.log / case log / API 最近请求响应记录。"""
from __future__ import annotations

import allure

from core.logging.logger import sanitize_case_id


def _attach_text(name: str, body: str):
    allure.attach(body, name=name, attachment_type=allure.attachment_type.TEXT)


def attach_api_exchanges(client, count: int = 20) -> None:
    """把客户端最近 N 次请求/响应（已脱敏）挂到 Allure。"""
    for ex in list(client.exchanges)[-count:]:
        allure.attach(ex.to_json(), name=f"API {ex.method} {ex.path} -> {ex.status}",
                      attachment_type=allure.attachment_type.JSON)


def attach_failure_evidence(item) -> None:
    """pytest_runtest_makereport 失败钩子里调用：三合一失败归因附件。"""
    ctx = item.config._af_ctx

    run_log = ctx.output.run_dir / "run.log"
    if run_log.is_file():
        _attach_text("失败归因-运行日志(run.log)",
                     run_log.read_text(encoding="utf-8", errors="ignore")[-8000:])

    case_log = ctx.output.cases_dir / f"{sanitize_case_id(item.nodeid)}.log"
    if case_log.is_file():
        _attach_text("失败归因-用例日志(case log)",
                     case_log.read_text(encoding="utf-8", errors="ignore"))

    client = (getattr(item, "funcargs", None) or {}).get("api_client")
    if client is not None:
        attach_api_exchanges(client)
