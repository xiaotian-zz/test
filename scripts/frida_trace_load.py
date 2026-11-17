#!/usr/bin/env python3
"""被动追踪原生 bundle 加载：hook gpdflailkgp / ghoioimpjia / LoadFromFileAsync。

用法: py -3.12 scripts/frida_trace_load.py <PID> [秒数]
期间在游戏里切换一次地图（或重启进图），即可看到原生拼出的完整路径。
"""
from __future__ import annotations

import json
import sys
import time

import frida

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 attach:new NativeFunction(E('il2cpp_thread_attach'),'pointer',['pointer'])};
try{f.attach(f.dom());}catch(e){}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '<null>';return p.add(0x14).readUtf16String(p.add(0x10).readU32());}catch(e){return '<err>';}}
function hookAt(rva,label,argIndex){
 const addr=ga.base.add(rva);
 try{
  Interceptor.attach(addr,{
   onEnter(a){this._n=ilstr(a[argIndex]);},
   onLeave(r){send({log:label+' ("'+this._n+'") => "'+ilstr(r)+'"'});}
  });
  send({log:'hooked '+label+' @'+addr});
 }catch(e){send({log:'hook fail '+label+' '+e});}
}
// gpdflailkgp(string name) 静态，rcx = name
hookAt(0x8ca200,'gpdflailkgp',0);
// ghoioimpjia(this, string name) 实例，rdx = name
hookAt(0x8ca480,'ghoioimpjia',1);
send({log:'ready - 请在游戏里切换地图'});
"""

pid = int(sys.argv[1])
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 180

s = frida.attach(pid)
sc = s.create_script(JS)
sc.on("message", lambda m, d: print(json.dumps(m.get("payload", m), ensure_ascii=False), flush=True))
sc.load()
try:
    time.sleep(secs)
finally:
    s.detach()
