#!/usr/bin/env python3
"""深度扫描 level 中的新年/摊位线索：对象名 + MonoBehaviour 内部字符串。

用法:
  python scan_level_strings.py <level文件> [关键词逗号分隔]
"""
from __future__ import annotations

import os
import re
import struct
import sys

import UnityPy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_newyear_maps import world_trs  # noqa: E402

PRINTABLE = re.compile(rb"[\x20-\x7e]{4,}")
DEFAULT_KEYS = "bazaar,baazar,christmas,market,stall,xmas,new_year,ny_"


def main() -> int:
    path = sys.argv[1]
    keys = [k.strip().lower() for k in (sys.argv[2] if len(sys.argv) > 2 else DEFAULT_KEYS).split(",") if k.strip()]
    data_dir = os.path.dirname(path)
    env = UnityPy.load(path)
    gos = {}
    nodes = {}
    tr_by_go = {}
    for obj in env.objects:
        if obj.type.name == "GameObject":
            try:
                gos[obj.path_id] = getattr(obj.read(), "m_Name", "?")
            except Exception:
                pass
        elif obj.type.name in ("Transform", "RectTransform"):
            d = obj.read()
            p, r, s = d.m_LocalPosition, d.m_LocalRotation, d.m_LocalScale
            nodes[obj.path_id] = type("N", (), {
                "pos": (p.x, p.y, p.z), "rot": (r.x, r.y, r.z, r.w), "scale": (s.x, s.y, s.z),
                "father": getattr(d, "m_Father", None), "go": d.m_GameObject.path_id,
            })()
            try:
                tr_by_go[d.m_GameObject.path_id] = obj.path_id
            except Exception:
                pass

    def chain(gid: int) -> list[str]:
        out = []
        cur = nodes.get(tr_by_go.get(gid, -1))
        for _ in range(8):
            if cur is None:
                break
            f = getattr(cur, "father", None)
            if f is None or f.path_id not in nodes:
                break
            cur = nodes[f.path_id]
            out.append(gos.get(cur.go, "?"))
        return out

    cache: dict[int, tuple] = {}
    print(f"== {os.path.basename(path)}")
    print("-- 对象名命中")
    for pid, name in gos.items():
        low = name.lower()
        if any(k in low for k in keys):
            tr = tr_by_go.get(pid)
            wp = world_trs(tr, nodes, cache)[0] if tr else (0, 0, 0)
            print(f"   [{pid}] {name}  world=({wp[0]:.2f},{wp[1]:.2f},{wp[2]:.2f})  parents={' < '.join(chain(pid))}")
    print("-- MonoBehaviour 字符串命中")
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        try:
            raw = obj.get_raw_data()
        except Exception:
            continue
        if len(raw) < 28:
            continue
        gfid, gpid = struct.unpack_from("<iq", raw, 0)
        hits = []
        for m in PRINTABLE.finditer(raw):
            txt = m.group().decode("utf-8", "ignore").lower()
            if any(k in txt for k in keys):
                hits.append(m.group().decode("utf-8", "ignore"))
        if not hits:
            continue
        tr = tr_by_go.get(gpid)
        wp = world_trs(tr, nodes, cache)[0] if tr else (0, 0, 0)
        print(
            f"   mb={obj.path_id} go={gos.get(gpid, '?')} world=({wp[0]:.2f},{wp[1]:.2f},{wp[2]:.2f}) "
            f"parents={' < '.join(chain(gpid))} strings={hits[:8]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
