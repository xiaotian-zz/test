#!/usr/bin/env python3
"""读取场景中 MeshFilter 引用的网格及外部文件编号。

用法:
  python mesh_source.py <level文件> <GameObject名>
"""
from __future__ import annotations

import sys

import UnityPy


def main() -> int:
    path, target = sys.argv[1], sys.argv[2]
    env = UnityPy.load(path)
    objs = {o.path_id: o for o in env.objects}
    ext_paths: list[str] = []
    for name, f in getattr(env, "files", {}).items():
        for ext in getattr(f, "externals", None) or []:
            ext_paths.append(getattr(ext, "path", str(ext)))
    print("externals:", len(ext_paths))
    for i, p in enumerate(ext_paths, start=1):
        print(f"   {i}: {p}")

    for obj in env.objects:
        if obj.type.name != "GameObject":
            continue
        data = obj.read()
        if getattr(data, "m_Name", "") != target:
            continue
        print(f"GameObject {target} path_id={obj.path_id}")
        for comp in data.m_Component:
            ptr = comp.component if hasattr(comp, "component") else comp
            cobj = objs.get(ptr.path_id)
            if cobj is None:
                continue
            if cobj.type.name != "MeshFilter":
                continue
            mf = cobj.read()
            mesh = mf.m_Mesh
            print(f"   MeshFilter -> mesh file_id={mesh.file_id} path_id={mesh.path_id}")
            if 1 <= mesh.file_id <= len(ext_paths):
                print(f"   来源文件: {ext_paths[mesh.file_id - 1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
