#!/usr/bin/env python3
"""探测 Shop 类型：字段偏移、方法、场景内现有实例。

用法: py -3.12 scripts/frida_shop_probe.py <PID>
"""
from __future__ import annotations

import json
import sys

import frida

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 cFields:new NativeFunction(E('il2cpp_class_get_fields'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 fName:new NativeFunction(E('il2cpp_field_get_name'),'pointer',['pointer']),
 fOff:new NativeFunction(E('il2cpp_field_get_offset'),'size_t',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']),
 invoke:new NativeFunction(E('il2cpp_runtime_invoke'),'pointer',['pointer','pointer','pointer','pointer']),
 isGeneric:new NativeFunction(E('il2cpp_method_is_generic'),'uint',['pointer']),
 cType:new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']),
 tObj:new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer']),
 clsName:new NativeFunction(E('il2cpp_class_get_name'),'pointer',['pointer']),
 fldType:new NativeFunction(E('il2cpp_field_get_type'),'pointer',['pointer']),
 tName:new NativeFunction(E('il2cpp_type_get_name'),'pointer',['pointer']),
 getParam:new NativeFunction(E('il2cpp_method_get_param'),'pointer',['pointer','uint'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '';return p.add(0x14).readUtf16String(p.add(0x10).readU32());}catch(e){return '';}}
const dom=f.dom();const cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;}
function findMethod(k,meth,argc){if(!k||k.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let i=0;i<800;i++){const mi=f.cMethods(k,it);if(mi.isNull())break;
  if(cs(f.mName(mi))===meth&&f.mParamCount(mi)===argc&&!f.isGeneric(mi))return mi;}return null;}
function inv(mi,obj,args){const exc=Memory.alloc(P);exc.writePointer(ptr(0));return f.invoke(mi,obj,args||ptr(0),exc);}
const SHOP=f.fromName(game,Memory.allocUtf8String('RF4.Client.FishingScene'),Memory.allocUtf8String('Shop'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const COMP=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Component'));
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const findObjs=findMethod(OBJ,'FindObjectsOfType',1);
const getName=findMethod(OBJ,'get_name',0);
const getGO=findMethod(COMP,'get_gameObject',0);
const TIME=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Time'));
const tickM=findMethod(TIME,'get_time',0)||findMethod(TIME,'get_realtimeSinceStartup',0);
send({log:'class shop='+(SHOP&&!SHOP.isNull())+' findObjs='+!!findObjs+' name='+!!getName+' getGO='+!!getGO});
if(SHOP&&!SHOP.isNull()){
 const fl=[];const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let i=0;i<120;i++){const fd=f.cFields(SHOP,it);if(fd.isNull())break;
  fl.push(cs(f.fName(fd))+'@'+f.fOff(fd)+':'+cs(f.tName(f.fldType(fd))));}
 send({log:'fields: '+fl.join(', ')});
 const ml=[];const mi=Memory.alloc(P);mi.writePointer(ptr(0));
 for(let i=0;i<200;i++){const m=f.cMethods(SHOP,mi);if(m.isNull())break;
  const pc=f.mParamCount(m);let ps=[];
  for(let k=0;k<pc;k++)ps.push(cs(f.tName(f.getParam(m,k))));
  ml.push(cs(f.mName(m))+'('+ps.join(',')+')');}
 send({log:'methods: '+ml.join(', ')});
 if(findObjs&&getName){
  const a=Memory.alloc(P);a.writePointer(f.tObj(f.cType(SHOP)));
  const arr=inv(findObjs,ptr(0),a);
  if(arr.isNull()){send({log:'FindObjectsOfType null'});}
  else{const len=arr.add(0x18).readU32();send({log:'instances='+len});
   for(let i=0;i<Math.min(len,8);i++){
    const o=arr.add(0x20+i*P).readPointer();const nm=ilstr(inv(getName,o,ptr(0)));
    let gnm='';try{const g=inv(getGO,o,ptr(0));if(!g.isNull())gnm=ilstr(inv(getName,g,ptr(0)));}catch(e){}
    const sid=ilstr(o.add(80).readPointer());const st=o.add(96).readInt();
    send({log:'  ['+i+'] sid='+sid+' type='+st+' comp='+nm+' go='+gnm});}
  }
 }
}
function once(){const m=new NativeFunction(tickM.add(P).readPointer(),'float',[]);let fired=false;
 Interceptor.attach(tickM.add(P).readPointer(),{onEnter(){if(fired)return;fired=true;setTimeout(()=>{send({log:'done'});},200);}});}
if(tickM)once();
"""
def main():
    pid = int(sys.argv[1])
    dev = frida.get_local_device()
    s = dev.attach(pid)
    sc = s.create_script(JS)
    def on_msg(m, d):
        if m.get("type") == "send":
            print(json.dumps(m["payload"], ensure_ascii=False), flush=True)
            if "done" in str(m["payload"]):
                s.detach()
        else:
            print(m, flush=True)
    sc.on("message", on_msg)
    sc.load()
    import time as _t
    _t.sleep(15)

if __name__ == "__main__":
    main()
