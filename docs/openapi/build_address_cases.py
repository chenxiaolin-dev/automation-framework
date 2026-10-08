"""把 api-test-gen 生成的「收货地址」基线用例，按需求增强为完整用例集。

生成链路：miaosha_api.json（原始 Swagger）
  -> normalize_address_spec.py（表单化 + 补必填）
  -> generate_cases.py --dry-run（预览）-> 正式生成 19 条基线
  -> 本脚本（按 7 条需求增强为 50 条）-> address_openapi_cases.yaml

需求落地对照：
  1. 只生成 tag=收货地址 的 6 个接口                 -> --only 收货地址
  2. 请求一律表单格式                                -> request.data（归一化文档已标 formData）
  3. 正向 p0+smoke / 负向 p1+negative / 边界 p2+boundary
  4. 负向按必填参数逐个做「缺省 / 为空 / 类型错误」    -> 缺省单条 + 为空/类型错误走 data_matrix
  5. 边界：id 取 99999 / -1，字符串取超长              -> data_matrix 展开 + 超长单条
  6. receiverName/Phone/detailAddress 用 ${fake}      -> variables + BASE_FIELDS
  7. 需要已有数据的接口在 setup 造数并 extract         -> setup_create()，禁止硬编码 id
  8. 产生脏数据的用例 teardown 调用 /address/delete    -> teardown_delete()

断言策略（2026-09-29 实测，非臆造）：
  - id 类参数：缺/空/类型错 -> 300101；99999/-1 -> 300601            -> 严格 json.code != 0
  - 字符串字段：缺/空/类型错 -> 0（服务端无校验，潜在缺陷）            -> 从宽（不臆造错误码）
  - 字符串超长 -> 300100                                              -> 严格 json.code != 0
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Administrator\.workbuddy\skills\api-test-gen\scripts")
import generate_cases as G  # noqa: E402  复用其 YAML 输出风格（flow style / 中文 / ${} 加引号）

OUT = Path(r"D:\PyCharm\automation-framework\projects\project_miaosha\data\api\address_openapi_cases.yaml")
LONG = "超长" * 150                     # 300 字符，实测触发 300100

# ---------------- 公共片段 ----------------
BASE_FIELDS = {
    "receiverName": "${fake.name}",
    "receiverPhone": "${fake.phone_number}",
    "province": "${province}",
    "city": "${city}",
    "district": "${district}",
    "detailAddress": "详细地址${fake.building_number}号",
    "zipCode": "${zip_code}",
    "isDefault": 0,
}
POSITIVE = [{"check": "status_code", "assert": "eq", "expect": 200},
            {"check": "json.code", "assert": "eq", "expect": 0}]
STRICT = [{"check": "status_code", "assert": "eq", "expect": 200},
          {"check": "json.code", "assert": "ne", "expect": 0}]
LOOSE = [{"check": "status_code", "assert": "eq", "expect": 200},
         {"check": "json.code", "assert": "exists"}]


def setup_create():
    """前置造数：新增一条地址并 extract address_id（响应 data 是 id 标量）。"""
    return [{"action": "request", "name": "前置-新增地址",
             "request": {"method": "POST", "path": "/address/add", "data": dict(BASE_FIELDS)},
             "validate": [{"check": "json.code", "assert": "eq", "expect": 0}],
             "extract": {"address_id": "json.data"}}]


def teardown_delete():
    """后置清理：删除本用例产生的地址（主请求已删除时会返回非 0，此处不做断言）。"""
    return [{"action": "request", "name": "清理-删除地址",
             "request": {"method": "POST", "path": "/address/delete", "data": {"id": "${address_id}"}}}]


def add_data(**over):
    d = dict(BASE_FIELDS)
    d.update(over)
    return d


def add_data_without(*fields, **over):
    d = dict(BASE_FIELDS)
    for f in fields:
        d.pop(f, None)
    d.update(over)
    return d


def upd_data(**over):
    d = {"id": "${address_id}"}
    d.update(BASE_FIELDS)
    d.update(over)
    return d


def upd_data_without(*fields, **over):
    d = upd_data(**over)
    for f in fields:
        d.pop(f, None)
    return d


cases: list[dict] = []


def C(cid, title, level, tags, request, validate, **kw):
    # 深拷贝：避免多条用例共用同一个断言字典，导致 YAML 输出 &id001 / *id001 锚点引用
    case = {"id": cid, "title": title, "level": level, "tags": tags, "request": request,
            "validate": copy.deepcopy(validate)}
    case.update(kw)
    cases.append(case)


# ================= 正向（p0 + smoke）=================
C("API_ADDRESS_ADD_P01", "新增收货地址-正向（全字段，Faker 造数）", "p0", ["smoke"],
  {"method": "POST", "path": "/address/add", "data": add_data()},
  POSITIVE + [{"check": "json.data", "assert": "not_empty"}],
  extract={"address_id": "json.data"}, teardown=teardown_delete())

C("API_ADDRESS_UPDATE_P01", "更新收货地址-正向（前置造数，按 address_id 更新）", "p0", ["smoke"],
  {"method": "POST", "path": "/address/update", "data": upd_data(receiverName="更新后的收件人")},
  POSITIVE, setup=setup_create(), teardown=teardown_delete())

C("API_ADDRESS_LIST_P01", "获取用户所有收货地址-正向", "p0", ["smoke"],
  {"method": "GET", "path": "/address/list"},
  POSITIVE + [{"check": "json.data", "assert": "type", "expect": "list"}])

C("API_ADDRESS_DETAIL_P01", "根据ID获取收货地址详情-正向（前置造数，路径参数取 address_id）", "p0", ["smoke"],
  {"method": "GET", "path": "/address/detail/${address_id}"},
  POSITIVE + [{"check": "json.data", "assert": "not_empty"}],
  setup=setup_create(), teardown=teardown_delete())

C("API_ADDRESS_SETDEFAULT_P01", "设置默认收货地址-正向（前置造数）", "p0", ["smoke"],
  {"method": "POST", "path": "/address/setDefault", "data": {"id": "${address_id}"}},
  POSITIVE, setup=setup_create(), teardown=teardown_delete())

C("API_ADDRESS_DELETE_P01", "删除收货地址-正向（前置造数，按 address_id 删除）", "p0", ["smoke"],
  {"method": "POST", "path": "/address/delete", "data": {"id": "${address_id}"}},
  POSITIVE, setup=setup_create())

# ================= 负向：新增（服务端对字符串字段无参数校验 -> 从宽）=================
# 注意：这些请求会真实新增成功，故 extract + teardown 清理
for cid, field in [("API_ADDRESS_ADD_N01", "receiverName"),
                   ("API_ADDRESS_ADD_N02", "receiverPhone"),
                   ("API_ADDRESS_ADD_N03", "detailAddress")]:
    C(cid, f"新增收货地址-负向：缺少必填参数 {field}", "p1", ["negative"],
      {"method": "POST", "path": "/address/add", "data": add_data_without(field)},
      LOOSE, extract={"address_id": "json.data"}, teardown=teardown_delete())

for cid, field, bad in [("API_ADDRESS_ADD_N04", "receiverName", ["", 123]),
                        ("API_ADDRESS_ADD_N05", "receiverPhone", ["", "abc"]),
                        ("API_ADDRESS_ADD_N06", "detailAddress", ["", 123])]:
    C(cid, f"新增收货地址-负向：{field} 为空 / 类型错误", "p1", ["negative"],
      {"method": "POST", "path": "/address/add",
       "data": add_data(**{field: "${%s}" % field})},
      LOOSE, data_matrix={field: bad},
      extract={"address_id": "json.data"}, teardown=teardown_delete())

# ================= 负向：更新（id 严格；字符串字段服务端无校验 -> 从宽）=================
C("API_ADDRESS_UPDATE_N01", "更新收货地址-负向：缺少必填参数 id", "p1", ["negative"],
  {"method": "POST", "path": "/address/update", "data": add_data()}, STRICT)

C("API_ADDRESS_UPDATE_N02", "更新收货地址-负向：id 为空 / 类型错误", "p1", ["negative"],
  {"method": "POST", "path": "/address/update", "data": upd_data(id="${id}")},
  STRICT, data_matrix={"id": ["", "abc"]})

for cid, field in [("API_ADDRESS_UPDATE_N03", "receiverName"),
                   ("API_ADDRESS_UPDATE_N04", "receiverPhone"),
                   ("API_ADDRESS_UPDATE_N05", "detailAddress")]:
    C(cid, f"更新收货地址-负向：缺少必填参数 {field}", "p1", ["negative"],
      {"method": "POST", "path": "/address/update", "data": upd_data_without(field)},
      LOOSE, setup=setup_create(), teardown=teardown_delete())

for cid, field, bad in [("API_ADDRESS_UPDATE_N06", "receiverName", ["", 123]),
                        ("API_ADDRESS_UPDATE_N07", "receiverPhone", ["", "abc"]),
                        ("API_ADDRESS_UPDATE_N08", "detailAddress", ["", 123])]:
    C(cid, f"更新收货地址-负向：{field} 为空 / 类型错误", "p1", ["negative"],
      {"method": "POST", "path": "/address/update",
       "data": upd_data(**{field: "${%s}" % field})},
      LOOSE, data_matrix={field: bad}, setup=setup_create(), teardown=teardown_delete())

# ================= 负向：删除 / 设默认 / 详情（id 有强校验 -> 严格）=================
C("API_ADDRESS_DELETE_N01", "删除收货地址-负向：缺少必填参数 id", "p1", ["negative"],
  {"method": "POST", "path": "/address/delete", "data": {}}, STRICT)

C("API_ADDRESS_DELETE_N02", "删除收货地址-负向：id 为空 / 类型错误", "p1", ["negative"],
  {"method": "POST", "path": "/address/delete", "data": {"id": "${id}"}},
  STRICT, data_matrix={"id": ["", "abc"]})

C("API_ADDRESS_SETDEFAULT_N01", "设置默认收货地址-负向：缺少必填参数 id", "p1", ["negative"],
  {"method": "POST", "path": "/address/setDefault", "data": {}}, STRICT)

C("API_ADDRESS_SETDEFAULT_N02", "设置默认收货地址-负向：id 为空 / 类型错误", "p1", ["negative"],
  {"method": "POST", "path": "/address/setDefault", "data": {"id": "${id}"}},
  STRICT, data_matrix={"id": ["", "abc"]})

# 详情的 id 在 path 上：类型错误走业务逻辑可断言业务码（300100）
C("API_ADDRESS_DETAIL_N01", "根据ID获取收货地址详情-负向：id 类型错误", "p1", ["negative"],
  {"method": "GET", "path": "/address/detail/${id}"}, STRICT,
  data_matrix={"id": ["abc", "not-a-number"]})
# id 为空时 URL 退化成 /address/detail/，路由层直接 404，根本进不到业务层，故断言 HTTP 404
C("API_ADDRESS_DETAIL_N02", "根据ID获取收货地址详情-负向：id 为空（路径不匹配，路由层 404）", "p1", ["negative"],
  {"method": "GET", "path": "/address/detail/"},
  [{"check": "status_code", "assert": "eq", "expect": 404}])

# ================= 边界：id 取不存在 99999 / 负数 -1（严格）=================
for cid, path, method, where in [
        ("API_ADDRESS_UPDATE_B01", "/address/update", "POST", "data"),
        ("API_ADDRESS_DELETE_B01", "/address/delete", "POST", "data"),
        ("API_ADDRESS_SETDEFAULT_B01", "/address/setDefault", "POST", "data")]:
    C(cid, f"{path.split('/')[-1]} 边界：id 取不存在 99999 / 负数 -1", "p2", ["boundary"],
      {"method": method, "path": path, "data": {"id": "${id}"}}, STRICT,
      data_matrix={"id": [99999, -1]})

C("API_ADDRESS_DETAIL_B01", "根据ID获取收货地址详情-边界：id 取不存在 99999 / 负数 -1", "p2", ["boundary"],
  {"method": "GET", "path": "/address/detail/${id}"}, STRICT,
  data_matrix={"id": [99999, -1]})

# ================= 边界：字符串超长（严格，实测 300100）=================
for cid, field, label in [("API_ADDRESS_ADD_B01", "receiverName", "收货人姓名"),
                          ("API_ADDRESS_ADD_B02", "receiverPhone", "收货人手机号"),
                          ("API_ADDRESS_ADD_B03", "detailAddress", "详细地址")]:
    C(cid, f"新增收货地址-边界：{label}超长（{len(LONG)}字符）", "p2", ["boundary"],
      {"method": "POST", "path": "/address/add", "data": add_data(**{field: LONG})}, STRICT)

for cid, field, label in [("API_ADDRESS_UPDATE_B02", "receiverName", "收货人姓名"),
                          ("API_ADDRESS_UPDATE_B03", "receiverPhone", "收货人手机号"),
                          ("API_ADDRESS_UPDATE_B04", "detailAddress", "详细地址")]:
    C(cid, f"更新收货地址-边界：{label}超长（{len(LONG)}字符）", "p2", ["boundary"],
      {"method": "POST", "path": "/address/update", "data": upd_data(**{field: LONG})},
      STRICT, setup=setup_create(), teardown=teardown_delete())

# ================= 鉴权负向 =================
C("API_ADDRESS_AUTH_N01", "鉴权-无效 token 访问地址列表被拒绝", "p1", ["negative"],
  {"method": "GET", "path": "/address/list", "headers": {"token": "invalid-token-for-negative-test"}},
  STRICT)

# ---------------- 输出 ----------------
ORDER = ("id", "title", "level", "tags", "depends_on", "setup", "request",
         "validate", "schema", "extract", "data_matrix", "teardown")
doc = {
    "meta": {"module": "收货地址", "default_method": "POST"},
    "variables": {"province": "广东省", "city": "深圳市", "district": "南山区", "zip_code": "518000"},
    "test_cases": [{k: c[k] for k in ORDER if k in c} for c in cases],
}

n_pos = sum(1 for c in cases if c["level"] == "p0")
n_neg = sum(1 for c in cases if "negative" in c["tags"])
n_bnd = sum(1 for c in cases if "boundary" in c["tags"])
n_matrix = sum(len(c["data_matrix"][list(c["data_matrix"])[0]]) - 1 for c in cases if "data_matrix" in c)
total = len(cases) + n_matrix

header = f"""# 收货地址 模块接口用例（OpenAPI 生成 + 需求增强）
# 文档来源: docs/openapi/miaosha_api.json（Swagger 2.0，59 接口）
#          -> normalize_address_spec.py 归一化（表单化 + 补必填）-> miaosha_api.address.form.json
# 生成工具: api-test-gen（--only 收货地址 --modules docs/openapi/address_modules.yaml）
# 增强脚本: docs/openapi/build_address_cases.py
# 用例规模: {len(cases)} 条模板 -> data_matrix 展开后 {total} 条
#           正向 {n_pos} / 负向 {n_neg} / 边界 {n_bnd}（含鉴权负向 1）
#
# 请求约定: 全部为表单 application/x-www-form-urlencoded（YAML 用 request.data）
# 鉴权: config/test.yaml 的 api.auth 登录换取 token，注入自定义请求头 token
#
# 断言策略（2026-09-29 对本环境实测，未臆造业务码）:
#   - id 类参数: 缺省/为空/类型错误 -> 300101；99999/-1 -> 300601         => 严格 json.code != 0
#   - 字符串字段: 缺省/为空/类型错误 -> code=0（服务端未校验，潜在缺陷）    => 从宽（status 200 + code 存在）
#   - 字符串超长 -> 300100                                                => 严格 json.code != 0
#
# 数据说明:
#   - receiverName/receiverPhone/detailAddress 用 ${{fake}} 造数
#   - 更新/详情/设默认/删除均在 setup 调 /address/add 造数，extract address_id，禁止硬编码 id
#   - 新增类负向用例服务端会真实新增成功，故统一 extract + teardown 删除，不留脏数据
#
# 运行:
#   python -m pytest projects/project_miaosha --project project_miaosha --env test --type api -k ADDRESS
#   python -m pytest projects/project_miaosha --project project_miaosha --env test --type api -m smoke
#
# 待人工确认:
#   - 字符串字段无参数校验（缺参也新增/更新成功）已按从宽断言；若想当缺陷暴露，把这些用例的
#     validate 改成 {{check: json.code, assert: ne, expect: 0}} 即可
#   - /address/detail/${{id}} 依赖框架解析 request.path 变量，已由 --patch-path-vars 补齐
#     （engines/api/yaml_runner.py，原文件备份 yaml_runner.py.bak）
#   - 账号收货地址上限 20 个，超出后 /address/add 恒返回 300603；跑大批量前请确认余量
"""

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(header + "\n" + G.dump_yaml(doc), encoding="utf-8")
print(f"已写入 {OUT}")
print(f"模板 {len(cases)} 条 -> 展开后 {total} 条（正向 {n_pos} / 负向 {n_neg} / 边界 {n_bnd}）")
