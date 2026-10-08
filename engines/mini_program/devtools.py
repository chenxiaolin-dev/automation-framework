"""微信开发者工具自动化端口辅助：检测端口，未开启则调用 CLI 拉起。"""
from __future__ import annotations

import socket
import subprocess
import time


def is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, int(port))) == 0


def open_devtools_port(cli_path: str | None, project_path: str | None,
                       port: int = 9420, wait: float = 20) -> None:
    """确保微信开发者工具已开启自动化端口（cli auto --project ... --auto-port N）。"""
    if is_port_open(port):
        return
    if not cli_path or not project_path:
        raise RuntimeError(
            f"自动化端口 {port} 未开启，且配置缺少 miniprogram.cli_path / project_path")
    subprocess.run([cli_path, "auto", "--project", str(project_path),
                    "--auto-port", str(port)], check=False, timeout=60)
    deadline = time.time() + wait
    while time.time() < deadline:
        if is_port_open(port):
            return
        time.sleep(0.5)
    raise RuntimeError(f"微信开发者工具自动化端口 {port} 拉起超时")
