#!/usr/bin/env python3
"""检查 Unity 场景文件中圣诞树对象及其层级/缩放。

用法:
  python inspect_tree.py <场景文件> <名称关键词>
"""
from __future__ import annotations

import sys

import UnityPy


def main() -> int:
    path, keyword = sys.argv[1], sys.argv[2].lower()
    env = UnityPy.load(path)
    gos = {}
    trs = {}
    for obj in env.objects:
        if obj.type.name == "GameObject":
            d = obj.read()
            gos[obj.path_id] = d
        elif obj.type.name in ("Transform", "RectTransform"):
            d = obj.read()
            trs[obj.path_id] = d

    name_of_go = {}
    for pid, go in gos.items():
        try:
            name_of_go[pid] = go.m_Name
        except Exception:
            pass

    tr_by_go = {}
    for pid, tr in trs.items():
        try:
            tr_by_go[tr.m_GameObject.path_id] = (pid, tr)
        except Exception:
            pass

    def tr_summary(go_pid: int) -> str:
        item = tr_by_go.get(go_pid)
        if not item:
            return "no-transform"
        _pid, tr = item
        p = tr.m_LocalPosition
        s = tr.m_LocalScale
        return (
            f"pos=({p.x:.2f},{p.y:.2f},{p.z:.2f}) "
            f"scale=({s.x:.2f},{s.y:.2f},{s.z:.2f})"
        )

    def children_names(go_pid: int) -> list[str]:
        item = tr_by_go.get(go_pid)
        if not item:
            return []
        _pid, tr = item
        out = []
        try:
            for child in tr.m_Children:
                cpid = child.path_id
                cgo = trs.get(cpid)
                if cgo is not None:
                    out.append(name_of_go.get(cgo.m_GameObject.path_id, "?"))
        except Exception:
            pass
        return out

    hits = 0
    go_by_tr = {pid: tr for pid, tr in trs.items()}
    for pid, go in gos.items():
        name = name_of_go.get(pid, "")
        if keyword in name.lower():
            hits += 1
            print(f"[{pid}] {name}  {tr_summary(pid)}")
            kids = children_names(pid)
            if kids:
                print("    children: " + ", ".join(kids[:20]))
            item = tr_by_go.get(pid)
            if item:
                chain = []
                tr = item[1]
                for _ in range(12):
                    try:
                        fpid = tr.m_Father.path_id
                    except Exception:
                        break
                    if not fpid or fpid not in go_by_tr:
                        break
                    parent_tr = go_by_tr[fpid]
                    gp = parent_tr.m_GameObject.path_id
                    chain.append(name_of_go.get(gp, "?"))
                    tr = parent_tr
                if chain:
                    print("    parents: " + " <- ".join(chain))
    print(f"total GameObjects={len(gos)} hits={hits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
