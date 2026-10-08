"""复用 api-test-gen 的 plan_module 预览「收货地址」用例清单（不写任何项目文件）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\Administrator\.workbuddy\skills\api-test-gen\scripts")
import yaml  # noqa: E402
import generate_cases as G  # noqa: E402

SPEC = Path(r"D:\PyCharm\automation-framework\docs\openapi\miaosha_api.address.form.json")
MODCFG = Path(r"D:\PyCharm\automation-framework\docs\openapi\address_modules.yaml")

spec = G.deref(*G.load_document(str(SPEC))[:1]) if False else G.load_document(str(SPEC))[0]
spec = G.deref(spec, spec)
ops = [o for o in G.collect_operations(spec) if not o["deprecated"]]
mod_cfg = (yaml.safe_load(MODCFG.read_text(encoding="utf-8")) or {}).get("modules") or {}

grouped: dict[str, list] = {}
for op in ops:
    grouped.setdefault(G.module_key(op), []).append(op)

for tag, tag_ops in grouped.items():
    if tag != "收货地址":
        continue
    cfg = mod_cfg.get(tag) or {}
    slug = cfg.get("slug") or G.default_slug(tag, tag_ops)
    mod = {"tag": tag, "slug": slug, "cn_name": cfg.get("cn_name") or tag,
           "id_prefix": cfg.get("id_prefix") or G.default_id_prefix(tag, tag_ops, slug),
           "levels": {"positive": "p0", "negative": "p1", "boundary": "p2"},
           "default_method": max({o["method"] for o in tag_ops},
                                 key=lambda m: sum(1 for o in tag_ops if o["method"] == m)),
           "smoke_positive": cfg.get("smoke_positive", True)}
    mod["levels"].update(cfg.get("levels") or {})
    ctx = {"spec": spec, "variables": {}, "bound_vars": {},
           "testdata": dict(cfg.get("testdata") or {}),
           "biz_code": 0, "auth_header": "token", "max_negative": 6,
           "project": "project_miaosha", "only": "收货地址"}
    items, notes, stats = G.plan_module(tag_ops, mod, ctx)
    items = G._renumber(items, mod, ctx)
    G.fixup_dependencies(items, ctx)

    print(f"模块: {mod['cn_name']}（tag={tag}） 文件=data/api/{slug}_cases.yaml  {stats}")
    print("-" * 100)
    for it in items:
        c = it["case"]
        req = c.get("request") or {}
        where = "data" if "data" in req else ("params" if "params" in req else "path")
        body = req.get("data") or req.get("params") or ""
        print(f"{c['id']:34} {c['level']} {str(c.get('tags') or ''):12} {it['kind']:8} "
              f"{req.get('method','')} {req.get('path','')}")
        print(f"{'':34}   title={c['title']}")
        if body:
            print(f"{'':34}   {where}={body}")
        for v in c.get("validate") or []:
            print(f"{'':34}   - {v['check']} {v['assert']} {v.get('expect','')}")
        if c.get("extract"):
            print(f"{'':34}   extract={c['extract']}")
        if c.get("depends_on"):
            print(f"{'':34}   depends_on={c['depends_on']}")
    print()
    print("variables =", ctx.get("variables"))
    print("notes =", notes)
