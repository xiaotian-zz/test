"""从运行中的 RF4 客户端导出 IL2CPP 元数据清单（类/字段/方法/属性/签名）。

用法: py -3 il2cpp_dump.py <pid> [assembly_index ...]
输出:
  f:\\rea\\artifacts\\il2cpp_dump\\<asm>.ndjson   每行一个类的完整 JSON
  f:\\rea\\artifacts\\il2cpp_dump\\dump.cs        C# 风格声明（无方法体）
"""
from __future__ import annotations

import frida
import json
import os
import sys
import time

OUT = r"f:\rea\artifacts\il2cpp_dump"

JS = r"""
const ga = Process.getModuleByName('GameAssembly.dll');
const E = n => ga.getExportByName(n);
const P = Process.pointerSize;
const F = {
  domainGet: new NativeFunction(E('il2cpp_domain_get'), 'pointer', []),
  domainAsms: new NativeFunction(E('il2cpp_domain_get_assemblies'), 'pointer', ['pointer','pointer']),
  asmImg: new NativeFunction(E('il2cpp_assembly_get_image'), 'pointer', ['pointer']),
  imgName: new NativeFunction(E('il2cpp_image_get_name'), 'pointer', ['pointer']),
  imgCount: new NativeFunction(E('il2cpp_image_get_class_count'), 'uint', ['pointer']),
  imgClass: new NativeFunction(E('il2cpp_image_get_class'), 'pointer', ['pointer','uint']),
  cName: new NativeFunction(E('il2cpp_class_get_name'), 'pointer', ['pointer']),
  cNs: new NativeFunction(E('il2cpp_class_get_namespace'), 'pointer', ['pointer']),
  cParent: new NativeFunction(E('il2cpp_class_get_parent'), 'pointer', ['pointer']),
  cFlags: new NativeFunction(E('il2cpp_class_get_flags'), 'uint', ['pointer']),
  cFields: new NativeFunction(E('il2cpp_class_get_fields'), 'pointer', ['pointer','pointer']),
  fName: new NativeFunction(E('il2cpp_field_get_name'), 'pointer', ['pointer']),
  fType: new NativeFunction(E('il2cpp_field_get_type'), 'pointer', ['pointer']),
  fOffset: new NativeFunction(E('il2cpp_field_get_offset'), 'uint', ['pointer']),
  fFlags: new NativeFunction(E('il2cpp_field_get_flags'), 'uint', ['pointer']),
  tName: new NativeFunction(E('il2cpp_type_get_name'), 'pointer', ['pointer']),
  cMethods: new NativeFunction(E('il2cpp_class_get_methods'), 'pointer', ['pointer','pointer']),
  mName: new NativeFunction(E('il2cpp_method_get_name'), 'pointer', ['pointer']),
  mToken: new NativeFunction(E('il2cpp_method_get_token'), 'uint', ['pointer']),
  mFlags: new NativeFunction(E('il2cpp_method_get_flags'), 'uint', ['pointer','pointer']),
  mRet: new NativeFunction(E('il2cpp_method_get_return_type'), 'pointer', ['pointer']),
  mParamCount: new NativeFunction(E('il2cpp_method_get_param_count'), 'uint', ['pointer']),
  mParam: new NativeFunction(E('il2cpp_method_get_param'), 'pointer', ['pointer','uint']),
  cProps: new NativeFunction(E('il2cpp_class_get_properties'), 'pointer', ['pointer','pointer']),
  pName: new NativeFunction(E('il2cpp_property_get_name'), 'pointer', ['pointer']),
  pFlags: new NativeFunction(E('il2cpp_property_get_flags'), 'uint', ['pointer']),
};
function cstr(p){ try { return p.isNull() ? '' : p.readUtf8String(); } catch(e){ return ''; } }
function tname(p){ try { return p.isNull() ? '' : cstr(F.tName(p)); } catch(e){ return ''; } }
function cfull(k){
  const ns = cstr(F.cNs(k)), nm = cstr(F.cName(k));
  return ns ? ns + '.' + nm : nm;
}
function dumpClass(k){
  const fields = [];
  try {
    const it = Memory.alloc(P); it.writePointer(ptr(0));
    for (let guard = 0; guard < 512; guard++) {
      const f = F.cFields(k, it);
      if (f.isNull()) break;
      fields.push({ name: cstr(F.fName(f)), type: tname(F.fType(f)),
                    offset: F.fOffset(f), flags: F.fFlags(f) });
    }
  } catch(e) {}
  const methods = [];
  try {
    const it = Memory.alloc(P); it.writePointer(ptr(0));
    for (let guard = 0; guard < 2048; guard++) {
      const m = F.cMethods(k, it);
      if (m.isNull()) break;
      const n = F.mParamCount(m);
      const ps = [];
      for (let i = 0; i < n && i < 32; i++) ps.push(tname(F.mParam(m, i)));
      const fl = Memory.alloc(4);
      const fv = F.mFlags(m, fl);
      methods.push({ name: cstr(F.mName(m)), token: F.mToken(m), ret: tname(F.mRet(m)),
                     params: ps, flags: fv, iflags: fl.readU32() });
    }
  } catch(e) {}
  const props = [];
  try {
    const it = Memory.alloc(P); it.writePointer(ptr(0));
    for (let guard = 0; guard < 512; guard++) {
      const p = F.cProps(k, it);
      if (p.isNull()) break;
      props.push({ name: cstr(F.pName(p)), flags: F.pFlags(p) });
    }
  } catch(e) {}
  const par = F.cParent(k);
  return {
    name: cstr(F.cName(k)), ns: cstr(F.cNs(k)),
    parent: par.isNull() ? '' : cfull(par),
    flags: F.cFlags(k),
    fields: fields, methods: methods, props: props,
  };
}

const asmIdx = %ASM_IDX%;
const domain = F.domainGet();
const cnt = Memory.alloc(8);
const asms = F.domainAsms(domain, cnt);
const total = cnt.readUInt();
if (asmIdx >= total) { send({error: 'bad index', total}); }
else {
  const asm = asms.add(asmIdx * P).readPointer();
  const img = F.asmImg(asm);
  const name = cstr(F.imgName(img));
  const n = F.imgCount(img);
  send({type:'meta', assembly:name, count:n});
  let batch = [];
  for (let i = 0; i < n; i++) {
    try {
      const k = F.imgClass(img, i);
      if (k.isNull()) continue;
      batch.push(dumpClass(k));
    } catch(e) {}
    if (batch.length >= 100) { send({type:'batch', classes:batch}); batch = []; }
  }
  if (batch.length) send({type:'batch', classes:batch});
  send({type:'done'});
}
"""


