#!/usr/bin/env python3
"""反汇编原生 bundle 加载器方法（hex 传输 + capstone）。

用法: py -3.12 scripts/frida_disasm_loader.py <PID>
"""
from __future__ import annotations

import json
import sys
import time

import frida
from capstone import CS_ARCH_X86, CS_MODE_64, Cs

CLASSES = ["lnepoeakhib", "pgohfpicjjd"]
SIZE = 1400

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function hex(buf){const u=new Uint8Array(buf);let s='';for(let i=0;i<u.length;i++)s+=('0'+u[i].toString(16)).slice(-2);return s;}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a);if(cs(f.imgName(im))==='Assembly-CSharp.dll')game=im;}
send({log:'base='+ga.base});
for(const name of __CLASSES__){
 const k=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String(name));
 if(k.isNull()){send({log:'MISS '+name});continue;}
 const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let j=0;j<400;j++){
  const mi=f.cMethods(k,it);if(mi.isNull())break;
  let mn='',argc=0,mp=null,inv=null;
  try{mn=cs(f.mName(mi));argc=f.mParamCount(mi);mp=mi.readPointer();inv=mi.add(P).readPointer();}catch(e){send({cls:name,err:'readMethodInfo '+e});continue;}
  let t=mp;
  if(t.isNull()||t.compare(ptr(0x10000))<0)t=inv;
  if(t.isNull()||t.compare(ptr(0x10000))<0){send({cls:name,method:mn,argc:argc,rva:-1,hex:''});continue;}
  let rva=0,data='';
  try{rva=t.sub(ga.base).toInt32();}catch(e){}
  // 逐字节读，遇到不可读页就停，避免整块读取 EFAULT
  const bytes=[];
  for(let i=0;i<__SIZE__;i++){
   try{bytes.push(t.add(i).readU8());}catch(e){break;}
  }
  data=bytes.map(b=>('0'+b.toString(16)).slice(-2)).join('');
  send({cls:name,method:mn,argc:argc,rva:rva,mp:mp.toString(),inv:inv.toString(),hex:data});
 }
}
send({log:'done'});
"""


def main() -> int:
    pid = int(sys.argv[1])
    js = JS.replace("__CLASSES__", json.dumps(CLASSES)).replace("__SIZE__", str(SIZE))
    s = frida.attach(pid)
    sc = s.create_script(js)
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True

    def on_msg(msg, data):
        if msg.get("type") != "send":
            print("[err]", msg.get("description"))
            return
        p = msg.get("payload") or {}
        if "log" in p:
            print("[log]", p["log"])
            return
        if not p.get("hex"):
            print(f"\n===== {p.get('cls')}::{p.get('method')} rva={p.get('rva')} (no body) =====")
            return
        raw = bytes.fromhex(p["hex"])
        base = p["rva"] & 0xFFFFFFFF
        print(f"\n===== {p['cls']}::{p['method']} argc={p.get('argc')} rva=0x{base:x} =====")
        for ins in md.disasm(raw, base):
            extra = ""
            if ins.mnemonic in ("call", "jmp") and ins.operands:
                op = ins.operands[0]
                if op.type == 2:
                    extra = f"   ; -> 0x{op.imm:x}"
                elif op.type == 3:
                    extra = f"   ; -> [{ins.op_str}]"
            print(f"  0x{ins.address:x}: {ins.mnemonic:8s} {ins.op_str}{extra}")

    sc.on("message", on_msg)
    sc.load()
    time.sleep(4)
    s.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
