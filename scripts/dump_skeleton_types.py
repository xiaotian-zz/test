#!/usr/bin/env python3
"""打印骨架包的 typetree 结构 + 每类一个实例的完整键。

用法:
  python dump_skeleton_types.py <bundle> [class_id ...]
"""
from __future__ import annotations

import sys

import UnityPy


def walk(node, depth=0, out=None):
    if out is None:
        out = []
    pad = "  " * depth
    out.append(
        f"{pad}{node.m_Type} {node.m_Name}"
        f" byte={node.m_ByteSize} var={node.m_VariableCount}"
        f" level={node.m_Level} metaflag={node.m_MetaFlag} typeflags={node.m_TypeFlags}"
    )
    for c in node.m_Children:
        walk(c, depth + 1, out)
    return out


def shorten(value, depth: int = 0):
    if depth > 6:
        return "..."
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    if isinstance(value, list):
        if len(value) > 14:
            return [shorten(v, depth + 1) for v in value[:14]] + [f"...{len(value)}"]
        return [shorten(v, depth + 1) for v in value]
    if isinstance(value, dict):
        return {k: shorten(v, depth + 1) for k, v in value.items()}
    return value


def main() -> int:
    path = sys.argv[1]
    want = {int(x) for x in sys.argv[2:]} or None
    env = UnityPy.load(path)
    bf = env.file
    sf = list(bf.files.values())[0]
    print(f"types={len(sf.types)} objects={len(sf.objects)}")
    seen = {}
    for i, t in enumerate(sf.types):
        cid = t.class_id
        print(f"\n=== types[{i}] class_id={cid} nodes={len(t.nodes.m_Children)}")
        print("\n".join(walk(t.nodes)))
        seen.setdefault(cid, t)
    for pid, obj in sf.objects.items():
        cid = int(obj.type)
        if want and cid not in want:
            continue
        if cid in getattr(main, "_done", set()):
            continue
        main._done = getattr(main, "_done", set()) | {cid}
        print(f"\n########## instance class_id={cid} path_id={pid}")
        try:
            tpl = obj.read_typetree()
        except Exception as exc:  # noqa: BLE001
            print(f"  failed: {exc}")
            continue
        print(shorten(tpl))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
