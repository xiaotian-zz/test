"""扫描 bundle 内的对象名，查找新年集市相关资源。"""
import re
import sys

import UnityPy

path = sys.argv[1]
pat = re.compile(sys.argv[2], re.I)

env = UnityPy.load(path)
hits = []
count = 0
for o in env.objects:
    count += 1
    t = o.type.name
    if t not in ("GameObject", "Mesh", "Material"):
        continue
    try:
        d = o.read()
        n = getattr(d, "m_Name", "") or ""
    except Exception:
        continue
    if pat.search(n):
        hits.append((t, n, o.path_id))

print(f"total={count} hits={len(hits)}")
for t, n, pid in hits[:80]:
    print(f"  {t:12s} {n}  id={pid}")
