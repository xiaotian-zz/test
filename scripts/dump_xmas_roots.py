#!/usr/bin/env python3
"""列出每张地图 CHRISTMAS 根及其直接子对象（加载内容清单）。

用法:
  python dump_xmas_roots.py <rf4_x64_Data目录> [输出json]
"""
from __future__ import annotations

import json
import os
import sys

import UnityPy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_newyear_maps import world_trs, yaw_of  # noqa: E402


def main() -> int:
    data_dir = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join("artifacts", "xmas_roots.json")
    levels = sorted(
        [f for f in os.listdir(data_dir) if f.startswith("level") and os.path.isfile(os.path.join(data_dir, f))],
        key=lambda x: int(x[5:] or 0),
    )
    all_data = []
    for lv in levels:
        env = UnityPy.load(os.path.join(data_dir, lv))
        gos, nodes, tr_by_go = {}, {}, {}
        mesh_ref = {}
        for obj in env.objects:
            if obj.type.name == "GameObject":
                try:
                    gos[obj.path_id] = obj.read()
                except Exception:
                    pass
            elif obj.type.name in ("Transform", "RectTransform"):
                d = obj.read()
                p, r, s = d.m_LocalPosition, d.m_LocalRotation, d.m_LocalScale
                nodes[obj.path_id] = type("N", (), {
                    "pos": (p.x, p.y, p.z), "rot": (r.x, r.y, r.z, r.w), "scale": (s.x, s.y, s.z),
                    "father": getattr(d, "m_Father", None), "children": getattr(d, "m_Children", []),
                    "go": d.m_GameObject.path_id,
                })()
                try:
                    tr_by_go[d.m_GameObject.path_id] = obj.path_id
                except Exception:
                    pass
            elif obj.type.name in ("MeshFilter", "SkinnedMeshRenderer"):
                try:
                    d = obj.read()
                    mesh_ref[d.m_GameObject.path_id] = (obj.type.name, d.m_Mesh.file_id, d.m_Mesh.path_id)
                except Exception:
                    pass
        name = lambda pid: getattr(gos.get(pid), "m_Name", "?")
        cache = {}
        root = next((pid for pid in gos if name(pid) == "CHRISTMAS"), None)
        if root is None:
            continue
        rtr = tr_by_go.get(root)
        wp, wq, ws = world_trs(rtr, nodes, cache) if rtr else ((0, 0, 0), (0, 0, 0, 1), (1, 1, 1))
        node = nodes.get(rtr)
        children = []
        if node:
            for child in node.children:
                cn = nodes.get(child.path_id)
                if cn is None:
                    continue
                cwp = world_trs(child.path_id, nodes, cache)[0]
                stack = [child.path_id]
                count = 0
                meshes = []
                while stack:
                    cur = nodes.get(stack.pop())
                    if cur is None:
                        continue
                    count += 1
                    if cur.go in mesh_ref:
                        m = mesh_ref[cur.go]
                        meshes.append(f"{name(cur.go)}:{m[0]}({m[1]}:{m[2]})")
                    stack.extend(c.path_id for c in cur.children)
                children.append({
                    "name": name(cn.go),
                    "worldPos": [round(v, 2) for v in cwp],
                    "objects": count,
                    "meshes": meshes[:8],
                    "meshCount": len(meshes),
                })
        entry = {
            "level": lv,
            "root": "CHRISTMAS",
            "worldPos": [round(v, 2) for v in wp],
            "yaw": round(yaw_of(wq), 1),
            "scale": [round(v, 3) for v in ws],
            "children": children,
        }
        all_data.append(entry)
        print(f"== {lv} CHRISTMAS world=({wp[0]:.2f},{wp[1]:.2f},{wp[2]:.2f}) yaw={entry['yaw']} children={len(children)}")
        for ch in children:
            print(f"   {ch['name']:<34} world=({ch['worldPos'][0]:.2f},{ch['worldPos'][1]:.2f},{ch['worldPos'][2]:.2f}) 对象={ch['objects']} 网格={ch['meshCount']}")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(all_data, fh, ensure_ascii=False, indent=2)
    print(f"写出 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
