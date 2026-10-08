"""APP 引擎驱动工厂（Appium 骨架）：Android UiAutomator2 / iOS XCUITest。"""
from __future__ import annotations

from loguru import logger


def _make_options(options_cls, caps: dict):
    options = options_cls()
    for k, v in (caps or {}).items():
        options.set_capability(k, v)
    return options


def create_android_driver(app_conf: dict):
    try:
        from appium import webdriver
        from appium.options.android import UiAutomator2Options
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("未安装 Appium-Python-Client: pip install Appium-Python-Client") from e

    server = app_conf.get("server_url", "http://127.0.0.1:4723")
    options = _make_options(UiAutomator2Options, app_conf.get("capabilities"))
    logger.info(f"Appium Android driver 启动: server={server}")
    return webdriver.Remote(server, options=options)


def create_ios_driver(app_conf: dict):
    try:
        from appium import webdriver
        from appium.options.ios import XCUITestOptions
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("未安装 Appium-Python-Client: pip install Appium-Python-Client") from e

    server = app_conf.get("server_url", "http://127.0.0.1:4723")
    options = _make_options(XCUITestOptions, app_conf.get("capabilities"))
    logger.info(f"Appium iOS driver 启动: server={server}")
    return webdriver.Remote(server, options=options)
