#!/usr/bin/env python3
"""读取当前相机世界坐标和朝向。用法: py -3.12 scripts/frida_campos.py <PID>"""
import json
import sys
import time

import frida

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']),
 invoke:new NativeFunction(E('il2cpp_runtime_invoke'),'pointer',['pointer','pointer','pointer','pointer']),
 isGeneric:new NativeFunction(E('il2cpp_method_is_generic'),'uint',['pointer'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
const dom=f.dom();const cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let core=null;for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a);if(cs(f.imgName(im))==='UnityEngine.CoreModule.dll')core=im;}
function findMethod(k,meth,argc){const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let i=0;i<800;i++){const mi=f.cMethods(k,it);if(mi.isNull())break;
  if(cs(f.mName(mi))===meth&&f.mParamCount(mi)===argc&&!f.isGeneric(mi))return mi;}return null;}
function inv(mi,obj,args){const exc=Memory.alloc(P);exc.writePointer(ptr(0));return f.invoke(mi,obj,args||ptr(0),exc);}
const CAM=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Camera'));
const COMP=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Component'));
const TR=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Transform'));
const camMain=findMethod(CAM,'get_main',0),getTc=findMethod(COMP,'get_transform',0);
const getPosI=findMethod(TR,'get_position_Injected',1),getFwdI=findMethod(TR,'get_forward_Injected',1);
try{
 send({log:'api cam='+!!camMain+' tc='+!!getTc+' pos='+!!getPosI+' fwd='+!!getFwdI+' camCls='+!!CAM+' compCls='+!!COMP});
 if(!camMain||!getTc||!getPosI){send({log:'api missing'});}
 else{
 const cam=inv(camMain,ptr(0),ptr(0));
 if(cam.isNull()){send({log:'no camera'});}else{
  const t=inv(getTc,cam,ptr(0));
  const p=Memory.alloc(12),a=Memory.alloc(P);a.writePointer(p);inv(getPosI,t,a);
  send({log:'pos='+p.readFloat().toFixed(2)+','+p.add(4).readFloat().toFixed(2)+','+p.add(8).readFloat().toFixed(2)});
 }
 }
}catch(e){send({log:'err '+e});}
"""

pid = int(sys.argv[1])
s = frida.get_local_device().attach(pid)
sc = s.create_script(JS)
sc.on("message", lambda m, d: print(json.dumps(m.get("payload") if m.get("type") == "send" else m, ensure_ascii=False)))
sc.load()
time.sleep(4)
s.detach()
