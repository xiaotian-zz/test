#!/usr/bin/env python3
"""解析种子 info_hash 并查询 tracker 的做种/下载人数。

用法:
  python bt_announce.py <torrent> [announce_url]
"""
from __future__ import annotations

import hashlib
import sys
import urllib.parse
import urllib.request


def parse_bencode(data: bytes, pos: int) -> tuple[object, int]:
    ch = data[pos : pos + 1]
    if ch == b"i":
        end = data.index(b"e", pos)
        return int(data[pos + 1 : end]), end + 1
    if ch == b"l":
        pos += 1
        items = []
        while data[pos : pos + 1] != b"e":
            item, pos = parse_bencode(data, pos)
            items.append(item)
        return items, pos + 1
    if ch == b"d":
        pos += 1
        result = {}
        while data[pos : pos + 1] != b"e":
            key, pos = parse_bencode(data, pos)
            val, pos = parse_bencode(data, pos)
            result[key] = val
        return result, pos + 1
    colon = data.index(b":", pos)
    length = int(data[pos:colon])
    start = colon + 1
    return data[start : start + length], start + length


def main() -> int:
    path = sys.argv[1]
    raw = open(path, "rb").read()
    meta, _ = parse_bencode(raw, 0)
    assert isinstance(meta, dict)
    # 定位 info 字段的原始字节范围
    idx = raw.index(b"4:infod")
    info_start = idx + len(b"4:info")
    _, info_end = parse_bencode(raw, info_start)
    info_hash = hashlib.sha1(raw[info_start:info_end]).digest()
    print("info_hash:", info_hash.hex())

    announce = sys.argv[2] if len(sys.argv) > 2 else meta[b"announce"].decode()
    params = {
        "info_hash": info_hash,
        "peer_id": b"-qB4550-abcdefghijkl"[0:20],
        "port": 6881,
        "uploaded": 0,
        "downloaded": 0,
        "left": meta[b"info"].get(b"length") or sum(f[b"length"] for f in meta[b"info"][b"files"]),
        "compact": 1,
        "event": "started",
    }
    query = urllib.parse.urlencode(params, safe="")
    url = announce + ("&" if "?" in announce else "?") + query
    with urllib.request.urlopen(url, timeout=25) as resp:
        body = resp.read()
    data, _ = parse_bencode(body, 0)
    if isinstance(data, dict):
        peers = data.get(b"peers", b"")
        print("complete(seeders):", data.get(b"complete"))
        print("incomplete(leechers):", data.get(b"incomplete"))
        print("interval:", data.get(b"interval"))
        print("peers_bytes:", len(peers) if isinstance(peers, bytes) else "list")
        if isinstance(peers, list):
            for p in peers[:10]:
                print("  peer:", p)
    else:
        print(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
