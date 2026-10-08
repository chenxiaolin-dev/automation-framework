"""Allure 元数据：environment.properties（环境信息）+ executor.json（执行者/CI 信息）。"""
from __future__ import annotations

import json
import os
import platform


def write_allure_metadata(ctx) -> None:
    results = ctx.output.allure_results
    results.mkdir(parents=True, exist_ok=True)

    api = ctx.config.get("api") or {}
    web = ctx.config.get("web_ui") or {}
    lines = [
        f"Project={ctx.project}",
        f"Env={ctx.env}",
        f"Type={ctx.test_type}",
        f"RunId={ctx.run_id}",
        f"Python={platform.python_version()}",
        f"OS={platform.platform()}",
        f"ApiBaseUrl={api.get('base_url', '')}",
        f"WebBaseUrl={web.get('base_url', '')}",
    ]
    (results / "environment.properties").write_text("\n".join(lines) + "\n", encoding="utf-8")

    executor = {
        "name": os.environ.get("CI_NAME") or os.environ.get("BUILD_NAME") or "local",
        "type": "jenkins" if os.environ.get("JENKINS_URL") else "local",
        "buildName": os.environ.get("BUILD_NAME") or f"{ctx.project}-{ctx.env}-{ctx.run_id}",
        "buildOrder": os.environ.get("BUILD_NUMBER") or ctx.run_id,
        "reportURL": os.environ.get("BUILD_URL") or "",
    }
    (results / "executor.json").write_text(
        json.dumps(executor, ensure_ascii=False, indent=2), encoding="utf-8")
