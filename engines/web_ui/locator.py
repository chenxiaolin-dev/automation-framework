"""定位器构造助手：POM 中集中声明定位，禁止散落在用例里。"""
from __future__ import annotations


class Locator:
    """统一返回 Playwright 选择器字符串。"""

    @staticmethod
    def css(value: str) -> str:
        return value

    @staticmethod
    def css_id(value: str) -> str:
        return f"#{value}"

    @staticmethod
    def xpath(value: str) -> str:
        return f"xpath={value}"

    @staticmethod
    def text(value: str) -> str:
        return f"text={value}"

    @staticmethod
    def attr(name: str, value: str) -> str:
        return f"[{name}='{value}']"
