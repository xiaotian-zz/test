#!/usr/bin/env python3
"""查找包含关键词的 TextAsset / MonoBehaviour 字符串。

用法:
  python find_assets_key.py <assets文件> <关键词> [截断长度]
"""
from __future__ import annotations

import re
import sys

import UnityPy

PRINTABLE = re.compile(rb"[\x20-\x7e\r\n\t]{8,}")


def main() -> int:
    path, key = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 800
    env = UnityPy.load(path)
    hits = 0
    for obj in env.objects:
        if obj.type.name not in ("TextAsset", "MonoBehaviour", "Shader"):
            continue
        try:
            data = obj.read()
        except Exception:
            continue
        name = getattr(data, "m_Name", "") or "?"
        text = ""
        if obj.type.name == "TextAsset":
            raw = getattr(data, "m_Script", b"") or b""
            if isinstance(raw, str):
                text = raw
            else:
                text = bytes(raw).decode("utf-8", "ignore")
        else:
            try:
                text = bytes(obj.get_raw_data()).decode("utf-8", "ignore")
            except Exception:
                continue
        if key not in text:
            continue
        hits += 1
        idx = text.find(key)
        print(f"== {obj.type.name} {name} pid={obj.path_id} len={len(text)} hits={text.count(key)}")
        print("   ..." + text[max(0, idx - 120): idx + limit].replace("\n", " | ") + "...")
    print(f"总命中对象 {hits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
