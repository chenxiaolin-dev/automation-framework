"""新项目脚手架生成器：一键生成 projects/<name> 标准骨架（框架代码零改动接入）。

用法:
    python tools/create_project.py project_c

生成后即可运行内置冒烟用例验证接入成功:
    python -m pytest projects/project_c --project project_c --type api
"""
import argparse
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECTS_DIR = BASE_DIR / "projects"

TEMPLATES: dict[str, str] = {
    "config/test.yaml": '''\
# 被测项目 {name} - 测试环境配置（更多环境：拷贝本文件为 prod.yaml 等）
# 支持环境变量占位符：${{ENV.KEY}} 会被替换为操作系统环境变量
project:
  name: "{name}"

api:
  base_url: "https://<被测服务地址>"   # TODO: 替换为真实测试环境地址
  timeout: 10
  headers:
    Accept: "application/json"
  # auth:                              # 可选，不配则裸发请求
  #   type: "login"
  #   request: {{method: POST, path: "/login", params: {{mobile: "...", password: "..."}}}}
  #   token_path: "json.data"
  #   header_name: "token"
  #   token_prefix: ""

web_ui:
  base_url: "https://<被测服务地址>"
  browser: "chromium"
  headless: true

safety:
  allow_prod_execution: false
''',
    "data/api/.gitkeep": "",
    "api/cases/test_yaml_cases.py": '''\
from pathlib import Path

import allure
import pytest

from engines.api.case_loader import discover_yaml_cases
from engines.api.yaml_runner import run_case

PROJECT_DIR = Path(__file__).parents[2]
CASES, IDS = discover_yaml_cases(PROJECT_DIR)


@allure.epic("{name}")
@allure.feature("API")
@pytest.mark.api
@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_api_yaml_case(api_client, api_context, case):
    allure.dynamic.story(case.get("module", "API"))
    allure.dynamic.title(f"[{{case.get('level')}}] {{case['title']}}")
    for tag in case.get("tags", []):
        allure.dynamic.tag(tag)
    run_case(api_client, case, context=api_context)
''',
}


def main():
    parser = argparse.ArgumentParser(description="生成新被测项目骨架")
    parser.add_argument("name", help="项目目录名，如 project_c")
    args = parser.parse_args()

    name = args.name.strip()
    if not name.replace("_", "").isalnum():
        sys.exit(f"非法项目名: {name}")
    target = PROJECTS_DIR / name
    if target.exists():
        sys.exit(f"项目已存在: {target}")

    created = []
    for rel, content in TEMPLATES.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.format(name=name), encoding="utf-8")
        created.append(path)
    # 三层包结构（防止多项目同名测试文件 import file mismatch）
    for d in ["", "api", "api/cases"]:
        (target / d / "__init__.py").write_text("", encoding="utf-8")

    print(f"[OK] 项目骨架已生成: {target}")
    for p in created:
        print(f"     - {p.relative_to(BASE_DIR)}")
    print(
        "\n下一步（约 5 分钟接入）:"
        "\n  1. 修改 config/test.yaml 中的 base_url / 登录鉴权配置"
        "\n  2. 在 data/api/ 下新建 *_cases.yaml 编写 YAML 用例（参考 project_a/data/api/demo_cases.yaml）"
        "\n  3. 运行验证: python -m pytest projects/" + name + " --project " + name + " --type api"
    )


if __name__ == "__main__":
    main()
