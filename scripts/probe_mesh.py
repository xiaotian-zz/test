#!/usr/bin/env python3
"""探测 sharedassets 中网格的顶点通道结构（精简输出）。

用法:
  python probe_mesh.py <sharedassets文件> <path_id> [path_id...]
"""
from __future__ import annotations

import sys

import UnityPy


def main() -> int:
    env = UnityPy.load(sys.argv[1])
    objs = {o.path_id: o for o in env.objects}
    for pid in [int(x) for x in sys.argv[2:]]:
        obj = objs.get(pid)
        if obj is None:
            print(f"{pid}: 不存在")
            continue
        mesh = obj.read()
        vd = getattr(mesh, "m_VertexData", None)
        vcount = getattr(vd, "m_VertexCount", None) if vd else None
        raw = getattr(vd, "m_DataSize", b"") if vd else b""
        idx = getattr(mesh, "m_IndexBuffer", b"") or b""
        channels = getattr(vd, "m_Channels", []) if vd else []
        print(f"== {getattr(mesh,'m_Name','?')} id={pid}")
        print(f"   verts={vcount} dataBytes={len(raw)} indexBytes={len(idx)} submeshes={len(getattr(mesh,'m_SubMeshes',[]) or [])}")
        for i, ch in enumerate(channels):
            print(
                f"   ch{i}: stream={getattr(ch,'stream','?')} offset={getattr(ch,'offset','?')} "
                f"format={getattr(ch,'format','?')} dim={getattr(ch,'dimension','?')}"
            )
        subs = getattr(mesh, "m_SubMeshes", []) or []
        for i, sm in enumerate(subs):
            print(
                f"   sub{i}: firstByte={getattr(sm,'firstByte','?')} indexCount={getattr(sm,'indexCount','?')} "
                f"baseVertex={getattr(sm,'baseVertex','?')} firstVertex={getattr(sm,'firstVertex','?')}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
