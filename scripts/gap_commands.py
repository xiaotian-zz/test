#!/usr/bin/env python3
"""对比客户端命令契约与服务端已注册处理器，输出缺失命令清单。

用法: py -3.12 gap_commands.py [repo_root] [-o out.json]
"""
from __future__ import annotations

import json
import os
import re
import sys

RE_REG = re.compile(r"\bd\.Register\(\s*(\d+)\s*,\s*(\d+)\s*,")
RE_FAMILY = re.compile(r"\bd\.RegisterFamily\(\s*(\d+)\s*,")


def scan(repo: str) -> tuple[set[tuple[int, int]], set[int]]:
    regs: set[tuple[int, int]] = set()
    fams: set[int] = set()
    for root, _dirs, files in os.walk(os.path.join(repo, "internal")):
        for fn in files:
            if not fn.endswith(".go") or fn.endswith("_test.go"):
                continue
            path = os.path.join(root, fn)
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for m in RE_REG.finditer(text):
                regs.add((int(m.group(1)), int(m.group(2))))
            for m in RE_FAMILY.finditer(text):
                fams.add(int(m.group(1)))
    return regs, fams


def main() -> int:
    repo = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else r"f:\rf4_server\rf4_server_simulator"
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "artifacts", "gap_commands.json")
    if "-o" in sys.argv:
        out = sys.argv[sys.argv.index("-o") + 1]

    contract_path = os.path.join(repo, "internal", "gameserver", "assets", "command_contract.json")
    with open(contract_path, "r", encoding="utf-8") as fh:
        contract = json.load(fh)["by_key"]

    regs, fams = scan(repo)

    known: list[tuple[int, int, str, str]] = []
    for key, meta in contract.items():
        main_s, _, sub_s = key.partition("/")
        try:
            main_i, sub_i = int(main_s), int(sub_s)
        except ValueError:
            continue
        known.append((main_i, sub_i, (meta.get("names") or [""])[0], meta.get("method") or ""))

    missing = sorted(
        [(m, s, n, meth) for (m, s, n, meth) in known if (m, s) not in regs and m not in fams]
    )
    covered = sorted(
        [(m, s, n, meth) for (m, s, n, meth) in known if (m, s) in regs or m in fams]
    )

    by_main: dict[int, list] = {}
    for m, s, n, meth in missing:
        by_main.setdefault(m, []).append({"sub": s, "name": n, "method": meth})

    result = {
        "repo": repo,
        "contract_commands": len(known),
        "registered_pairs": len(regs),
        "registered_families": sorted(fams),
        "covered": len(covered),
        "missing": len(missing),
        "missing_by_main": {str(k): v for k, v in sorted(by_main.items())},
        "missing_list": [f"{m}/{s} {n}" for m, s, n, _ in missing],
    }
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    print(f"contract commands: {len(known)}  registered: {len(regs)}  families: {sorted(fams)}")
    print(f"covered: {len(covered)}  missing: {len(missing)}  -> {out}")
    for k, v in sorted(by_main.items()):
        print(f"[{k}] missing {len(v)}: " + ", ".join(f"{e['sub']}:{e['name']}" for e in v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
