#!/usr/bin/env python3
"""用 il2cpp_runtime_invoke 正确调用 Unity API 验证 AssetBundle 加载。

用法:
  py -3.12 scripts/frida_ab_test.py <PID> --path <bundle> [--asset 名字]
"""
from __future__ import annotations

import json
import sys
import time

import frida

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={
 dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 attach:new NativeFunction(E('il2cpp_thread_attach'),'pointer',['pointer']),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']),
 cName:new NativeFunction(E('il2cpp_class_get_name'),'pointer',['pointer']),
 classGetParent:new NativeFunction(E('il2cpp_class_get_parent'),'pointer',['pointer']),
 objGetClass:new NativeFunction(E('il2cpp_object_get_class'),'pointer',['pointer']),
 strNew:new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer']),
 imgClassCount:new NativeFunction(E('il2cpp_image_get_class_count'),'uint',['pointer']),
 imgClass:new NativeFunction(E('il2cpp_image_get_class'),'pointer',['pointer','uint']),
 invoke:new NativeFunction(E('il2cpp_runtime_invoke'),'pointer',['pointer','pointer','pointer','pointer']),
 gchNew:new NativeFunction(E('il2cpp_gchandle_new'),'uint',['pointer','int']),
 gchTgt:new NativeFunction(E('il2cpp_gchandle_get_target'),'pointer',['uint']),
 objNew:new NativeFunction(E('il2cpp_object_new'),'pointer',['pointer']),
 cType:new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']),
 tObj:new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null,abm=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.AssetBundleModule.dll')abm=im;}
function cls(img,ns,nm){return f.fromName(img,Memory.allocUtf8String(ns),Memory.allocUtf8String(nm));}
function methodOf(klass,name,argc){
 let k=klass;
 for(let d=0;d<8&&!k.isNull();d++){
  const it=Memory.alloc(P);it.writePointer(ptr(0));
  for(let j=0;j<600;j++){const mm=f.cMethods(k,it);if(mm.isNull())break;
   if(cs(f.mName(mm))===name&&f.mParamCount(mm)===argc)return mm;}
  k=f.classGetParent(k);
 }
 return null;
}
function call(mi,obj,args){
 const arr=Memory.alloc(P*Math.max(1,args.length));
 for(let i=0;i<args.length;i++)arr.add(i*P).writePointer(args[i]);
 const exc=Memory.alloc(P);
 const ret=f.invoke(mi,obj,arr,exc);
 return ret;
}
function boxInt(o){try{return o.isNull()?0:o.add(0x10).readS32();}catch(e){return 0;}}
const OBJ=cls(core,'UnityEngine','Object'),GO=cls(core,'UnityEngine','GameObject');
const TR=cls(core,'UnityEngine','Transform'),CAM=cls(core,'UnityEngine','Camera');
const AB=abm.isNull()?null:cls(abm,'UnityEngine','AssetBundle');
try{f.attach(dom);}catch(e){}
const m={loadFile:AB?methodOf(AB,'LoadFromFile',1):null,
 loadAsync:AB?methodOf(AB,'LoadAssetAsync',1):null,
 inst:methodOf(OBJ,'Instantiate',1),getT:methodOf(GO,'get_transform',0),setAct:methodOf(GO,'SetActive',1),
 camMain:methodOf(CAM,'get_main',0),
 gp:methodOf(TR,'get_position_Injected',1),fwd:methodOf(TR,'get_forward_Injected',1),
 sp:methodOf(TR,'set_position_Injected',1),sr:methodOf(TR,'set_rotation_Injected',1),gr:methodOf(TR,'get_rotation_Injected',1)};
send({log:'apis '+JSON.stringify({loadFile:!!m.loadFile,loadAsync:!!m.loadAsync,inst:!!m.inst,sp:!!m.sp})});
const PATH=__PATH__,ASSET=__ASSET__,DIST=__DIST__;
let fired=false,ready=false,winner=null,probes=[],st=0,hReq=0,hAsset=0,frames=0;
function step(){
 if(st===0){st=1;
  const p=f.strNew(Memory.allocUtf8String(PATH));
  const hp=f.gchNew(p,0);
  const r=call(m.loadFile,ptr(0),[f.gchTgt(hp)]);
  send({log:'LoadFromFile(invoke) -> '+(r.isNull()?'NULL':r)});
  if(!r.isNull()){hReq=f.gchNew(r,0);st=2;frames=0;}
  else st=9;
  return;}
 if(st===2){const b=f.gchTgt(hReq);
  send({log:'bundle ptr='+b});
  if(b.isNull()){send({log:'bundle handle lost'});st=9;return;}
  try{
   const nm=f.gchNew(f.strNew(Memory.allocUtf8String(ASSET)),0);
   const ar=call(m.loadAsync,b,[f.gchTgt(nm)]);
   send({log:'LoadAssetAsync -> '+(ar.isNull()?'NULL':ar)});
   if(ar.isNull()){st=9;return;}
   hAsset=f.gchNew(ar,0);st=3;frames=0;
  }catch(e){send({log:'loadAsync err '+e});st=9;}
  return;}
 if(st===3){frames++;
  const ar=f.gchTgt(hAsset);
  const dm=methodOf(f.objGetClass(ar),'get_isDone',0);
  const done=boxInt(call(dm,ar,[]));
  if(frames%30===0)send({log:'isDone='+done+' frame='+frames});
  if(!done)return;
  const ga=methodOf(f.objGetClass(ar),'get_asset',0);
  const asset=call(ga,ar,[]);
  send({log:'asset -> '+(asset.isNull()?'NULL':asset)});
  if(asset.isNull()){st=9;return;}
  const obj=call(m.inst,ptr(0),[asset]);
  send({log:'Instantiate -> '+(obj.isNull()?'NULL':obj)});
  if(obj.isNull()){st=9;return;}
  const t=call(m.getT,obj,[]);
  const cam=call(m.camMain,ptr(0),[]);
  if(!cam.isNull()&&m.gp&&m.fwd&&m.gr&&m.sp&&m.sr){
   const ct=call(m.getT,cam,[]);
   const cp=Memory.alloc(12),cf=Memory.alloc(12),cr=Memory.alloc(16);
   call(m.gp,ct,[cp]);call(m.fwd,ct,[cf]);call(m.gr,ct,[cr]);
   const pos=Memory.alloc(12);
   pos.writeFloat(cp.readFloat()+cf.readFloat()*DIST);
   pos.add(4).writeFloat(cp.add(4).readFloat()+cf.add(4).readFloat()*DIST-1.2);
   pos.add(8).writeFloat(cp.add(8).readFloat()+cf.add(8).readFloat()*DIST);
   call(m.sp,t,[pos]);call(m.sr,t,[cr]);
   send({log:'placed '+pos.readFloat().toFixed(1)+','+pos.add(4).readFloat().toFixed(1)+','+pos.add(8).readFloat().toFixed(1)});
  }
  const b1=Memory.alloc(1);b1.writeU8(1);
  call(m.setAct,obj,[b1]);
  send({log:'DONE'});
  st=4;return;}
}
function cleanup(){for(const p of probes){try{p.detach();}catch(e){}}probes.length=0;ready=true;
 try{probes.push(Interceptor.attach(winner,{onEnter(){if(st<4)step();}}));}catch(e){}
 send({log:'single hook ready'});}
const total=f.imgClassCount(game);let cntU=0;
for(let i=0;i<total;i++){
 const k=f.imgClass(game,i);if(k.isNull())continue;
 const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let j=0;j<800;j++){
  const mm=f.cMethods(k,it);if(mm.isNull())break;
  if(cs(f.mName(mm))!=='Update'||f.mParamCount(mm)!==0)continue;
  const mp=mm.add(P).readPointer();if(mp.isNull())continue;
  try{probes.push(Interceptor.attach(mp,{onEnter(){if(!fired){fired=true;winner=mp;setImmediate(cleanup);}else if(ready&&st<4)step();}}));cntU++;}catch(e){}
 }
}
send({log:'hooks '+cntU});
"""


def main() -> int:
    pid = int(sys.argv[1])
    path = "F:\\RF4\\Game\\rf4_x64_Data\\Data\\lures_wta"
    asset = "connector"
    dist = 6.0
    for i, a in enumerate(sys.argv):
        if a == "--path":
            path = sys.argv[i + 1]
        elif a == "--asset":
            asset = sys.argv[i + 1]
        elif a == "--dist":
            dist = float(sys.argv[i + 1])
    js = JS.replace("__PATH__", json.dumps(path)).replace("__ASSET__", json.dumps(asset)).replace("__DIST__", str(dist))
    s = frida.attach(pid)
    sc = s.create_script(js)
    sc.on("message", lambda m, d: print(json.dumps(m.get("payload", m), ensure_ascii=False)))
    sc.load()
    time.sleep(12)
    s.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
