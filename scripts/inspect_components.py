#!/usr/bin/env python3
"""递归打印 GameObject 层级中的渲染组件与网格引用。

用法:
  python inspect_components.py <场景文件> <GameObject名> [名称...]
"""
from __future__ import annotations

import sys

import UnityPy


def main() -> int:
    path, targets = sys.argv[1], sys.argv[2:]
    env = UnityPy.load(path)
    objs = {o.path_id: o for o in env.objects}
    gos: dict[int, object] = {}
    trs: dict[int, object] = {}
    for obj in env.objects:
        if obj.type.name == "GameObject":
            gos[obj.path_id] = obj.read()
        elif obj.type.name in ("Transform", "RectTransform"):
            trs[obj.path_id] = obj.read()
    tr_by_go = {}
    for pid, tr in trs.items():
        try:
            tr_by_go[tr.m_GameObject.path_id] = tr
        except Exception:
            pass

    def go_name(pid: int) -> str:
        go = gos.get(pid)
        return getattr(go, "m_Name", "?") if go else "?"

    def dump(go_pid: int, depth: int) -> None:
        go = gos.get(go_pid)
        if go is None:
            return
        pad = "  " * depth
        parts = []
        for comp in getattr(go, "m_Component", []):
            ptr = comp.component if hasattr(comp, "component") else comp
            cobj = objs.get(ptr.path_id)
            if cobj is None:
                continue
            t = cobj.type.name
            extra = ""
            try:
                cd = cobj.read()
                if t in ("MeshFilter", "SkinnedMeshRenderer"):
                    mesh = cd.m_Mesh
                    extra = f" mesh=(file={mesh.file_id},pid={mesh.path_id})"
                if t == "MeshRenderer":
                    mats = [m.path_id for m in (cd.m_Materials or [])]
                    extra = f" mats={mats}"
                if t == "SkinnedMeshRenderer":
                    root = getattr(cd, "m_RootBone", None)
                    if root is not None:
                        extra += f" rootBone={root.path_id}"
            except Exception as exc:  # noqa: BLE001
                extra = f" readFail={exc}"
            parts.append(t + extra)
        tr = tr_by_go.get(go_pid)
        pos = ""
        if tr is not None:
            p = tr.m_LocalPosition
            s = tr.m_LocalScale
            pos = f" pos=({p.x:.2f},{p.y:.2f},{p.z:.2f}) scale=({s.x:.2f},{s.y:.2f},{s.z:.2f})"
        print(f"{pad}[{go_pid}] {go_name(go_pid)}{pos} :: " + ", ".join(parts))
        if tr is not None and depth < 6:
            for child in tr.m_Children:
                cgo = trs.get(child.path_id)
                if cgo is not None:
                    dump(cgo.m_GameObject.path_id, depth + 1)

    for target in targets:
        for pid, go in gos.items():
            if getattr(go, "m_Name", "") != target:
                continue
            print(f"=== {target} path_id={pid}")
            dump(pid, 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
