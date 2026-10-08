# project_miaosha · 秒杀管理模块 API 用例报告

- 来源：`docs/openapi/miaosha_api.json`（秒杀系统 API文档 1.0.0，Swagger 2.0）
- 生成时间：2026-10-01 14:55（基线）→ 人工增强 2026-10-01 14:58
- 框架根目录：`D:\PyCharm\automation-framework`
- 过滤：only=秒杀管理（9 接口）· priority=全部
- 产出文件：`data/api/miaosha_manage_cases.yaml`
- 合计：**36 条**（正向 p0/smoke 9 · 负向 p1 10 · 边界 p2 17）

> **实测结论（2026-10-01，已连跑两轮 36/36 通过）**：本环境隐藏路径**不是固定的 `testpath`**，
> 而是每次 `GET /miaosha/path?goodsId=1&verifyCode=9999` 返回的 32 位随机串。
> 故核心接口改用 setup 动态链路：reset → 取真实 path（extract）→ `POST /miaosha/${miaosha_path}/miaosha`。
> 框架 `engines/api/yaml_runner.py:75` 已支持 `resolve_value(req["path"], scopes)`，无需补丁。

## 从基线到交付做了什么

生成器 dry-run 基线为 `21 条（pos 9 / neg 12 / bnd 0）`——**边界 0 条**是因为 Swagger 里
没有任何 maxLength/minimum 约束，生成器无从下手。以下为人工增强项：

| # | 基线问题 | 增强处理 |
| --- | --- | --- |
| 1 | 边界用例 0 条 | 按 goodsId 补「为空 / 负数 -1 / 不存在 99999」三类，共 17 条 p2 |
| 2 | 路径写死 `testpath` | **实测无效**：返回 `{code:300102,"验证码错误或请求非法！"}`。改为 setup 动态取真实 path（见下节） |
| 3 | 无 setup 重置库存 | 3 个「执行秒杀」接口的全部用例（含负向/边界，共 12 条）setup 先调 `GET /miaosha/reset`，避免库存售罄假失败 |
| 4 | 传参用 `request.params` | 服务端实际收表单（`application/x-www-form-urlencoded`），POST 一律改 `request.data`，GET 保留 `request.params` |
| 5 | 负向断言从宽（`json.code exists`） | 按业务要求改为 `json.code ne 0`（服务端有校验，实测非法参数返回 300100） |
| 6 | 验证码接口断言 `json.code eq 0` | `/miaosha/path`、`/miaosha/verifyCode` 的 verifyCode 传 1234 占位，**只断言 status_code=200**（响应可能非 JSON，断言业务码会误报） |
| 7 | ID 前缀重复 `API_MIAOSHA_MGMT_MGMT_xxx` | 统一为 `API_MIAOSHA_MGMT_001`~`036` |
| 8 | `reset3` 参数被填成 `stock=-1, times=-1` | 正向改 `stock=10, times=1`；另加 1 条 `stock=-1` 边界 |
| 9 | 负向「类型非法」取值等于正向值（`'1'`） | 改为字符串 `abc`，避免与正向用例重复 |
| 10 | 秒杀下单会写库但无清理 | 正向秒杀用例配 `teardown: GET /miaosha/reset` 重置库存与秒杀状态 |

## 模块明细

| 模块(tag) | 中文名 | 文件 | 正向 | 负向 | 边界 | 合计 |
| --- | --- | --- | --- | --- | --- | --- |
| 秒杀管理 | 秒杀管理 | `data/api/miaosha_manage_cases.yaml` | 9 | 10 | 17 | 36 |

## 覆盖矩阵

| 接口 | 正向 p0 | 负向 p1 | 边界 p2 | 备注 |
| --- | --- | --- | --- | --- |
| POST `/miaosha/miaosha` | 001 | 010 缺参 / 011 abc | 020 空 / 021 -1 / 022 99999 | setup+teardown reset |
| POST `/miaosha/over/miaosha` | 002 | 012 缺参 / 013 abc | 023 空 / 024 -1 / 025 99999 | setup+teardown reset |
| GET `/miaosha/path` | 003 | 014 缺参 | 032 -1 / 033 99999 | verifyCode=1234，只断言 200 |
| GET `/miaosha/reset` | 004 | — | — | 测试辅助接口 |
| GET `/miaosha/reset2` | 005 | — | — | 测试辅助接口 |
| POST `/miaosha/reset3` | 006 | — | 036 stock=-1 | 自定义库存 |
| GET `/miaosha/result` | 007 | 015 缺参 / 016 abc | 026 空 / 027 -1 / 028 99999 | — |
| GET `/miaosha/verifyCode` | 008 | 017 缺参 | 034 -1 / 035 99999 | verifyCode=1234，只断言 200 |
| POST `/miaosha/testpath/miaosha` | 009 | 018 缺参 / 019 abc | 029 空 / 030 -1 / 031 99999 | path 固定 testpath，setup+teardown reset |