def render(classes):
    lines = []
    for c in classes:
        ns = c.get("ns") or ""
        name = c.get("name") or ""
        full = f"{ns}.{name}" if ns else name
        parent = c.get("parent") or ""
        kind = "class"
        flags = c.get("flags") or 0
        if flags & 0x20:
            kind = "interface"
        if flags & 0x80:
            kind = "struct"
        if flags & 0x100:
            kind = "enum"
        head = f"public {kind} {full}"
        if parent:
            head += f" : {parent}"
        lines.append(head + " {")
        for f in c.get("fields") or []:
            lines.append(f"    public {f.get('type','')} {f.get('name','')}; // +0x{f.get('offset',0):X}")
        for p in c.get("props") or []:
            lines.append(f"    public {p.get('name','')} {{ get; set; }}")
        for m in c.get("methods") or []:
            params = ", ".join(m.get("params") or [])
            ret = m.get("ret") or "void"
            lines.append(f"    // RVA: 0x0 Token: 0x{m.get('token',0):X}")
            lines.append(f"    public {ret} {m.get('name','')}({params}) {{ }}")
        lines.append("}")
        lines.append("")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    pid = int(sys.argv[1])
    idxs = [int(x) for x in sys.argv[2:]] or [0]
    os.makedirs(OUT, exist_ok=True)
    session = frida.attach(pid)
    for idx in idxs:
        state = {"asm": f"asm{idx}", "classes": []}
        script = session.create_script(JS.replace("%ASM_IDX%", str(idx)))
        t0 = time.time()

        def on_msg(m, data):
            if m.get("type") != "send":
                print("[frida]", m, file=sys.stderr)
                return
            p = m.get("payload") or {}
            if p.get("type") == "meta":
                state["asm"] = p.get("assembly", state["asm"]).replace(".dll", "")
                print(f"[{idx}] {state['asm']} classes={p.get('count')}")
            elif p.get("type") == "batch":
                state["classes"].extend(p.get("classes") or [])
            elif p.get("type") == "done":
                state["done"] = True
            elif p.get("error"):
                print("[frida error]", p, file=sys.stderr)

        script.on("message", on_msg)
        script.load()
        while not state.get("done") and time.time() - t0 < 1800:
            time.sleep(0.2)
        try:
            script.unload()
        except Exception:
            pass
        asm = state["asm"] or f"asm{idx}"
        nd = os.path.join(OUT, f"{asm}.ndjson")
        with open(nd, "w", encoding="utf-8") as fh:
            for c in state["classes"]:
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
        cs = os.path.join(OUT, f"{asm}.cs")
        with open(cs, "w", encoding="utf-8") as fh:
            fh.write(render(state["classes"]))
        print(f"wrote {nd} ({len(state['classes'])} classes) and {cs}")
    session.detach()
    return 0


if __name__ == "__main__":
    sys.exit(main())
