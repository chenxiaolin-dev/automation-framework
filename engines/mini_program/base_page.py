"""小程序 BasePage（POM 基类骨架）：Minium 页面操作统一封装。

具体 API（get_element / inner_text 等）以 minium 官方文档为准。
"""
from __future__ import annotations

from loguru import logger


class MiniBasePage:
    PAGE_PATH = ""

    def __init__(self, mini):
        self.mini = mini

    def open(self):
        logger.info(f"[MP] 打开 {self.PAGE_PATH}")
        return self.mini.reLaunch(self.PAGE_PATH)

    def element_text(self, selector: str, max_depth: int = 5) -> str:
        page = self.mini.current_page
        return page.get_element(selector, max_depth=max_depth).inner_text
