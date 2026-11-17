#!/usr/bin/env python3
"""探测流式存储网格（数据在 .resS）的 stride 与 UV 通道。

用法:
  python probe_stream_mesh.py <assets文件> <path_id> [path_id...]
"""
from __future__ import annotations

import os
import struct
import sys

import UnityPy


def half_to_float(h: int) -> float:
    return struct.unpack("<e", struct.pack("<H", h))[0]


def read_stream(mesh_tree, assets_path: str) -> bytes:
    sd = mesh_tree.get("m_StreamData") or {}
    path = sd.get("path") or ""
    if not path:
        return b""
    res_path = os.path.join(os.path.dirname(assets_path), os.path.basename(path))
    if not os.path.exists(res_path):
        res_path = assets_path + ".resS"
    off, size = sd.get("offset", 0), sd.get("size", 0)
    with open(res_path, "rb") as fh:
        fh.seek(off)
        return fh.read(size)


def main() -> int:
    assets = sys.argv[1]
    wanted = [int(x) for x in sys.argv[2:]]
    env = UnityPy.load(assets)
    for obj in env.objects:
        if obj.path_id not in wanted:
            continue
        tree = obj.read_typetree()
        vd = tree["m_VertexData"]
        vcount = vd["m_VertexCount"]
        data = read_stream(tree, assets)
        aabb = tree["m_LocalAABB"]
        c = aabb["m_Center"]
        e = aabb["m_Extent"]
        print(f"== {tree['m_Name']} id={obj.path_id} verts={vcount} dataBytes={len(data)}")
        print(f"   channels={[(ch['stream'], ch['offset'], ch['format'], ch['dimension']) for ch in vd['m_Channels'][:6]]}")
        print(f"   aabb center=({c['x']:.3f},{c['y']:.3f},{c['z']:.3f}) extent=({e['x']:.3f},{e['y']:.3f},{e['z']:.3f})")
        if not data:
            print("   无流数据")
            continue
        for stride in range(12, 121, 4):
            if len(data) < stride * 2:
                continue
            ok = 0
            tested = 0
            for i in range(0, min(vcount, 40)):
                x, y, z = struct.unpack_from("<fff", data, i * stride)
                tested += 1
                if abs(x - c["x"]) <= e["x"] * 1.2 + 1e-4 and abs(y - c["y"]) <= e["y"] * 1.2 + 1e-4 and abs(z - c["z"]) <= e["z"] * 1.2 + 1e-4:
                    ok += 1
            if ok == tested and tested > 0:
                print(f"   stride={stride} 位置全部落在 AABB")
        # 逐 stride 检查 UV 合理性
        for stride in range(12, 121, 4):
            if len(data) < stride * 2:
                continue
            pos_ok = 0
            for i in range(0, min(vcount, 40)):
                x, y, z = struct.unpack_from("<fff", data, i * stride)
                if abs(x - c["x"]) <= e["x"] * 1.2 + 1e-4 and abs(y - c["y"]) <= e["y"] * 1.2 + 1e-4 and abs(z - c["z"]) <= e["z"] * 1.2 + 1e-4:
                    pos_ok += 1
            if pos_ok != min(vcount, 40):
                continue
            for off in range(12, stride - 3):
                for kind in ("f32", "f16"):
                    if kind == "f32" and off + 8 > stride:
                        continue
                    if kind == "f16" and off + 4 > stride:
                        continue
                    us, vs = [], []
                    for i in range(0, min(vcount, 40)):
                        base = i * stride + off
                        if kind == "f32":
                            u, v = struct.unpack_from("<ff", data, base)
                        else:
                            u, v = struct.unpack_from("<HH", data, base)
                            u, v = half_to_float(u), half_to_float(v)
                        us.append(u)
                        vs.append(v)
                    inside = sum(1 for u, v in zip(us, vs) if -0.01 <= u <= 1.01 and -0.01 <= v <= 1.01)
                    if inside >= len(us) * 0.95:
                        print(f"   stride={stride} UV候选 off={off} {kind} 在[0,1]比例={inside}/{len(us)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
