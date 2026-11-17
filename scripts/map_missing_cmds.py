#!/usr/bin/env python3
"""把缺失命令映射到客户端反编译清单（类/方法/签名/DTO 字段）。

输入:
  f:\\rea\\artifacts\\il2cpp_dump\\Assembly-CSharp.cs
  f:\\rf4_server\\rf4_server_simulator\\internal\\gameserver\\assets\\command_contract.json
  f:\\rea\\artifacts\\gap_full_analysis.json
输出:
  f:\\rea\\artifacts\\missing_commands_map.json
  f:\\rea\\artifacts\\missing_commands_map.md
"""
from __future__ import annotations

import json
import os
import re

CS = r"f:\rea\artifacts\il2cpp_dump\Assembly-CSharp.cs"
GS = r"f:\rf4_server\rf4_server_simulator\internal\gameserver\assets"
OUT_J = r"f:\rea\artifacts\missing_commands_map.json"
OUT_M = r"f:\rea\artifacts\missing_commands_map.md"

# 已确认由 world.go 循环注册，不算缺失
COVERED_BY_LOOP = {f"29/{i}" for i in range(1, 6)}


def parse_blocks(path):
    """返回 [(kind, fullname, parent, start_line, lines)]。"""
    blocks = []
    cur = None
    header = re.compile(r"^public (class|struct|enum|interface) ([^\s:]+)(?: : ([^\s{]+))? \{")
    with open(path, encoding="utf-8") as fh:
        for no, line in enumerate(fh, 1):
            if cur is None:
                m = header.match(line.rstrip("\n"))
                if m:
                    cur = [m.group(1), m.group(2), m.group(3) or "", no, []]
            else:
                if line.startswith("}"):
                    blocks.append(cur)
                    cur = None
                else:
                    cur[4].append(line.rstrip("\n"))
    return blocks


def methods_of(block):
    out = []
    for line in block[4]:
        m = re.match(r"\s+public (.+?) (\S+)\((.*?)\) \{ \}", line)
        if m and not m.group(2).startswith("get_") and not m.group(2).startswith("set_"):
            out.append({"ret": m.group(1).strip(), "name": m.group(2),
                        "params": m.group(3).strip()})
    return out


def fields_of(block):
    out = []
    for line in block[4]:
        m = re.match(r"\s+public (.+?) (\S+); // \+0x([0-9A-F]+)", line)
        if m:
            out.append({"type": m.group(1).strip(), "name": m.group(2),
                        "offset": int(m.group(3), 16)})
    return out


def render_type(type_name, by_full):
    """把类型名解析到同名 block，附上字段/基类。"""
    base = re.sub(r"<.*>", "", type_name).replace("[]", "").strip()
    b = by_full.get(base)
    if not b:
        return None
    return {"name": b[1], "parent": b[2], "kind": b[0],
            "fields": fields_of(b)[:40]}


def main():
    with open(CS, encoding="utf-8") as fh:
        blocks = parse_blocks(CS)
    by_full = {}
    for b in blocks:
        by_full[b[1]] = b
    by_method = {}
    for b in blocks:
        for m in methods_of(b):
            by_method.setdefault(m["name"], []).append((b, m))

    contract = json.load(open(os.path.join(GS, "command_contract.json"), encoding="utf-8"))["by_key"]
    gap = json.load(open(r"f:\rea\artifacts\gap_full_analysis.json", encoding="utf-8"))
    wire = json.load(open(r"f:\rf4_server\rf4_server_simulator\internal\wiregen\testdata\wire_spec.json",
                          encoding="utf-8"))
    wclasses = wire["classes"]

    missing = [r for r in gap["rows"] if r["status"] == "MISSING" and r["cmd"] not in COVERED_BY_LOOP]
    result = []
    for row in missing:
        key = row["cmd"]
        meta = contract.get(key, {})
        names = meta.get("names") or []
        route = next((n for n in names if "/" in str(n)), "")
        cand_names = []
        if meta.get("method"):
            cand_names.append(meta["method"])
        for n in names:
            if re.fullmatch(r"[a-z][a-z0-9]{6,}", str(n)) and n not in cand_names:
                cand_names.append(n)
        hits = []
        for cn in cand_names:
            for b, m in by_method.get(cn, []):
                hits.append({
                    "class": b[1], "kind": b[0], "parent": b[2],
                    "method": m["name"], "ret": m["ret"], "params": m["params"],
                    "class_fields": fields_of(b)[:30],
                    "ret_detail": render_type(m["ret"], by_full),
                    "param_types": [render_type(p.strip(), by_full)
                                    for p in split_params(m["params"]) if p.strip()],
                })
        resp = meta.get("resp") or {}
        wire_info = {}
        for cls in resp.get("classes") or []:
            wi = wclasses.get(cls)
            if wi:
                wire_info[cls] = {"type_id": wi.get("type_id"), "ops": wi.get("ops"),
                                  "dto": wi.get("dto"),
                                  "fields": [{"name": f.get("name"), "zh": f.get("zh")}
                                             for f in wi.get("fields") or []]}
        result.append({
            "cmd": key, "route": route or (names[0] if names else ""),
            "names": names, "resp": resp, "fallback": row.get("fallback"),
            "argcode": row.get("argcode"), "capture": row.get("capture"),
            "wire": wire_info, "client_hits": hits,
        })

    with open(OUT_J, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    families = {}
    for r in result:
        families.setdefault(r["cmd"].split("/")[0], []).append(r)
    lines = ["# RF4 缺失命令 ↔ 客户端反编译清单映射", ""]
    for fam in sorted(families, key=int):
        lines.append(f"## {fam} 族")
        for r in families[fam]:
            lines.append(f"### {r['cmd']} `{r['route']}`")
            if r["client_hits"]:
                for h in r["client_hits"]:
                    lines.append(f"- 客户端方法: `{h['class']}.{h['method']}`")
                    lines.append(f"  - 返回: `{h['ret']}`")
                    lines.append(f"  - 参数: `{h['params'] or '(无)'}`")
                    if h["class_fields"]:
                        lines.append("  - 所在类字段: " + ", ".join(
                            f"{f['name']}:{f['type']}" for f in h["class_fields"][:12]))
                    for pt in h["param_types"]:
                        if pt and pt["kind"] in ("class", "struct"):
                            lines.append(f"  - 参数类型 `{pt['name']}`: " + ", ".join(
                                f"{f['name']}:{f['type']}" for f in pt["fields"][:12]))
                    rd = h.get("ret_detail")
                    if rd and rd["kind"] in ("class", "struct"):
                        lines.append(f"  - 返回类型 `{rd['name']}`: " + ", ".join(
                            f"{f['name']}:{f['type']}" for f in rd["fields"][:12]))
            else:
                lines.append("- 客户端方法: 未定位（需按语义继续查）")
            for cls, wi in r["wire"].items():
                lines.append(f"- 响应 wire 类 `{cls}` tid={wi['type_id']}: " + ", ".join(
                    f"{f['name']}({f['zh']})" for f in wi["fields"]))
            lines.append(f"- 兜底: `{json.dumps(r['fallback'], ensure_ascii=False)}`")
            lines.append("")
    with open(OUT_M, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("wrote", OUT_J, OUT_M, "missing", len(result))


def split_params(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur:
        out.append(cur)
    return out


if __name__ == "__main__":
    main()
