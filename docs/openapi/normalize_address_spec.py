"""把 miaosha_api.json 中「收货地址」模块归一化成生成器可识别的形态。

原文档问题（Swagger 2.0 由 SpringFox 自动生成，与真实服务不一致）：
  1. 所有参数都是 in=query，实际服务端收表单（application/x-www-form-urlencoded）
  2. 除 id 外没有任何 required 标记 -> 生成不出「必填缺失」负向用例
  3. 没有任何 maxLength/minimum 约束 -> 生成不出边界用例
  4. 混入 User 对象的无关字段（head/nickname/password/salt/loginCount...）

本脚本只改 /address/* 这 6 个接口，其余 tag 原样保留：
  - POST 接口：参数改写为 in=formData，按业务真实必填项打 required
  - GET /address/detail/{id}：保留 path 参数 id（required）
  - consumes 改为 application/x-www-form-urlencoded
运行后会生成 miaosha_api.address.form.json，供 api-test-gen 使用。
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "miaosha_api.json"
DST = HERE / "miaosha_api.address.form.json"

# 业务真实必填项（文档未标，按接口语义与实测补充）
REQUIRED = {
    "/address/add": {"receiverName", "receiverPhone", "detailAddress"},
    "/address/update": {"id", "receiverName", "receiverPhone", "detailAddress"},
    "/address/delete": {"id"},
    "/address/setDefault": {"id"},
    "/address/detail/{id}": set(),          # path 参数本身就是必填
}
# 保留字段白名单（其余 User 对象字段全部丢弃）
KEEP = {
    "receiverName", "receiverPhone", "province", "city", "district",
    "detailAddress", "zipCode", "isDefault", "id",
}
# 需要出现在正向报文里、但不参与负向遍历的非必填字段（走模块 testdata 注入，这里不标 required）
FORM_FIELDS = {
    "/address/add": ["receiverName", "receiverPhone", "province", "city",
                     "district", "detailAddress", "zipCode", "isDefault"],
    "/address/update": ["id", "receiverName", "receiverPhone", "province", "city",
                        "district", "detailAddress", "zipCode", "isDefault"],
    "/address/delete": ["id"],
    "/address/setDefault": ["id"],
}
TYPE_MAP = {"id": "integer", "isDefault": "integer"}


def main() -> None:
    spec = json.loads(SRC.read_text(encoding="utf-8"))
    out = copy.deepcopy(spec)

    for path, item in (out.get("paths") or {}).items():
        if not path.startswith("/address/"):
            continue
        for method, op in list(item.items()):
            if not isinstance(op, dict):
                continue
            op["consumes"] = ["application/x-www-form-urlencoded"]
            new_params = []
            for p in op.get("parameters") or []:
                name = p.get("name")
                loc = p.get("in")
                if loc == "path":                      # /address/detail/{id}
                    new_params.append({"name": name, "in": "path", "required": True,
                                       "type": TYPE_MAP.get(name, "string"),
                                       "description": p.get("description", "")})
                    continue
                if name in KEEP and name in FORM_FIELDS.get(path, []):
                    new_params.append({
                        "name": name,
                        "in": "formData",
                        "required": name in REQUIRED.get(path, set()),
                        "type": TYPE_MAP.get(name, "string"),
                        "description": p.get("description", ""),
                    })
            # 原文档 id 会重复出现（一次选填 query、一次必填），按 name 去重，保留必填那个
            dedup: dict[str, dict] = {}
            for p in new_params:
                old = dedup.get(p["name"])
                if old is None or (p.get("required") and not old.get("required")):
                    dedup[p["name"]] = p
            op["parameters"] = list(dedup.values())

    DST.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成: {DST}")
    for path in REQUIRED:
        item = out["paths"][path]
        for method, op in item.items():
            if isinstance(op, dict):
                req = [p["name"] for p in op["parameters"] if p.get("required")]
                allf = [f"{p['name']}({p['in']})" for p in op["parameters"]]
                print(f"  {method.upper():6} {path:24} required={req}")
                print(f"         fields={allf}")


if __name__ == "__main__":
    main()
