# automation-framework 通用自动化测试框架

支持 **接口 / Web UI / APP / 微信小程序** 四大测试方向的企业级 pytest 测试框架。
三层结构：**统一底座（core）+ 分方向引擎（engines）+ 多项目用例隔离（projects）**。

技术栈：Python 3.12+ · pytest · httpx · PyYAML · Loguru · Allure · Faker · jsonschema（可选：Playwright / Appium / Minium / pymysql）

> **开发方式说明**：本框架的代码由 AI 编码助手（Claude Code）生成；本人负责**需求定义、架构决策、
> 生成结果评审**（覆盖 / 正确性 / 独立性 / 数据 / 可维护 五维度），并以**真实服务端实测响应为准**
> 修正断言与用例实现。所有用例均在真实测试环境实跑验证。

## 目录结构

```
automation-framework/
├── conftest.py            # pytest 全局入口（RuntimeContext/过滤/失败归因，见下）
├── core/                  # 统一底座（不依赖任何测试方向）
│   ├── config/loader.py   #   RuntimeContext + YAML 配置加载（${ENV.KEY} 替换）
│   ├── paths.py           #   输出目录规划 outputs/{project}/{env}/{type}/{run_id}/
│   ├── logging/           #   logger.py（run.log + case log 双层）/ redaction.py（脱敏）
│   ├── reporting/         #   allure_metadata（environment.properties/executor.json）
│   │                      #   allure_attach（失败自动挂 run/case 日志 + API 交互）
│   └── data/              #   factory(Faker)/isolation/cleanup/database
├── engines/               # 分方向引擎
│   ├── api/               #   client / auth / yaml_runner / case_loader / assertions ★核心
│   ├── web_ui/            #   Playwright 骨架（config/base_page/locator）
│   ├── app/               #   Appium 骨架（driver_factory/device_lock/base_page）
│   └── mini_program/      #   Minium 骨架（minium_factory/devtools/base_page）
├── fixtures/              # pytest fixture 聚合：api/web/app/mini_program/data
├── projects/              # 被测项目资产（只依赖 engines 和 fixtures）
│   ├── project_a/         #   演示骨架（httpbin.org 公共服务，真实可跑）
│   └── project_miaosha/   #   秒杀商城实战（http://121.43.36.83:2001，表单格式+token 鉴权，54 条用例实跑通过）
├── scripts/run.py         # 统一运行入口（清空结果/失败不出报告/allure.bat 兼容）
├── tests/                 # 框架自身离线自测（63 条，MockTransport，不依赖外网）
├── tools/create_project.py# 新项目脚手架
└── docs/                  # 方案文档 + 用例编写规范
```

依赖方向：`projects/` 只依赖 `engines/` 和 `fixtures/`；新增被测项目不改框架代码。

## conftest.py 做了什么

- 命令行参数：`--project`（默认 project_a）、`--env`（默认 test）、`--type`（api/web_ui/app/mini_program/all）、`--allow-prod`；支持 `AF_PROJECT/AF_ENV/AF_TEST_TYPE/AF_LOG_LEVEL` 环境变量
- `pytest_configure`：构建 RuntimeContext → 加载 `projects/{project}/config/{env}.yaml`（`${ENV.KEY}` 替换）→ 创建 `outputs/{project}/{env}/{type}/{run_id}/` → 初始化 run.log + case log → 生成 Allure `environment.properties` 与 `executor.json` → **生产环境保护**（`--env prod` 必须同时 `--allow-prod` 且配置 `safety.allow_prod_execution: true`）
- `pytest_collection_modifyitems`：按项目前缀过滤；按 `--type` 过滤；YAML 用例按 level(p0/p1/p2) 和 tags 自动添加 marker
- `pytest_runtest_makereport`：失败自动挂载 run.log、case log、API 最近请求响应（脱敏）作为 Allure 附件

## API YAML 用例引擎（核心）

编写位置（引擎递归扫描两个根，见 `CASE_SCAN_ROOTS`）：`projects/<项目>/data/api/**/*_cases.yaml` 或 `projects/<项目>/api/cases/**/*_cases.yaml`（文件名必须 `_cases.yaml` 结尾，同一份用例不要两处都放）。
入口统一为 `api/cases/test_yaml_cases.py`（固定内容，无需修改）。

