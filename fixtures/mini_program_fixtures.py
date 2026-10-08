"""小程序夹具（Minium）：先确保微信开发者工具自动化端口开启；未安装时自动跳过。"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def mini_program(runtime_ctx):
    pytest.importorskip("minium",
                        reason="未安装 minium（pip install minium，并开启微信开发者工具自动化端口）")
    from engines.mini_program.devtools import open_devtools_port
    from engines.mini_program.minium_factory import create_minium

    conf = dict(runtime_ctx.config.get("miniprogram") or {})
    open_devtools_port(conf.get("cli_path"), conf.get("project_path"),
                       port=int(conf.get("port", 9420)))
    mini = create_minium(conf)
    yield mini
    mini.close()
