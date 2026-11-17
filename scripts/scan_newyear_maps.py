#!/usr/bin/env python3
"""扫描所有地图场景，列出新年配件根对象及其世界坐标。

用法:
  python scan_newyear_maps.py <rf4_x64_Data目录> [输出json]
"""
from __future__ import annotations

import json
import math
import os
import sys

import UnityPy

KEYWORDS = (
    "christmas",
    "snegovik",
    "snowman",
    "santa",
    "ny_bazaar",
    "xmas",
    "bazaar",
    "new_year",
    "ny2026",
    "ny_2026",
    "chocolate",
    "elka",
)


def quat_matrix(x: float, y: float, z: float, w: float) -> list[list[float]]:
    xx, yy, zz = x * x, y * y, z * z
    xy, xz, yz = x * y, x * z, y * z
    wx, wy, wz = w * x, w * y, w * z
    return [
        [1 - 2 * (yy + zz), 2 * (xy - wz), 2 * (xz + wy)],
        [2 * (xy + wz), 1 - 2 * (xx + zz), 2 * (yz - wx)],
        [2 * (xz - wy), 2 * (yz + wx), 1 - 2 * (xx + yy)],
    ]


class TransformNode:
    __slots__ = ("pos", "rot", "scale", "father", "children", "go")

    def __init__(self, pos, rot, scale, father, children, go):
        self.pos = pos
        self.rot = rot
        self.scale = scale
        self.father = father
        self.children = children
        self.go = go


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def world_trs(pid: int, nodes: dict[int, TransformNode], cache: dict[int, tuple]) -> tuple:
    if pid in cache:
        return cache[pid]
    node = nodes.get(pid)
    if node is None:
        result = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0))
        cache[pid] = result
        return result
    if node.father and node.father.path_id in nodes:
        (pp, pq, ps) = world_trs(node.father.path_id, nodes, cache)
        pm = quat_matrix(*pq)
        lm = quat_matrix(*node.rot)
        rm = mat_mul(pm, lm)
        # 位置：父旋转 * (父缩放 * 本地位置) + 父位置
        sx, sy, sz = ps
        lx, ly, lz = node.pos
        vx, vy, vz = lx * sx, ly * sy, lz * sz
        wx = pm[0][0] * vx + pm[0][1] * vy + pm[0][2] * vz + pp[0]
        wy = pm[1][0] * vx + pm[1][1] * vy + pm[1][2] * vz + pp[1]
        wz = pm[2][0] * vx + pm[2][1] * vy + pm[2][2] * vz + pp[2]
        ws = (ps[0] * node.scale[0], ps[1] * node.scale[1], ps[2] * node.scale[2])
        # 四元数相乘（世界 = 父 * 本地）
        px, py, pz, pw = pq
        lx2, ly2, lz2, lw = node.rot
        qx = pw * lx2 + px * lw + py * lz2 - pz * ly2
        qy = pw * ly2 - px * lz2 + py * lw + pz * lx2
        qz = pw * lz2 + px * ly2 - py * lx2 + pz * lw
        qw = pw * lw - px * lx2 - py * ly2 - pz * lz2
        result = ((wx, wy, wz), (qx, qy, qz, qw), ws)
    else:
        result = (node.pos, node.rot, node.scale)
    cache[pid] = result
    return result


def yaw_of(q) -> float:
    x, y, z, w = q
    return math.degrees(math.atan2(2 * (w * y + x * z), 1 - 2 * (y * y + z * z)))


def scan_level(path: str, mesh_names: dict[int, str]) -> dict:
    env = UnityPy.load(path)
    gos: dict[int, object] = {}
    nodes: dict[int, TransformNode] = {}
    tr_by_go: dict[int, int] = {}
    for obj in env.objects:
        if obj.type.name == "GameObject":
            gos[obj.path_id] = obj.read()
        elif obj.type.name in ("Transform", "RectTransform"):
            d = obj.read()
            p, r, s = d.m_LocalPosition, d.m_LocalRotation, d.m_LocalScale
            nodes[obj.path_id] = TransformNode(
                (p.x, p.y, p.z), (r.x, r.y, r.z, r.w), (s.x, s.y, s.z),
                getattr(d, "m_Father", None), getattr(d, "m_Children", []), d.m_GameObject.path_id,
            )
            try:
                tr_by_go[d.m_GameObject.path_id] = obj.path_id
            except Exception:
                pass

    def name(pid: int) -> str:
        go = gos.get(pid)
        return getattr(go, "m_Name", "?") if go else "?"

    def is_target(pid: int) -> bool:
        low = name(pid).lower()
        return any(k in low for k in KEYWORDS)

    cache: dict[int, tuple] = {}
    results = []
    seen_roots = set()
    for pid, go in gos.items():
        if not is_target(pid):
            continue
        tr_pid = tr_by_go.get(pid)
        if tr_pid is None:
            continue
        # 找匹配集合中的最高祖先
        root_pid = pid
        cur = nodes.get(tr_pid)
        chain = []
        while cur is not None and cur.father and cur.father.path_id in nodes:
            parent = nodes[cur.father.path_id]
            chain.append(name(cur.go))
            if is_target(parent.go):
                root_pid = parent.go
            else:
                break
            cur = parent
        if root_pid in seen_roots:
            continue
        seen_roots.add(root_pid)
        rtr = tr_by_go.get(root_pid)
        if rtr is None:
            continue
        wp, wq, ws = world_trs(rtr, nodes, cache)
        node = nodes.get(rtr)
        lp = node.pos if node else (0, 0, 0)
        results.append({
            "root": name(root_pid),
            "rootPath": " <- ".join(["CHRISTMAS" if c == "CHRISTMAS" else c for c in chain]) or "-",
            "localPos": [round(v, 3) for v in lp],
            "worldPos": [round(v, 3) for v in wp],
            "worldYaw": round(yaw_of(wq), 1),
            "worldScale": [round(v, 3) for v in ws],
        })
    return {"level": os.path.basename(path), "items": results}


def main() -> int:
    data_dir = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join("artifacts", "newyear_maps.json")
    levels = sorted(
        [f for f in os.listdir(data_dir) if f.startswith("level") and os.path.isfile(os.path.join(data_dir, f))],
        key=lambda x: int(x[5:] or 0),
    )
    all_data = []
    for lv in levels:
        path = os.path.join(data_dir, lv)
        try:
            data = scan_level(path, {})
        except Exception as exc:  # noqa: BLE001
            print(f"{lv}: 失败 {exc}")
            continue
        if data["items"]:
            print(f"== {lv} ({len(data['items'])} 个配件根)")
            for it in data["items"]:
                print(
                    f"   {it['root']:<28} world=({it['worldPos'][0]:.2f},{it['worldPos'][1]:.2f},{it['worldPos'][2]:.2f}) "
                    f"local=({it['localPos'][0]:.2f},{it['localPos'][1]:.2f},{it['localPos'][2]:.2f}) "
                    f"yaw={it['worldYaw']} scale={it['worldScale']} path={it['rootPath']}"
                )
            all_data.append(data)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(all_data, fh, ensure_ascii=False, indent=2)
    print(f"写出 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
