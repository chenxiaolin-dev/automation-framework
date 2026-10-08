"""Web UI 引擎配置读取 + Playwright 启动封装（骨架）。"""
from __future__ import annotations


def create_page(config: dict):
    """按 web_ui 配置段启动浏览器，返回 (playwright, browser, context, page)。

    依赖: pip install playwright && playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("未安装 playwright: pip install playwright && playwright install chromium") from e

    conf = config.get("web_ui") or {}
    pw = sync_playwright().start()
    browser = getattr(pw, conf.get("browser", "chromium")).launch(
        headless=bool(conf.get("headless", True)))
    context = browser.new_context(
        base_url=conf.get("base_url", ""),
        viewport=conf.get("viewport") or {"width": 1366, "height": 768},
        storage_state=conf.get("storage_state") or None,  # 复用 UI 登录态
    )
    page = context.new_page()
    return pw, browser, context, page
