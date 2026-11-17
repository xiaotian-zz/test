#!/usr/bin/env python3
"""检查 AssetBundle 中指定 Prefab 的组件与 MonoBehaviour 字段。

用法:
  python inspect_prefab.py <bundle> <prefab名>
"""
from __future__ import annotations

import sys

import UnityPy


def main() -> int:
    path, prefab = sys.argv[1], sys.argv[2]
    env = UnityPy.load(path)
    objs = {o.path_id: o for o in env.objects}

    go = None
    for obj in env.objects:
        if obj.type.name == "GameObject":
            d = obj.read()
            if getattr(d, "m_Name", "") == prefab:
                go = (obj, d)
                break
    if go is None:
        print(f"prefab {prefab} not found")
        return 1

    obj, data = go
    print(f"GameObject {prefab} path_id={obj.path_id} active={getattr(data,'m_IsActive','?')}")
    for comp in data.m_Component:
        cp = comp.component if hasattr(comp, "component") else comp
        try:
            cobj = objs.get(cp.path_id)
        except Exception:
            cobj = None
        ctype = cobj.type.name if cobj else "?"
        print(f"  - {ctype} path_id={cp.path_id}")
        if ctype == "MonoBehaviour" and cobj is not None:
            try:
                tree = cobj.read_typetree()
                for k, v in tree.items():
                    if k.startswith("m_") and k not in ("m_GameObject", "m_Enabled", "m_Script"):
                        continue
                    print(f"      {k} = {v!r}")
            except Exception as exc:  # noqa: BLE001
                print(f"      <typetree failed: {exc}>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