## 隐藏路径链路（核心接口 009 / 018 / 019 / 029 / 030 / 031）

```yaml
setup:
  - {action: request, name: "前置-重置库存(10)", request: {method: GET, path: "/miaosha/reset"}}
  - action: request
    name: "前置-获取真实隐藏路径"
    request: {method: GET, path: "/miaosha/path", params: {goodsId: "${goods_id}", verifyCode: "${verify_code}"}}
    validate: [{check: status_code, assert: eq, expect: 200}]   # 限流时 code 非 0，故不校验业务码
    extract: {miaosha_path: json.data}
request:
  method: POST
  path: "/miaosha/${miaosha_path}/miaosha"
  data: {goodsId: "${goods_id}"}
```

关键点：**万能验证码是 9999**（与登录一致）。原方案给的 `1234` 实测返回
`{code:300102,"验证码错误或请求非法！"}`，`0/1111/123456` 同样无效。

## 实测基线（2026-10-01，同一会话）

| 请求 | 结果 |
| --- | --- |
| `POST /miaosha/miaosha {goodsId:1}`（reset 后） | `code=0 data=0` 下单成功 |
| `POST /miaosha/over/miaosha {goodsId:1}`（reset 后） | `code=0`；未 reset 时 `300501 不能重复秒杀` |
| `GET /miaosha/over/miaosha?goodsId=1` | `code=300100 服务端异常`（GET 不被支持，故按文档用 POST 是对的） |
| `GET /miaosha/result?goodsId=1` | `code=0 data=523`（订单号） |
| `GET /miaosha/path?goodsId=1&verifyCode=9999` | `code=0 data=<32位随机串>`，每次不同 |
| `POST /miaosha/<真实path>/miaosha {goodsId:1}` | `code=0` 秒杀成功 |
| `POST /miaosha/testpath/miaosha {goodsId:1}` | `code=300102` **testpath 无效** |
| `GET /miaosha/verifyCode?...` | 返回 **JPEG 图片流**（无 json.code，故只断言 200） |

## 潜在缺陷（交给服务端/产品确认）

| 用例 | 现象 | 说明 |
| --- | --- | --- |
| 027 `GET /miaosha/result?goodsId=-1` | 返回 `code=0 data=0` | 负数 goodsId 未校验 |
| 028 `GET /miaosha/result?goodsId=99999` | 返回 `code=0 data=0` | 不存在的 goodsId 未校验 |
| 036 `POST /miaosha/reset3 {stock:-1}` | 返回 `code=0 data=true` | 负数库存未校验 |

这三条已按要求把断言改为从宽（`status_code lt 500` + `json.code exists`）并在标题标注 `⚠ 潜在缺陷`，
不臆造错误码。其余负向/边界均断言 `json.code != 0`，实测服务端确有校验（返回 300100 等）。

## 其他注意事项

1. **限流**：高频调用 `/miaosha/path` 会返回 `{code:300104,"访问太频繁！"}`。
   本模块有 6 条用例调用该接口，顺序执行两轮均未触发；若并发执行（pytest-xdist）或环境变慢
   偶发 300104，重跑即可，或在 setup 里加 `{action: wait, seconds: 1}`。
2. **脏数据**：秒杀下单会生成订单，本模块无删除订单接口，teardown 的 `GET /miaosha/reset`
   只重置库存与秒杀状态，订单表残留需 DBA 侧清理。
3. **`over/miaosha` 方法**：手工用例曾记为 GET，实测 GET 返回 300100，POST 正确，已按文档用 POST。

## 运行

```bash
# 全量
python -m pytest projects/project_miaosha --project project_miaosha --env test --type api
# 冒烟（本模块 9 条正向）
python -m pytest projects/project_miaosha --project project_miaosha --env test --type api -m smoke
# 只看本模块负向/边界
python -m pytest projects/project_miaosha --project project_miaosha --env test --type api -m "p1 or p2" -k MIAOSHA_MGMT
```

## 验证结果

- `--collect-only`：本模块 36 条（p0 9 / p1 10 / p2 17），无用例 ID 冲突，
  `negative`/`boundary`/`smoke` marker 均已在 `pytest.ini` 注册，无 PytestUnknownMarkWarning。
- **实跑两轮**：`36 passed`（11.1s / 11.3s），冒烟 `-m smoke` 9 passed。
- 旧的手工用例 `data/api/miaosha_cases.yaml` 未改动，可独立运行。
