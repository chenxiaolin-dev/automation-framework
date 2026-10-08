"""Web UI BasePage（POM 基类骨架）：页面操作统一封装（日志/等待/截图）。"""
from __future__ import annotations

from loguru import logger


class BasePage:
    def __init__(self, page):
        self.page = page

    def goto(self, path: str):
        logger.info(f"[UI] 打开页面: {path}")
        self.page.goto(path)

    def click(self, selector: str):
        logger.info(f"[UI] 点击: {selector}")
        self.page.click(selector)

    def fill(self, selector: str, text: str):
        logger.info(f"[UI] 输入: {selector} <- {text}")
        self.page.fill(selector, text)

    def text(self, selector: str) -> str:
        self.page.wait_for_selector(selector)
        return self.page.inner_text(selector)

    def screenshot(self, path: str):
        self.page.screenshot(path=path, full_page=True)
        logger.info(f"[UI] 截图: {path}")
