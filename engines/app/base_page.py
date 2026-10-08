"""APP BasePage（POM 基类骨架）：Appium 元素操作统一封装。"""
from __future__ import annotations

from loguru import logger


class AppBasePage:
    def __init__(self, driver, timeout: int = 10):
        self.driver = driver
        self.timeout = timeout

    def _wait(self, locator: tuple, timeout: int | None = None):
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
        return WebDriverWait(self.driver, timeout or self.timeout).until(
            EC.visibility_of_element_located(locator))

    def click(self, locator: tuple):
        logger.info(f"[APP] 点击: {locator}")
        self._wait(locator).click()

    def input(self, locator: tuple, text: str):
        logger.info(f"[APP] 输入: {locator}")
        el = self._wait(locator)
        el.clear()
        el.send_keys(text)

    def text(self, locator: tuple) -> str:
        return self._wait(locator).text

    def screenshot(self, path: str):
        self.driver.save_screenshot(path)
        logger.info(f"[APP] 截图: {path}")
