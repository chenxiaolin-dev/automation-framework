"""小程序引擎工厂（腾讯官方 Minium 骨架）。"""
from __future__ import annotations

from loguru import logger


def create_minium(mp_conf: dict):
    try:
        import minium
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "未安装 minium: pip install minium（并通过微信开发者工具 CLI 开启自动化端口）") from e

    logger.info(f"Minium 启动: project_path={mp_conf.get('project_path')} port={mp_conf.get('port', 9420)}")
    return minium.MiniProgram(
        project_path=mp_conf.get("project_path"),
        cli_path=mp_conf.get("cli_path"),
        port=int(mp_conf.get("port", 9420)),
    )
