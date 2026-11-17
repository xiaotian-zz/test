#!/usr/bin/env python3
"""从运行中的 RF4 客户端进程内存里抓取 IL2CPP global-metadata.dat。

用法: py -3 dump_il2cpp_meta.py [exe] [outdir]
不执行任何游戏逻辑，只做 ReadProcessMemory 搜索 0xFAB11BAF 头。
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import struct
import subprocess
import sys
import time

MAGIC = 0xFAB11BAF
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MEMORY_BASIC_INFORMATION64(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_ulonglong),
        ("AllocationBase", ctypes.c_ulonglong),
        ("AllocationProtect", wt.DWORD),
        ("__alignment1", wt.DWORD),
        ("RegionSize", ctypes.c_ulonglong),
        ("State", wt.DWORD),
        ("Protect", wt.DWORD),
        ("Type", wt.DWORD),
        ("__alignment2", wt.DWORD),
    ]


k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_ulonglong,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION64), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_ulonglong, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL

READABLE = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}
MEM_COMMIT = 0x1000


def read_mem(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, addr, buf, size, ctypes.byref(got)):
        return None
    return buf.raw[:got.value]


def find_magic(h, pid):
    addr = 0
    hits = []
    mbi = MEMORY_BASIC_INFORMATION64()
    while addr < 0x7FFFFFFF0000:
        if not k32.VirtualQueryEx(h, addr, ctypes.byref(mbi), ctypes.sizeof(mbi)):
            break
        base = mbi.BaseAddress
        size = mbi.RegionSize
        if size == 0:
            break
        nxt = base + size
        if (mbi.State == MEM_COMMIT and (mbi.Protect & 0xFF) in READABLE
                and 1 * 1024 * 1024 <= size <= 2 * 1024 * 1024 * 1024):
            off = 0
            chunk = 8 * 1024 * 1024
            tail = b""
            while off < size:
                n = min(chunk, size - off)
                data = read_mem(h, base + off, n)
                if data:
                    buf = tail + data
                    i = 0
                    mag = struct.pack("<I", MAGIC)
                    while True:
                        j = buf.find(mag, i)
                        if j < 0:
                            break
                        hits.append(base + off - len(tail) + j)
                        i = j + 1
                    tail = buf[-4:]
                off += n
        addr = nxt
    return hits


def header_extent(data):
    """按 global-metadata 头里的 (offset,count) 对估算文件长度。"""
    if len(data) < 0x100:
        return len(data)
    version = struct.unpack_from("<i", data, 4)[0]
    best = 0
    # 头部 0x08..0x100 是连续 (offset,size/count) 对；取 offset+size 的最大值。
    for off in range(8, min(0x100, len(data) - 8) + 1, 8):
        o, c = struct.unpack_from("<ii", data, off)
        if 0 < o < 0x40000000 and 0 <= c < 0x40000000:
            best = max(best, o + c)
    return version, best


def find_pid(name):
    out = subprocess.check_output(["tasklist", "/FO", "CSV", "/NH"], text=True,
                                  errors="replace")
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == name.lower() + ".exe":
            return int(parts[1].replace(",", ""))
    return None


def main():
    attach = len(sys.argv) > 1 and sys.argv[1] == "--attach"
    exe = r"F:\RF4\Game\rf4_x64.exe" if attach else (sys.argv[1] if len(sys.argv) > 1 else r"F:\RF4\Game\rf4_x64.exe")
    outdir = sys.argv[2] if not attach and len(sys.argv) > 2 else r"f:\rea\artifacts\il2cpp_meta"
    os.makedirs(outdir, exist_ok=True)

    if attach:
        pid = find_pid("rf4_x64")
        if not pid:
            print("rf4_x64.exe not running")
            return 1
        proc = None
        print("attach pid", pid)
    else:
        proc = subprocess.Popen([exe], cwd=os.path.dirname(exe))
        pid = proc.pid
        print("started pid", pid)
        time.sleep(2.0)
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print("OpenProcess failed", ctypes.get_last_error())
        return 1
    try:
        deadline = time.time() + (30 if attach else 20)
        hits = []
        while time.time() < deadline:
            if proc is not None and proc.poll() is not None:
                break
            hits = find_magic(h, pid)
            if hits:
                break
            time.sleep(0.5)
        print("hits", [hex(x) for x in hits[:5]], "count", len(hits))
        for idx, hit in enumerate(hits[:5]):
            head = read_mem(h, hit, 0x200) or b""
            version, extent = header_extent(head)
            print(f"hit {idx} @{hit:#x} version={version} extent={extent:#x}")
            if not (24 <= version <= 40) or extent < 1024:
                continue
            length = min(extent + 0x1000, 512 * 1024 * 1024)
            data = read_mem(h, hit, length)
            if not data:
                print("read failed")
                continue
            out = os.path.join(outdir, "global-metadata.dat")
            with open(out, "wb") as fh:
                fh.write(data)
            print("wrote", out, len(data))
            return 0
        return 2
    finally:
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    sys.exit(main())
