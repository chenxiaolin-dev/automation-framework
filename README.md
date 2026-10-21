# automation-framework

> **企业级通用自动化测试框架** —— 一套框架覆盖 **接口 / Web UI / APP / 微信小程序** 四个测试方向，多项目隔离、配置与代码分离、YAML 数据驱动。
>
> *A general-purpose enterprise test automation framework covering API / Web UI / Mobile App / WeChat Mini Program, with multi-project isolation and YAML-driven test cases.*

[![CI](https://github.com/chenxiaolin-dev/automation-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/chenxiaolin-dev/automation-framework/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![pytest](https://img.shields.io/badge/pytest-8.2%2B-0A9EDC?logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Allure](https://img.shields.io/badge/Allure-2.13%2B-FF4500?logo=Allure&logoColor=white)](https://allurereport.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 目录 / Table of Contents

- [English Summary](#english-summary)
- [核心特性](#核心特性)
- [架构](#架构)
- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [YAML 用例引擎](#yaml-用例引擎)
- [配置体系](#配置体系)
- [命令行与标记](#命令行与标记)
- [输出与报告](#输出与报告)
- [接入新项目](#接入新项目)
- [CI/CD](#cicd)
- [项目实例](#项目实例)
- [安全说明](#安全说明)
- [贡献指南](#贡献指南)
- [License](#license)

---

## English Summary

A pytest-based automation framework for teams that test **multiple products across multiple directions**.

- **Three-layer architecture** — `core/` (shared foundation) + `engines/` (per-direction engines) + `projects/` (per-product assets). Adding a product never touches framework code.
- **API direction is production-ready** — tests are written as YAML, not Python: variables, data matrices, dependency chains, 19 assertion operators, setup/teardown actions and JSON-Schema validation are all declarative.
- **Other directions are ready to extend** — Playwright (Web UI), Appium (App), Minium (Mini Program) engines and fixtures are in place; each is skipped automatically when its optional dependency is absent.
- **Self-hosted reporting** — Loguru dual-layer logs with credential redaction, Allure reports with automatic failure attribution (run log + per-case log + last 20 API exchanges).
- **Safety by default** — production environments are protected by a two-switch gate; requests and responses are redacted before they reach the report.

```bash
pip install -r requirements.txt
python -m pytest tests                  # 77 offline self-tests
python -m pytest projects/project_a --project project_a --type api   # 10 demo cases
```

---

## 核心特性

| 能力 | 说明 |
|---|---|
| **四方向统一** | 接口 / Web UI / APP / 小程序共用同一套底座、配置、日志、报告与 fixture 体系 |
| **多项目隔离** | 每个被测项目独占 `projects/<name>/` 目录，项目之间零耦合 |
| **配置与代码分离** | `config/{env}.yaml` 多环境切换，`${ENV.KEY}` 占位符注入敏感信息 |
| **YAML 数据驱动** | 接口用例全声明式编写，非测试同学也能直接维护 |
| **数据矩阵** | `data_matrix` 笛卡尔积自动展开，一条模板批量生成多条用例 |
| **依赖链** | `depends_on` 拓扑排序保证执行顺序，`extract` 跨用例传递变量 |
| **19 种断言** | 状态码 / JSON 路径 / 头 / 长度 / 类型 / 正则 / 比较，覆盖主流校验场景 |
| **失败自动归因** | 用例失败自动挂载运行日志、单例日志、最近 20 条 API 交互（已脱敏） |
| **日志脱敏** | `password` / `token` / `mobile` / `secret` 等敏感字段自动打码 |
| **生产保护** | 生产环境双开关校验，缺一即在收集阶段拒绝执行 |
| **开箱即用** | 附带演示项目 + 140 条实战用例 + 新项目脚手架生成器 |

---

## 架构

```
┌───────────────────────────────────────────────────────────┐
│  projects/<项目>/     被测项目资产（只依赖 engines + fixtures）  │
│    ├── config/{env}.yaml      环境配置（base_url / 鉴权 / 安全）    │
│    ├── data/api/*_cases.yaml  YAML 用例（约定位置）                  │
│    └── api/cases/             pytest 入口（固定模板，不改）            │
├───────────────────────────────────────────────────────────┤
│  engines/              分方向引擎                              │
│    ├── api/            ★ YAML 驱动，完整可用                     │
│    ├── web_ui/         Playwright 骨架                          │
│    ├── app/            Appium 骨架                              │
│    └── mini_program/   Minium 骨架                             │
├───────────────────────────────────────────────────────────┤
│  core/                 统一底座（不依赖任何测试方向）                 │
│    config/ paths/ logging/ reporting/ data/                    │
└───────────────────────────────────────────────────────────┘
```

**依赖方向是单向的**：`projects/` → `engines/` → `core/`。框架代码不包含任何项目信息，新项目接入**不改框架一行代码**。

---

## 快速开始

### 环境要求

- Python **3.12+**
- 依赖安装：`pip install -r requirements.txt`

### 三条命令跑起来

```bash
# 1) 框架自身离线自测（77 条，MockTransport 模拟请求，不依赖外网）
python -m pytest tests

# 2) 演示项目回归（project_a 指向公共 httpbin.org，10 条，验证 YAML 引擎全链路）
python -m pytest projects/project_a --project project_a --env test --type api

# 3) 统一入口（自动清理 allure-results + 生成 Allure 报告 + 打开报告服务）
python scripts/run.py --project project_a --env test --type api --generate-report --open
```

> `scripts/run.py` 会在 pytest 失败时**跳过报告生成**并返回 pytest 的退出码，避免用上一次的旧结果生成误导性报告。

### 可选方向安装

未安装对应依赖时，相关方向的用例会**自动跳过**（不影响其他方向）：

```bash
pip install playwright && playwright install chromium   # Web UI
pip install Appium-Python-Client                        # APP（需本机启动 appium 服务，默认 4723）
pip install minium                                      # 小程序（需微信开发者工具开启自动化端口）
pip install pymysql                                     # 数据库校验
```

---

## 目录结构

```
automation-framework/
├── conftest.py              # pytest 全局入口：参数解析 / 用例过滤 / 生产保护 / 失败归因
├── pytest.ini               # pytest 配置 + 14 个已注册 marker
├── requirements.txt
├── core/                    # ── 统一底座 ──
│   ├── config/loader.py     #   RuntimeContext + YAML 加载 + ${ENV.KEY} 替换 + 生产环境识别
│   ├── paths.py             #   输出目录规划 outputs/{project}/{env}/{type}/{run_id}/
│   ├── logging/             #   logger.py（run.log + case log 双层）/ redaction.py（脱敏）
│   ├── reporting/           #   allure_metadata.py / allure_attach.py（失败自动归因）
│   └── data/                #   factory(Faker) / isolation / cleanup / database
├── engines/                 # ── 分方向引擎 ──
│   ├── api/                 #   client / auth / yaml_runner / case_loader / assertions ★核心
│   ├── web_ui/              #   Playwright 骨架（config / base_page / locator）
│   ├── app/                 #   Appium 骨架（driver_factory / device_lock / base_page）
│   └── mini_program/        #   Minium 骨架（minium_factory / devtools / base_page）
├── fixtures/                # pytest fixture 聚合：api / web / app / mini_program / data
├── projects/                # ── 被测项目资产 ──
│   ├── project_a/           #   演示骨架（httpbin.org，10 条，真实可跑）
│   └── project_miaosha/     #   秒杀商城实战（140 条，表单格式 + token 鉴权）
├── scripts/run.py           # 统一运行入口
├── tests/                   # 框架自身离线自测（77 条）
├── tools/create_project.py  # 新项目脚手架生成器
├── ci/                      # Jenkinsfile / GitLab CI 示例
└── docs/                    # 方案文档 + 用例编写规范 + OpenAPI 原始资料
```

---

## YAML 用例引擎

**接口用例不写 Python，写 YAML。** 引擎扫描 `CASE_SCAN_ROOTS = ("data/api", "api/cases")` 两个根目录，递归加载所有 `*_cases.yaml` 文件。

> **约定**：新用例统一放 `projects/<项目>/data/api/**/*_cases.yaml`。
> `projects/<项目>/api/cases/` 只放 pytest 入口 `test_yaml_cases.py` 与 `__init__.py`。
> 同一份用例**不要在两个目录各放一份**（会被收集两遍并触发「用例 ID 重复」）。

### 一条用例的执行流程

```
setup 前置 → 主请求 → validate 断言 → schema 校验 → extract 提取 → teardown 后置
```

### 完整示例

```yaml
meta:
  module: "收货地址"        # Allure Story 分组
  default_method: POST      # 文件级默认方法，单条用例可覆盖

variables:
  keyword: "固定值"          # 文件级变量，用例中 ${keyword} 引用

test_cases:
  - id: API_ADDRESS_ADD_001 # 全局唯一
    title: "新增收货地址-正向"
    level: p0               # p0/p1/p2，自动映射 pytest marker
    tags: [smoke]           # 自动映射 pytest marker
    request:
      path: "/address/add"
      data:                 # 表单服务用 data，JSON 服务用 json
        receiverName: "${fake.name}"
        mobile: "${ENV.TEST_MOBILE}"
    validate:
      - check: status_code
        assert: eq
        expect: 200
      - check: json.code
        assert: eq
        expect: 0
    extract:
      address_id: "json.data.id"
    teardown:
      - action: request
        request:
          method: POST
          path: "/address/delete"
          data: {id: "${address_id}"}
```

### 变量四来源

| 写法 | 来源 | 示例 |
|---|---|---|
| `${name}` | 文件级 `variables` / `extract` 提取 / 上下文 `api_context` | `${address_id}` |
| `${ENV.KEY}` | 操作系统环境变量（未设置直接报错） | `${ENV.TEST_MOBILE}` |
| `${fake.xxx}` | Faker(zh_CN) 方法，支持字符串拼接 | `"某路${fake.building_number}号"` |
| `${field}` | `data_matrix` 展开字段 | `${page}` |

变量值本身含 `${...}` 时**最多递归解析 3 层**；整串就是一个变量时**保留原始类型**（`${page}` 不会变成字符串 `"1"`）。

### 关键机制

| 机制 | 说明 |
|---|---|
| `data_matrix` | 笛卡尔积展开：`API_001` → `API_001_1`、`API_001_2` |
| `depends_on` | 拓扑排序保证被依赖用例先执行，跨用例传值；循环依赖 / 依赖缺失会报错 |
| `validate` | `check`（取值路径）+ `assert`（断言操作符）+ `expect`（期望值） |
| `schema` | jsonschema 响应结构校验 |
| `setup` / `teardown` | 5 种动作：`log` / `wait` / `set` / `request` / `assert` |
| `extract` | 提取响应字段到上下文，供后续用例引用；路径缺失记 warning 不中断 |

### 断言操作符（19 种）

```
eq  ne  contains  not_contains  exists  not_exists  not_empty  regex  in
gt  ge  lt  le  len_eq  len_gt  len_lt  type  is_true  is_false
```

- `type` 支持的期望类型名：`str` / `int` / `float` / `list` / `dict` / `bool` / `none` / `null`
- 检查路径语法：`status_code`、`headers.Content-Type`、`json`、`json.data.token`、`json.data.items[0].id`
- 路径不存在时，`exists` / `not_exists` 走存在性语义，其它操作符按「路径不存在」失败

> **断言原则**：正向用例断言到业务码（`status_code eq 200` + `json.code eq 0`）；
> 异常用例断言从宽（`status_code lt 500` + `json.code exists`）—— 不臆造服务端没约定的错误码。

完整规范见 [`docs/用例编写规范.md`](docs/用例编写规范.md)。

---

## 配置体系

配置文件路径为 `projects/<项目>/config/{env}.yaml`，**文件名即环境名**：`--env test` → `config/test.yaml`。

```yaml
project:
  name: project_miaosha

api:
  base_url: "http://121.43.36.83:2001"
  timeout: 10
  headers:
    Accept: "application/json"
  auth:                          # 可选，不配则裸发请求
    type: "login"                 # bearer | login
    request:
      method: POST
      path: "/login/redis/login"
      data:                        # 表单；JSON 服务改用 json，query 改用 params
        mobile: "13588000000"
        password: "5c4fcc5add5d087de1e8534189c687f7"
        verifyCode: "9999"
    token_path: "json.data"       # 从登录响应中取 token 的路径
    header_name: "token"          # 服务端用自定义头，不是 Authorization
    token_prefix: ""

web_ui:
  base_url: "https://example.com"
  browser: "chromium"
  headless: true

safety:
  allow_prod_execution: false     # 生产环境双开关之一
```

### `${ENV.KEY}` 占位符

配置里写 `${ENV.MY_KEY}`，运行前注入同名环境变量即可；**未设置会直接报错**（避免静默用错环境）。

框架还会把 `api.auth.request.data` 的每个字段自动导出为 `TEST_<字段名大写>` 环境变量：

| 配置字段 | 自动导出的环境变量 |
|---|---|
| `data.mobile` | `TEST_MOBILE` |
| `data.password` | `TEST_PASSWORD` |
| `data.verifyCode` | `TEST_VERIFYCODE` |

用例里直接写 `${ENV.TEST_MOBILE}` 即可，**账号密码不必写进用例文件**。CI 若已预设同名变量，以 CI 的为准。

### 生产环境双开关

环境名按 `_` / `-` 分词后命中 `prod` / `production` / `preprod` 即视为生产环境
（`prod`、`env_prod`、`prod_cn`、`pre-prod` 都会被识别；`product_test` 不会误判）。

执行生产环境需要**同时**满足：

1. 命令行传入 `--allow-prod`
2. 配置文件中 `safety.allow_prod_execution: true`

缺一即在 collection 阶段拒绝执行（退出码 4），避免误跑生产数据。

---

## 命令行与标记

### 命令行参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--project` | `project_a` | 被测项目名（`projects/` 下的目录名） |
| `--env` | `test` | 运行环境（对应 `config/{env}.yaml`） |
| `--type` | `all` | 测试方向：`api` / `web_ui` / `app` / `mini_program` / `all` |
| `--allow-prod` | 关 | 允许在生产环境执行（还需配置开关） |
| `--log-level` | `INFO` | 日志级别（pytest 内置参数） |

**环境变量优先级高于命令行**：`AF_PROJECT` / `AF_ENV` / `AF_TEST_TYPE` / `AF_LOG_LEVEL`。

### 已注册 marker（14 个）

| 分类 | Marker |
|---|---|
| 测试方向 | `api` / `web_ui` / `app` / `mini_program` |
| 优先级 | `p0` / `p1` / `p2` |
| 用例类型 | `smoke` / `regression` / `negative` / `boundary` |
| 依赖链 | `crud` / `serial` / `cleanup` |

YAML 用例的 `level`（p0/p1/p2）与 `tags` 会**自动映射为 marker**，无需在 Python 入口里手工标注。

### 常用组合

```bash
# 只跑 P0 冒烟
python -m pytest projects/project_a --project project_a -m "api and p0 and smoke"

# 跑全量并生成报告
python scripts/run.py --project project_miaosha --env test --type api --generate-report

# 失败重跑 2 次（区分环境抖动与真实缺陷）
python -m pytest projects/project_miaosha --project project_miaosha --reruns 2
```

---

## 输出与报告

每次运行的产物都在 `outputs/{project}/{env}/{type}/` 下：

```
outputs/{project}/{env}/{type}/
├── {run_id}/                 # 每次运行独立目录（run_id = 时间戳）
│   ├── run.log               # 全局 DEBUG 日志（20MB 滚动，保留 10 天）
│   └── cases/<nodeid>.log    # 每条用例独立日志
├── allure-results/           # Allure 原始结果 + environment.properties + executor.json
├── allure-report/            # Allure HTML 报告
└── _history/                 # 趋势数据持久化（跨次运行保留）
```

**失败自动归因**：用例失败时自动挂载 3 份附件到 Allure —— 运行日志尾部、单例日志全文、最近 20 条 API 交互（请求/响应均已脱敏）。

**日志脱敏**：`password` / `passwd` / `pwd` / `token` / `authorization` / `secret` / `api_key` / `credential` / `mobile` 等字段名命中的值一律替换为 `******`。

---

## 接入新项目

```bash
python tools/create_project.py project_c
```

自动生成：

```
projects/project_c/
├── config/test.yaml           # 测试环境配置（含 TODO 占位）
├── config/prod.yaml           # 生产环境配置（默认拒绝执行）
├── data/api/smoke_cases.yaml  # 1 条冒烟用例（生成后即可直接跑通）
└── api/cases/test_yaml_cases.py  # pytest 入口（固定模板，不改）
```

接入步骤：

1. 改 `config/test.yaml` 的 `base_url` 与鉴权配置
2. 在 `data/api/` 下新建 `*_cases.yaml` 编写用例
3. 跑 `python -m pytest projects/project_c --project project_c --type api` 验证

**框架代码零改动。**

---

## CI/CD

仓库提供两份可直接参考的流水线配置：

| 文件 | 说明 |
|---|---|
| `.github/workflows/ci.yml` | GitHub Actions：框架自测 + 演示项目回归 + **生产保护校验** |
| `ci/Jenkinsfile` | Jenkins 声明式流水线（Allure 插件 + 产物归档） |
| `ci/gitlab-ci-example.yml` | GitLab CI 示例（按方向与环境调度） |

GitHub Actions 的三个 Job：

| Job | 内容 | 是否依赖外网 |
|---|---|---|
| `self-test` | 77 条框架自测 | 否 |
| `demo-api` | project_a 10 条演示用例 | 是（httpbin.org） |
| `prod-guard` | 校验生产环境双开关确实会拦截 | 否 |

**敏感信息注入**：把配置里的凭据改成 `${ENV.KEY}` 占位符，在 CI 的 Secrets / Variables 里注入，避免明文入库。

---

## 项目实例

### `project_a` —— 演示骨架

- 被测服务：公共 `https://httpbin.org`，**无需任何部署，clone 即可跑**
- 10 条用例，覆盖 GET / POST / 非 200 状态码 / 响应头 / 数据矩阵 / extract / depends_on / setup-teardown

### `project_miaosha` —— 秒杀商城实战

- 被测服务：`http://121.43.36.83:2001`（松勤教育秒杀商城测试环境，无需本地部署）
- 请求格式：**表单 `application/x-www-form-urlencoded`**（用例统一用 `request.data`）
- 鉴权：`POST /login/redis/login` → `json.data` 取 token → 放入自定义请求头 `token`

**140 条用例**（126 条 YAML 模板 + 14 条 `data_matrix` 展开）：

| 文件 | 模块 | 模板 | 展开 |
|---|---|---:|---:|
| `address_cases.yaml` | 收货地址 | 29 | 29 |
| `address_openapi_cases.yaml` | 收货地址 | 37 | 51 |
| `miaosha_manage_cases.yaml` | 秒杀管理 | 36 | 36 |
| `login_cases.yaml` | 登录鉴权 | 9 | 9 |
| `address_crud_cases.yaml` | 收货地址-CRUD链路 | 6 | 6 |
| `miaosha_cases.yaml` | 秒杀业务 | 5 | 5 |
| `goods_cases.yaml` | 商品 | 3 | 3 |
| `config_check_cases.yaml` | 配置自检 | 1 | 1 |
| **合计** | | **126** | **140** |

用例覆盖登录鉴权、收货地址 CRUD 与依赖链、秒杀业务、商品列表；正向 / 负向 / 边界三类场景齐备，产生脏数据的用例均配 teardown 清理。

> ⚠️ 该实例指向**共享测试环境**，并发跑会产生互相干扰（如秒杀「已购」去重状态）。详见 [`docs/openapi/`](docs/openapi/) 下的接口原始资料。

---

## 安全说明

> [!IMPORTANT]
> 本仓库为**公开仓库**，且 `projects/project_miaosha/config/test.yaml` 中提交了**测试环境**的
> 手机号、加盐 MD5 密码与万能验证码 `9999`。

请注意：

- 这些凭据**仅对共享测试环境有效**，无法用于任何生产系统
- 万能验证码 `9999` 是该测试环境的固有特性，服务端不校验验证码真实性
- 日志与 Allure 附件中，敏感字段名命中的值会自动脱敏为 `******`
- 如果你 fork 了本仓库，**请立即轮换这些凭据**，并把配置改为 `${ENV.KEY}` 形式

生产环境保护是双开关设计（见上文「生产环境双开关」），默认拒绝执行。

---

## 贡献指南

1. 新增用例一律放 `projects/<项目>/data/api/**/*_cases.yaml`，**不要**新建到 `api/cases/` 下
2. 用例 ID 全局唯一，命名带模块前缀（如 `API_ADDRESS_ADD_001`）
3. 新增 marker 必须先在 `pytest.ini` 的 `markers` 中注册
4. 提交前跑一遍 `python -m pytest tests`（框架自测必须全绿）
5. 产生脏数据的用例**必须**配 teardown 清理
6. 敏感信息不得写进用例文件与配置文件

### 开发环境

```bash
python -m pytest tests -q          # 框架自测
python -m pytest projects/project_a --project project_a --type api -v   # 演示回归
```

---

## License

[MIT](LICENSE) © chenxiaolin
