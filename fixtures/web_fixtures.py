"""Web UI 夹具（Playwright）：未安装时自动跳过。"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def web_page(runtime_ctx):
    pytest.importorskip("playwright.sync_api",
                        reason="未安装 playwright（pip install playwright && playwright install chromium）")
    from engines.web_ui.config import create_page
    pw, browser, context, page = create_page(runtime_ctx.config)
    yield page
    browser.close()
    pw.stop()
