"""统一运行入口。

处理三个易错点：
1. 启动 pytest 前先清空 outputs/{project}/{env}/{type}/allure-results/ —— 否则 Allure 结果
   跨执行累加，报告用例数翻倍。
2. pytest 退出码非 0 时跳过报告生成并在 stderr 输出警告 —— 否则会用上一次旧结果生成误导性报告。
3. Windows 下 Allure CLI 命令是 allure.bat，subprocess 调用时按操作系统补全命令名。

报告流程：pytest 成功 -> allure generate --clean -> 把报告 history 持久化到 _history/
（下次运行前复制回 results 以保留趋势图）-> --open 时 allure open 拉起服务。

用法:
    python scripts/run.py --project project_a --env test --type api --generate-report
    python scripts/run.py --project project_miaosha --env test --type api --mark "api and p0" --generate-report --open
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve_allure_cmd(allure: str) -> str:
    """按操作系统补全 Allure CLI 命令名（Windows 下补全 allure.bat）。"""
    if os.name == "nt" and not Path(allure).suffix:
        found = shutil.which(allure) or shutil.which(allure + ".bat")
        return found or (allure + ".bat")
    return allure


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


def copy_tree(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="automation-framework 统一运行入口")
    parser.add_argument("--project", required=True, help="被测项目名（projects/ 下目录名）")
    parser.add_argument("--env", default="test", help="运行环境")
    parser.add_argument("--type", default="api",
                        choices=["api", "web_ui", "app", "mini_program", "all"])
    parser.add_argument("--mark", default=None, help="pytest -m 标记表达式，如 'api and p0'")
    parser.add_argument("--allure", default="allure", help="Allure CLI 命令/路径")
    parser.add_argument("--generate-report", action="store_true", help="生成 Allure 报告")
    parser.add_argument("--open", action="store_true", help="生成并打开 Allure 报告服务")
    args = parser.parse_args()

    type_dir = ROOT / "outputs" / args.project / args.env / args.type
    results = type_dir / "allure-results"
    report = type_dir / "allure-report"
    history = type_dir / "_history"

    # 易错点 1：先清空旧的 allure-results
    clean_dir(results)

    cmd = [sys.executable, "-m", "pytest", f"projects/{args.project}",
           "--project", args.project, "--env", args.env, "--type", args.type, "-v",
           # 易错点 4：必须显式指定 --alluredir，否则 allure-pytest 一条结果都不写，
           # 生成的报告就是 0 条用例（Environment 有值、用例全是 ???）
           "--alluredir", str(results), "--clean-alluredir"]
    if args.mark:
        cmd += ["-m", args.mark]
    print(f"[run] {' '.join(cmd)}")

    exit_code = subprocess.call(cmd, cwd=ROOT)

    # 易错点 2：pytest 失败时跳过报告生成，避免旧结果生成误导性报告
    if exit_code != 0:
        print(f"[run][WARN] pytest 退出码 {exit_code}，跳过 Allure 报告生成", file=sys.stderr)
        sys.exit(exit_code)

    if args.generate_report or args.open:
        # 趋势图：把上次持久化的 history 复制回 results
        copy_tree(history, results / "history")
        allure_cmd = resolve_allure_cmd(args.allure)
        code = subprocess.call([allure_cmd, "generate", str(results),
                                "-o", str(report), "--clean"], cwd=ROOT)
        if code != 0:
            print(f"[run][WARN] Allure 报告生成失败（退出码 {code}，请确认已安装 allure CLI）",
                  file=sys.stderr)
            sys.exit(code)
        # 持久化本次 history，供下次运行恢复趋势
        copy_tree(report / "history", history)
        print(f"[run] Allure 报告已生成: {report}")
        if args.open:
            subprocess.call([allure_cmd, "open", str(report)], cwd=ROOT)


if __name__ == "__main__":
    main()
