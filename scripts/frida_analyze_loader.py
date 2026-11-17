#!/usr/bin/env python3
"""分析游戏原生 AssetBundle 加载路径：静态反汇编 + 运行时调用追踪。

用法:
  py -3.12 scripts/frida_analyze_loader.py <PID> [--secs 20]
"""
from __future__ import annotations

import json
import sys
import time

import frida
from capstone import CS_ARCH_X86, CS_MODE_64, Cs

DUMP_CLASSES = ["lnepoeakhib", "pgohfpicjjd"]

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 attach:new NativeFunction(E('il2cpp_thread_attach'),'pointer',['pointer']),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']),
 cName:new NativeFunction(E('il2cpp_class_get_name'),'pointer',['pointer']),
 imgClassCount:new NativeFunction(E('il2cpp_image_get_class_count'),'uint',['pointer']),
 imgClass:new NativeFunction(E('il2cpp_image_get_class'),'pointer',['pointer','uint']),
 cType:new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']),
 tObj:new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '';return p.add(0x14).readUtf16String(p.add(0x10).readU32());}catch(e){return '';}}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null,abm=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.AssetBundleModule.dll')abm=im;}
try{f.attach(dom);}catch(e){}
// ---------- 1) 静态 dump ----------
function dumpClass(name){
 const k=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String(name));
 if(k.isNull()){send({log:'class '+name+' NOT FOUND'});return;}
 const it=Memory.alloc(P);it.writePointer(ptr(0));
 let idx=0;
 for(let j=0;j<400;j++){
  const mi=f.cMethods(k,it);if(mi.isNull())break;
  const mn=cs(f.mName(mi)),argc=f.mParamCount(mi);
  const mp=mi.readPointer(),inv=mi.add(P).readPointer();
  let target=(!mp.isNull()&&mp.compare(ptr(0x10000))>=0)?mp:inv;
  if(target.isNull())continue;
  const rva=target.sub(ga.base).toInt32();
  try{send({cls:name,idx:idx++,method:mn,argc:argc,rva:rva,mp:mp.toString(),inv:inv.toString()},Memory.readByteArray(target,640));}
  catch(e){send({cls:name,method:mn,err:''+e});}
 }
 send({log:'dumped '+name+' count='+idx});
}
for(const c of __CLASSES__)dumpClass(c);
// ---------- 2) 运行时 hook Unity 加载 API ----------
function hookLoad(clsImg,clsName,methName,wantArgc){
 if(clsImg.isNull())return;
 const k=f.fromName(clsImg,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String(clsName));
 if(k.isNull()){send({log:'no class '+clsName});return;}
 const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let j=0;j<400;j++){
  const mi=f.cMethods(k,it);if(mi.isNull())break;
  if(cs(f.mName(mi))!==methName)continue;
  if(wantArgc!==undefined&&f.mParamCount(mi)!==wantArgc)continue;
  const targets=[mi.readPointer(),mi.add(P).readPointer()];
  const seen=new Set();
  for(const t of targets){
   if(t.isNull()||t.compare(ptr(0x10000))<0)continue;
   const key=t.toString();if(seen.has(key))continue;seen.add(key);
   try{
    Interceptor.attach(t,{onEnter(a){
     let p='';
     try{p=ilstr(a[1]);}catch(e){}
     send({log:'[native] '+clsName+'.'+methName+'("'+p+'") argc='+f.mParamCount(mi)});
    }});
    send({log:'hooked '+clsName+'.'+methName+' @'+key});
   }catch(e){}
  }
 }
}
hookLoad(abm,'AssetBundle','LoadFromFile',1);
hookLoad(abm,'AssetBundle','LoadFromFileAsync',1);
hookLoad(abm,'AssetBundle','LoadAsset',1);
hookLoad(abm,'AssetBundle','LoadAssetAsync',1);
send({log:'ready'});
"""


def main() -> int:
    pid = int(sys.argv[1])
    secs = 20
    for i, a in enumerate(sys.argv):
        if a == "--secs":
            secs = float(sys.argv[i + 1])
    js = JS.replace("__CLASSES__", json.dumps(DUMP_CLASSES))
    s = frida.attach(pid)
    sc = s.create_script(js)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    dump = {}
    ga_base = None

    def on_msg(msg, data):
        nonlocal ga_base
        if msg.get("type") != "send":
            print("[err]", msg.get("description"))
            return
        p = msg.get("payload") or {}
        if "log" in p:
            print("[log]", p["log"])
            return
        if "rva" in p:
            lines = []
            base = int(p["rva"])
            if data:
                for ins in md.disasm(bytes(data), 0):
                    tag = ""
                    if ins.mnemonic in ("call", "jmp"):
                        t = ins.operands[0]
                        if t.type == 2:  # imm
                            tag = f"  -> +0x{t.imm:x}"
                        elif t.type == 3:  # mem
                            tag = f"  -> [{ins.op_str}]"
                    lines.append(f"0x{ins.address:04x}: {ins.mnemonic} {ins.op_str}{tag}")
            print(f"\n===== {p['cls']}::{p['method']} argc={p['argc']} rva=0x{p['rva']:x} mp={p['mp']} =====")
            print("\n".join(lines))

    sc.on("message", on_msg)
    sc.load()
    time.sleep(secs)
    s.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
