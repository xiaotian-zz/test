#!/usr/bin/env python3
"""按命令族汇总契约覆盖度。"""
from __future__ import annotations

import json
from collections import defaultdict

REPO = r"f:\rf4_server\rf4_server_simulator"
GAP = r"f:\rea\artifacts\gap_commands.json"


def main() -> None:
    contract = json.load(open(REPO + r"\internal\gameserver\assets\command_contract.json", encoding="utf-8"))["by_key"]
    gap = json.load(open(GAP, encoding="utf-8"))

    missing: set[str] = set()
    for main_key, items in gap["missing_by_main"].items():
        for e in items:
            missing.add(f"{main_key}/{e['sub']}")

    total: dict[str, int] = defaultdict(int)
    covered: dict[str, int] = defaultdict(int)
    names: dict[str, dict[str, str]] = defaultdict(dict)
    for key, meta in contract.items():
        nm = (meta.get("names") or [""])[0]
        if nm.startswith("push:"):
            continue
        main_key = key.split("/")[0]
        total[main_key] += 1
        names[main_key][key] = nm
        if key not in missing:
            covered[main_key] += 1

    for main_key in sorted(total, key=int):
        miss = sorted((k for k in missing if k.split("/")[0] == main_key), key=lambda s: int(s.split("/")[1]))
        detail = ", ".join(f"{k.split('/')[1]}:{names[main_key].get(k, '?')}" for k in miss)
        print(f"[{main_key:>3}] {covered[main_key]:>2}/{total[main_key]:<2} missing({len(miss)}): {detail}")


if __name__ == "__main__":
    main()