一条用例的执行流程：**setup 前置 → 主请求 → validate 断言 → schema 校验 → extract 提取 → teardown 后置**。

关键机制：

| 机制 | 说明 |
|---|---|
| 变量 `${name}` | 文件级 variables / extract 提取 / 上下文（api_context） |
| 变量 `${ENV.KEY}` | 操作系统环境变量，未设置报错 |
| 变量 `${fake.xxx}` | Faker(zh_CN) 同名方法，支持拼接（`"某路${fake.building_number}号"`），未知方法解析期报错 |
| 变量 `${field}` | data_matrix 展开字段 |
| data_matrix | 笛卡尔积展开：`API_001` → `API_001_1`、`API_001_2` |
| depends_on | 拓扑排序保证被依赖用例先执行，extract 变量跨用例传递（循环/缺失依赖报错） |
| validate | `check`（status_code / headers.X / json.a.b[0].c）+ `assert`（eq/ne/contains/not_contains/exists/not_empty/regex/in/gt/ge/lt/le/len_eq/len_gt/len_lt/type/is_true/is_false）+ `expect` |
| schema | jsonschema 响应结构校验 |
| setup/teardown | `log` / `wait` / `set` / `request`（支持 validate/extract/schema）/ `assert`（断言 context.xxx） |
| 鉴权 login | `config/{env}.yaml` 的 `api.auth.request` 支持 `params`(query) / `json` / `data`(表单) 三种传参，表单服务用 `data` |

完整用例格式见 `docs/用例编写规范.md` 与 `projects/project_miaosha/data/api/` 示例。

## 快速开始

```bash
pip install -r requirements.txt

# 框架自测（离线，63 条）
python -m pytest tests

# project_a 演示（httpbin.org，真实可跑，10 条）
python -m pytest --project project_a --type api

# 统一入口（处理 allure-results 清理 / 失败不出报告 / allure.bat）
python scripts/run.py --project project_a --env test --type api --generate-report

# 新项目接入
python tools/create_project.py project_c
```

## project_miaosha（秒杀商城实战 · 仅 API 方向）

- 被测服务：`http://121.43.36.83:2001`（松勤教育秒杀商城，测试环境，无需本地部署）
- 配置：`projects/project_miaosha/config/test.yaml`（已填真实值，可 `${ENV.KEY}` 覆盖）
  - 请求格式：**表单 `application/x-www-form-urlencoded`**（用例统一用 `request.data`）
  - 鉴权：`POST /login/redis/login`（mobile + password 加盐 MD5 + 万能验证码 9999）→ `json.data` 取 token → 自定义请求头 `token`
- 运行：
  ```bash
  python scripts/run.py --project project_miaosha --env test --type api --generate-report --open
  ```
- 用例分布（共 54 条，全部实跑通过）：

  | 文件 | 模块 | 条数 |
  |---|---|---|
  | `login_cases.yaml` | 登录鉴权（正向/密码错/验证码错/手机号不存在/缺参/无效 token） | 7 |
  | `address_cases.yaml` | 收货地址单接口（增/查/改/删 + 异常边界，脏数据 teardown 清理） | 21 |
  | `address_crud_cases.yaml` | 收货地址 CRUD 依赖链（extract + depends_on + data_matrix） | 10 |
  | `miaosha_cases.yaml` | 秒杀业务（重置库存→秒杀→结果轮询 / 重复秒杀 / 参数异常） | 13 |
  | `goods_cases.yaml` | 商品列表（结构断言，只读无脏数据） | 3 |

服务端已知特性（用例已按此设计断言）：
1. `update`/`delete` 的主键字段是 **`id`**（不是 addressId）；`isDefault` 用 `0`/`1`
2. 新增地址接口参数校验缺失（缺参也返回 `code=0`），异常用例断言从宽
3. `/miaosha/over/miaosha` 服务端自身异常、`/miaosha/testpath/miaosha` 需验证码，两条断言从宽
4. 秒杀用例前置 `GET /miaosha/reset` 重置库存，避免用例间互相影响

## 可选方向安装

```bash
pip install playwright && playwright install chromium   # Web UI
pip install Appium-Python-Client                        # APP（需启动 appium 服务）
pip install minium                                      # 小程序（需微信开发者工具自动化端口）
pip install pymysql                                     # 数据库校验
```
