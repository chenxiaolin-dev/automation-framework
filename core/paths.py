"""输出目录规划：outputs/{project}/{env}/{type}/{run_id}/。"""
from __future__ import annotations

import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"


class OutputLayout:
    """一次运行的产物布局（run_id 精确到秒，目录按项目/环境/类型隔离）。"""

    def __init__(self, project: str, env: str, test_type: str, run_id: str | None = None):
        self.project = project
        self.env = env
        self.test_type = test_type
        self.run_id = run_id or time.strftime("%Y%m%d_%H%M%S")
        type_dir = OUTPUTS / project / env / test_type
        self.run_dir = type_dir / self.run_id
        self.cases_dir = self.run_dir / "cases"
        self.allure_results = type_dir / "allure-results"
        self.allure_report = type_dir / "allure-report"
        self.history_dir = type_dir / "_history"

    def ensure(self) -> "OutputLayout":
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.cases_dir.mkdir(parents=True, exist_ok=True)
        return self
