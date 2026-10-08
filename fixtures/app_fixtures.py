"""APP 夹具（Appium）：设备锁保证并发时同一设备串行使用；未安装时自动跳过。"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def android_driver(runtime_ctx):
    pytest.importorskip("appium",
                        reason="未安装 Appium-Python-Client（pip install Appium-Python-Client，并启动 appium 服务）")
    from engines.app.device_lock import device_lock
    from engines.app.driver_factory import create_android_driver

    conf = runtime_ctx.config.get("app") or {}
    caps = conf.get("capabilities") or {}
    udid = caps.get("udid") or caps.get("deviceName") or "default-device"
    with device_lock(udid):
        driver = create_android_driver(conf)
        yield driver
        driver.quit()
