"""从运行中客户端的目标网络方法里提取 RIP 相对字符串引用（简易反编译）。"""
import frida, json, sys, time

PID = int(sys.argv[1]) if len(sys.argv) > 1 else 19924

TARGETS = ["onkfgefhlmd", "ckfocaolppf", "pckcdcpghbh", "kffeojjoiap",
           "fmmbakkighp", "plopofeioap", "glonlbdjadi", "ahfcgnafglo",
           "paannkpolaj", "gffmgkaheho", "idmplnggaoe", "llhgklogeal"]

JS = r"""
const ga = Process.getModuleByName('GameAssembly.dll');
const E = n => ga.getExportByName(n);
const P = Process.pointerSize;
const f = {
  dom: new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
  asms: new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
  asmImg: new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
  imgCount: new NativeFunction(E('il2cpp_image_get_class_count'),'uint',['pointer']),
  imgClass: new NativeFunction(E('il2cpp_image_get_class'),'pointer',['pointer','uint']),
  cName: new NativeFunction(E('il2cpp_class_get_name'),'pointer',['pointer']),
  cMethods: new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
  mName: new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
};
const targets = %TARGETS%;
function cstr(p){ try { return p.isNull()?'':p.readUtf8String(); } catch(e){ return ''; } }
function printable(s){ return s && s.length>=3 && /^[\x20-\x7e\t\r\n]+$/.test(s); }
function readC(p, max){
  try { return p.readUtf8String(max); } catch(e){ return ''; }
}
function readW(p, max){
  try { return p.readUtf16String(max); } catch(e){ return ''; }
}
const base = ga.base, end = ga.base.add(ga.size);
function scanStrings(addr){
  const out = [];
  let code;
  try { code = addr.readByteArray(0x900); } catch(e){ return out; }
  const b = new Uint8Array(code);
  for (let i=0;i+7<=b.length;i++){
    const b0=b[i];
    // 48/4C 8D/8B modrm with mod=00 rm=101 (rip-rel): modrm in {05,0D,15,1D,25,2D,35,3D}
    if ((b0===0x48||b0===0x4C) && (b[i+1]===0x8D||b[i+1]===0x8B)) {
      const m=b[i+2];
      if (m===0x05||m===0x0D||m===0x15||m===0x1D||m===0x25||m===0x2D||m===0x35||m===0x3D) {
        const disp = (b[i+3] | (b[i+4]<<8) | (b[i+5]<<16) | (b[i+6]<<24)) | 0;
        const tgt = addr.add(i+7+disp);
        if (tgt.compare(base)<0 || tgt.compare(end)>=0) continue;
        const s1 = readC(tgt, 120);
        if (printable(s1) && /[A-Za-z_]/.test(s1)) out.push(s1);
        else {
          const s2 = readW(tgt, 80);
          if (printable(s2)) out.push('W:'+s2);
        }
      }
    }
  }
  return out;
}
const dom = f.dom(), cnt = Memory.alloc(8);
const asms = f.asms(dom, cnt), n = cnt.readUInt();
for (let ai=0; ai<n; ai++){
  const asm = asms.add(ai*P).readPointer();
  const img = f.asmImg(asm);
  if (img.isNull()) continue;
  const cn = f.imgCount(img);
  for (let ci=0; ci<cn; ci++){
    const k = f.imgClass(img, ci);
    if (k.isNull()) continue;
    const it = Memory.alloc(P); it.writePointer(ptr(0));
    for (let gi=0; gi<512; gi++){
      const m = f.cMethods(k, it);
      if (m.isNull()) break;
      const mn = cstr(f.mName(m));
      if (targets.indexOf(mn) < 0) continue;
      const mp1 = m.add(P).readPointer();
      const mp2 = m.add(P*2).readPointer();
      const mp0 = m.readPointer();
      for (const mp of [mp1, mp2, mp0]) {
        if (mp.isNull() || mp.compare(base)<0 || mp.compare(end)>=0) continue;
        const ss = scanStrings(mp);
        if (ss.length) send({method:mn, class:cstr(f.cName(k)), ptr:mp.toString(), strings:ss});
      }
    }
  }
}
send({done:true});
"""

session = frida.attach(PID)
script = session.create_script(JS.replace("%TARGETS%", json.dumps(TARGETS)))
seen = set()
state = {"done": False}

def on_msg(m, d):
    if m.get("type") != "send":
        print("[frida]", m, file=sys.stderr); return
    p = m.get("payload") or {}
    if p.get("done"):
        state["done"] = True
        return
    key = (p.get("method"), tuple(p.get("strings") or []))
    if key in seen:
        return
    seen.add(key)
    print(p.get("class"), p.get("method"), p.get("ptr"))
    for s in p.get("strings") or []:
        print("   ", s)

script.on("message", on_msg)
script.load()
deadline = time.time() + 90
while not state["done"] and time.time() < deadline:
    time.sleep(0.2)
print("seen", len(seen))
session.detach()
