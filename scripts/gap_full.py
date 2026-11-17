#!/usr/bin/env python3
"""生成全覆盖分析表：注册/推送/缺失 + 响应形状 + wire 类字段注释。"""
from __future__ import annotations

import json
import os
import re
import sys

REPO = r"f:\rf4_server\rf4_server_simulator"
GS = os.path.join(REPO, "internal", "gameserver")
OUT = r"f:\rea\artifacts\gap_full_analysis.json"


def load(name, sub=None):
    with open(os.path.join(GS, "assets", name), encoding="utf-8") as fh:
        d = json.load(fh)
    return d[sub] if sub else d


def scan_go():
    reg, fam, push, pushvar = set(), set(), set(), {}
    for root, _dirs, files in os.walk(os.path.join(REPO, "internal")):
        for fn in files:
            if not fn.endswith(".go") or fn.endswith("_test.go"):
                continue
            path = os.path.join(root, fn)
            t = open(path, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r"\bd\.Register\(\s*(\d+)\s*,\s*(\d+)\s*,", t):
                reg.add((int(m.group(1)), int(m.group(2))))
            for m in re.finditer(r"\bd\.RegisterFamily\(\s*(\d+)\s*,", t):
                fam.add(int(m.group(1)))
            for m in re.finditer(r"\.Push\(\s*(\d+)\s*,\s*(\d+)\s*,", t):
                push.add((int(m.group(1)), int(m.group(2))))
            for m in re.finditer(r"\.Push\(\s*(\d+)\s*,\s*uint8\(", t):
                pushvar.setdefault(int(m.group(1)), set()).add(os.path.basename(path))
            # 包装函数名 Push2_1 / Push14_15 等
            for m in re.finditer(r"func \(s \*Session\) Push(\d+)_(\d+)", t):
                push.add((int(m.group(1)), int(m.group(2))))
    return reg, fam, push, pushvar


def main():
    contract = load("command_contract.json")["by_key"]
    caps = load("command_responses.json")
    kinds = load("fallback_kinds.json")
    argcode = load("argcode_table.json")["by_cmd"]
    wire = json.load(open(os.path.join(REPO, "internal", "wiregen", "testdata", "wire_spec.json"),
                          encoding="utf-8"))
    # wire_spec: 可能是 {classes:[...]} 或 {name: {...}}
    wire_by = {}
    if isinstance(wire, dict):
        items = wire.get("classes") or wire.get("types") or wire
        if isinstance(items, list):
            for c in items:
                wire_by[c.get("name") or c.get("class")] = c
        elif isinstance(items, dict):
            wire_by = items
    reg, fam, push, pushvar = scan_go()

    rows = []
    for key, meta in contract.items():
        a_s, b_s = key.split("/")
        a, b = int(a_s), int(b_s)
        if (a, b) in reg:
            status = "registered"
        elif a in fam:
            status = "family"
        elif (a, b) in push:
            status = "push-emitted"
        elif a in pushvar and b in (27, 28, 29, 30, 31):
            status = "push-probe(var)"
        elif meta.get("names") and str(meta["names"][0]).startswith("push:"):
            status = "push-not-emitted"
        else:
            status = "MISSING"
        resp = meta.get("resp") or {}
        cap = caps.get(key) or {}
        shapes = []
        if resp.get("type_ids"):
            for tid in resp["type_ids"]:
                shapes.append(f"tid={tid}")
        for cls in resp.get("classes") or []:
            shapes.append(f"cls={cls}")
        rows.append({
            "cmd": key, "status": status,
            "name": (meta.get("names") or [""])[0], "method": meta.get("method", ""),
            "resp_kind": resp.get("kind", ""), "resp_shape": " ".join(shapes),
            "fallback": kinds.get(key, {}), "argcode": argcode.get(key, ""),
            "capture": {k: cap.get(k) for k in ("wire", "tid", "array", "resp") if cap.get(k) is not None},
            "wire_class": {},
        })

    # 补 wire 类字段注释
    for r in rows:
        classes = []
        for tok in r["resp_shape"].split():
            if tok.startswith("cls="):
                classes.append(tok[4:])
        if r["capture"].get("wire"):
            classes.append(r["capture"]["wire"])
        for cls in classes:
            info = wire_by.get(cls)
            if not isinstance(info, dict):
                continue
            fields = info.get("fields") or info.get("members") or []
            desc = info.get("comment") or info.get("desc") or ""
            slim = []
            for f in fields if isinstance(fields, list) else []:
                if isinstance(f, dict):
                    slim.append(f.get("comment") or f.get("name") or f.get("cs") or "")
                else:
                    slim.append(str(f))
            r["wire_class"][cls] = {"desc": desc, "fields": slim}

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"repo": REPO, "count": len(rows), "rows": rows}, fh,
                  ensure_ascii=False, indent=2)

    from collections import Counter
    print("total", len(rows), dict(Counter(r["status"] for r in rows)))
    print("missing request commands:")
    for r in rows:
        if r["status"] == "MISSING":
            print(f"  {r['cmd']}\t{r['name']}\t{r['method']}\t{r['resp_shape']}\tfb={r['fallback']}\targ={r['argcode']}")
    print("push not emitted:")
    for r in rows:
        if r["status"] == "push-not-emitted":
            print(f"  {r['cmd']}\t{r['name']}\t{r['resp_shape']}")
    print("->", OUT)


if __name__ == "__main__":
    sys.exit(main())
