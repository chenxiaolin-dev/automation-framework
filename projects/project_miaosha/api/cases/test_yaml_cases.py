from pathlib import Path

import allure
import pytest

from engines.api.case_loader import discover_yaml_cases
from engines.api.yaml_runner import run_case

PROJECT_DIR = Path(__file__).parents[2]
CASES, IDS = discover_yaml_cases(PROJECT_DIR)


@allure.epic("秒杀商城")
@allure.feature("API")
@pytest.mark.api
@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_api_yaml_case(api_client, api_context, case):
    allure.dynamic.story(case.get("module", "API"))
    allure.dynamic.title(f"[{case.get('level')}] {case['title']}")
    for tag in case.get("tags", []):
        allure.dynamic.tag(tag)
    run_case(api_client, case, context=api_context)
