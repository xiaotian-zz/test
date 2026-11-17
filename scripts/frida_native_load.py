#!/usr/bin/env python3
"""走游戏原生 AssetBundle 管理器加载本地 bundle（异步、分帧）。

用法:
  py -3.12 scripts/frida_native_load.py <PID> --probe
  py -3.12 scripts/frida_native_load.py <PID> [--asset CHRISTMAS] [--dist 6]
"""
from __future__ import annotations

import json
import sys
import time

import frida

BUNDLE = "F:\\rea\\artifacts\\xmas_stalls.bundle"
ASSET = "CHRISTMAS"

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={
 dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 attach:new NativeFunction(E('il2cpp_thread_attach'),'pointer',['pointer']),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cType:new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']),
 tObj:new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']),
 cName:new NativeFunction(E('il2cpp_class_get_name'),'pointer',['pointer']),
 cMethodByName:new NativeFunction(E('il2cpp_class_get_method_from_name'),'pointer',['pointer','pointer','int']),
 cFieldByName:new NativeFunction(E('il2cpp_class_get_field_from_name'),'pointer',['pointer','pointer']),
 fieldStaticGet:new NativeFunction(E('il2cpp_field_static_get_value'),'void',['pointer','pointer']),
 objGetClass:new NativeFunction(E('il2cpp_object_get_class'),'pointer',['pointer']),
 classGetParent:new NativeFunction(E('il2cpp_class_get_parent'),'pointer',['pointer']),
 strNew:new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer']),
 imgClassCount:new NativeFunction(E('il2cpp_image_get_class_count'),'uint',['pointer']),
 imgClass:new NativeFunction(E('il2cpp_image_get_class'),'pointer',['pointer','uint'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull()||p.compare(ptr(0x10000))<0)return '';return p.add(0x14).readUtf16String(p.add(0x10).readU32());}catch(e){return '';}}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
const gchNew=new NativeFunction(E('il2cpp_gchandle_new'),'uint',['pointer','int']);
const gchTgt=new NativeFunction(E('il2cpp_gchandle_get_target'),'pointer',['uint']);
let game=null,core=null,abm=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.AssetBundleModule.dll')abm=im;}
function cls(img,ns,nm){return f.fromName(img,Memory.allocUtf8String(ns),Memory.allocUtf8String(nm));}
function mptr(mi){return mi.readPointer();}                 // MethodInfo::methodPointer
function mInv(mi){return mi.add(P).readPointer();}           // MethodInfo::invoker_method
function mv(mi){const p=mptr(mi);return (p.isNull()||p.compare(ptr(0x10000))<0)?mInv(mi):p;}
function methodOf(klass,name,argc){
 let k=klass;
 for(let d=0;d<8&&!k.isNull();d++){
  const it=Memory.alloc(P);it.writePointer(ptr(0));
  for(let j=0;j<600;j++){
   const mm=f.cMethods(k,it);
   if(mm.isNull())break;
   if(cs(f.mName(mm))===name&&f.mParamCount(mm)===argc)return mm;
  }
  k=f.classGetParent(k);
 }
 return null;
}
const GO=cls(core,'UnityEngine','GameObject'),TR=cls(core,'UnityEngine','Transform'),OBJ=cls(core,'UnityEngine','Object');
const CAM=cls(core,'UnityEngine','Camera'),AOP=cls(core,'UnityEngine','AsyncOperation');
const ABR=abm.isNull()?null:cls(abm,'UnityEngine','AssetBundleRequest');
const ABCR=abm.isNull()?null:cls(abm,'UnityEngine','AssetBundleCreateRequest');
const AB=abm.isNull()?null:cls(abm,'UnityEngine','AssetBundle');
const CM=cls(game,'RF4.Client','Common'); // 占位
const LOADER=cls(game,'','pgohfpicjjd');
try{f.attach(dom);}catch(e){}
send({log:'loader class '+(LOADER.isNull()?'NULL':'ok')+' AB='+(AB&&!AB.isNull()?'ok':'NULL')});
let singleton=ptr(0),gpd=null;
if(!LOADER.isNull()){
 try{
  const fld=f.cFieldByName(LOADER,Memory.allocUtf8String('hfcggegmohh'));
  send({log:'field hfcggegmohh '+(fld.isNull()?'NULL':'ok')});
  if(!fld.isNull()){const buf=Memory.alloc(8);f.fieldStaticGet(fld,buf);singleton=buf.readPointer();send({log:'singleton '+(singleton.isNull()?'NULL':singleton)});}
  const gm=methodOf(LOADER,'gpdflailkgp',1);
  if(gm){gpd=new NativeFunction(mv(gm),'pointer',['pointer','pointer']);send({log:'gpdflailkgp ok'});}else send({log:'gpdflailkgp missing'});
 }catch(e){send({log:'loader err '+e});}
}
const m={
 inst:methodOf(OBJ,'Instantiate',1), getT:methodOf(GO,'get_transform',0),
 setAct:methodOf(GO,'SetActive',1), camMain:methodOf(CAM,'get_main',0),
 gp:methodOf(TR,'get_position_Injected',1), fwd:methodOf(TR,'get_forward_Injected',1),
 sp:methodOf(TR,'set_position_Injected',1), sr:methodOf(TR,'set_rotation_Injected',1), gr:methodOf(TR,'get_rotation_Injected',1),
 loadAsync:AB&&!AB.isNull()?methodOf(AB,'LoadAssetAsync',1):null,
 loadFile:AB&&!AB.isNull()?methodOf(AB,'LoadFromFile',1):null,
 loadFileAsync:AB&&!AB.isNull()?methodOf(AB,'LoadFromFileAsync',1):null,
 getAsset:null, getBundle:null,
 isDone:!AOP.isNull()?methodOf(AOP,'get_isDone',0):null};
send({log:'apis '+JSON.stringify({gh:!!(singleton&&!singleton.isNull()),inst:!!m.inst,loadAsync:!!m.loadAsync,sp:!!m.sp,isDone:!!m.isDone})});
const PROBE=__PROBE__,DIST=__DIST__,ASSET=__ASSET__,PATH=__PATH__,SYNC=__SYNC__;
let fired=false,ready=false,winner=null,probes=[],st=0,req=null,bundle=null,areq=null,fail='',hReq=0,hBundle=0,hAreq=0,frames=0,dbg1=false;
function step(){
 if(st===0){
  st=1;
  if(PROBE){
   if(gpd&&singleton&&!singleton.isNull()){
    const s=gpd(singleton,f.strNew(Memory.allocUtf8String(PATH)));
    send({log:'gpdflailkgp -> '+(s.isNull()?'NULL':ilstr(s))});
   }
   return;
  }
  const p=f.strNew(Memory.allocUtf8String(PATH));
  if(SYNC&&m.loadFile){
   const sb=new NativeFunction(mv(m.loadFile),'pointer',['pointer'])(p);
   send({log:'sync LoadFromFile -> '+(sb.isNull()?'NULL':sb)+' mi='+m.loadFile+' mp='+mv(m.loadFile)});
   if(!sb.isNull()){bundle=sb;hBundle=gchNew(sb,0);st=2;
    areq=new NativeFunction(mv(m.loadAsync),'pointer',['pointer','pointer'])(sb,f.strNew(Memory.allocUtf8String(ASSET)));
    if(areq&&!areq.isNull())hAreq=gchNew(areq,0);
    send({log:'LoadAssetAsync -> '+(areq.isNull()?'NULL':'ok')});}
   else st=9;
   return;
  }
  if(gpd&&singleton&&!singleton.isNull()){
   const gm=methodOf(f.objGetClass(singleton),'ghoioimpjia',1);
   if(gm){req=new NativeFunction(mv(gm),'pointer',['pointer','pointer'])(singleton,p);send({log:'native ghoioimpjia -> '+(req.isNull()?'NULL':'ok')});}
   else send({log:'ghoioimpjia missing on '+cs(f.imgName(game))});
  }
  if(!req||req.isNull()){
   req=new NativeFunction(mv(m.loadFileAsync),'pointer',['pointer'])(p);
   send({log:'fallback LoadFromFileAsync -> '+(req.isNull()?'NULL':'ok')});
  }
  if(req&&!req.isNull())hReq=gchNew(req,0);
  return;
 }
 if(st===1){
  req=hReq?gchTgt(hReq):ptr(0);
  frames++;
  const dm=methodOf(f.objGetClass(req),'get_isDone',0);
  if(!dbg1){dbg1=true;send({log:'dbg req='+req+' isDoneMi='+dm+' mp='+(dm?mv(dm):'-')+' val='+(dm?(new NativeFunction(mv(dm),'int',['pointer'])(req)):'-')});}
  if(frames<20)return;
  const k=getKeep();
  if(k<0){st=9;fail='no keepWaiting';send({log:fail});return;}
  if(k>0)return;
  if(singleton&&!singleton.isNull()&&!req.isNull()){
   const dm=methodOf(f.objGetClass(req),'ddkbjcdpelm',0);
   if(dm){bundle=new NativeFunction(mv(dm),'pointer',['pointer'])(req);}
  }
  if(!bundle||bundle.isNull()){
   const bm=methodOf(f.objGetClass(req),'get_assetBundle',0);
   if(bm)bundle=new NativeFunction(mv(bm),'pointer',['pointer'])(req);
  }
  send({log:'bundle -> '+(bundle&&!bundle.isNull()?'ok':'NULL')});
  if(!bundle||bundle.isNull()){st=9;return;}
  hBundle=gchNew(bundle,0);
  areq=new NativeFunction(mv(m.loadAsync),'pointer',['pointer','pointer'])(bundle,f.strNew(Memory.allocUtf8String(ASSET)));
  if(areq&&!areq.isNull())hAreq=gchNew(areq,0);
  send({log:'LoadAssetAsync -> '+(areq.isNull()?'NULL':'ok')});
  st=2;return;
 }
 if(st===2){
  areq=hAreq?gchTgt(hAreq):ptr(0);
  const d=new NativeFunction(mv(methodOf(f.objGetClass(areq),'get_isDone',0)||m.isDone),'int',['pointer'])(areq);
  if(d===0)return;
  const ga=methodOf(f.objGetClass(areq),'get_asset',0);
  if(!ga){st=9;send({log:'no get_asset'});return;}
  const asset=new NativeFunction(mv(ga),'pointer',['pointer'])(areq);
  send({log:'asset -> '+(asset.isNull()?'NULL':'ok')});
  if(asset.isNull()){st=9;return;}
  const obj=new NativeFunction(mv(m.inst),'pointer',['pointer'])(asset);
  send({log:'Instantiate -> '+(obj.isNull()?'NULL':'ok')});
  if(obj.isNull()){st=9;return;}
  const t=new NativeFunction(mv(m.getT),'pointer',['pointer'])(obj);
  if(m.camMain&&m.gp&&m.fwd&&m.gr&&m.sp&&m.sr){
   const cam=new NativeFunction(mv(m.camMain),'pointer',[])();
   if(!cam.isNull()){
    const ct=new NativeFunction(mv(m.getT),'pointer',['pointer'])(cam);
    const cp=Memory.alloc(12),cf=Memory.alloc(12),cr=Memory.alloc(16);
    new NativeFunction(mv(m.gp),'void',['pointer','pointer'])(ct,cp);
    new NativeFunction(mv(m.fwd),'void',['pointer','pointer'])(ct,cf);
    new NativeFunction(mv(m.gr),'void',['pointer','pointer'])(ct,cr);
    const pos=Memory.alloc(12);
    pos.writeFloat(cp.readFloat()+cf.readFloat()*DIST);
    pos.add(4).writeFloat(cp.add(4).readFloat()+cf.add(4).readFloat()*DIST-1.2);
    pos.add(8).writeFloat(cp.add(8).readFloat()+cf.add(8).readFloat()*DIST);
    new NativeFunction(mv(m.sp),'void',['pointer','pointer'])(t,pos);
    new NativeFunction(mv(m.sr),'void',['pointer','pointer'])(t,cr);
    send({log:'placed at '+pos.readFloat().toFixed(1)+','+pos.add(4).readFloat().toFixed(1)+','+pos.add(8).readFloat().toFixed(1)});
   }else send({log:'no camera'});
  }
  new NativeFunction(mv(m.setAct),'void',['pointer','int'])(obj,1);
  send({log:'DONE'});
  st=3;return;
 }
}
function getKeep(){
 if(!req||req.isNull())return -1;
 const k=f.objGetClass(req);
 const km=methodOf(k,'get_keepWaiting',0);
 if(km)return new NativeFunction(mv(km),'int',['pointer'])(req)&0xff;
 const dm=methodOf(k,'get_isDone',0);
 if(dm)return (new NativeFunction(mv(dm),'int',['pointer'])(req)&0xff)?0:1;
 return -1;
}
function cleanup(){
 for(const p of probes){try{p.detach();}catch(e){}}
 probes.length=0;
 ready=true;
 try{probes.push(Interceptor.attach(winner,{onEnter(){if(st<3)step();}}));}catch(e){send({log:'reattach err '+e});}
 send({log:'cleaned, single hook ready'});
}
function hookOne(mp){
 try{probes.push(Interceptor.attach(mp,{onEnter(){if(!fired){fired=true;winner=mp;setImmediate(cleanup);}else if(ready&&st<3)step();}}));}catch(e){}
}
if(m.inst&&m.loadAsync&&m.loadFileAsync&&m.sp){
 const total=f.imgClassCount(game);
 let cntU=0;
 for(let i=0;i<total;i++){
  const k=f.imgClass(game,i);if(k.isNull())continue;
  const it=Memory.alloc(P);it.writePointer(ptr(0));
  for(let j=0;j<800;j++){
   const mm=f.cMethods(k,it);if(mm.isNull())break;
   if(cs(f.mName(mm))!=='Update'||f.mParamCount(mm)!==0)continue;
   const mp=mInv(mm);if(mp.isNull()||mp.compare(ptr(0x10000))<0)continue;
   hookOne(mp);cntU++;
  }
 }
 send({log:'hooks '+cntU});
}else send({log:'missing core api'});
"""


def main() -> int:
    pid = int(sys.argv[1])
    probe = "--probe" in sys.argv
    asset = ASSET
    dist = 6.0
    for i, a in enumerate(sys.argv):
        if a == "--asset":
            asset = sys.argv[i + 1]
        elif a == "--dist":
            dist = float(sys.argv[i + 1])
    js = JS.replace("__PROBE__", "1" if probe else "0").replace("__DIST__", str(dist))
    js = js.replace("__SYNC__", "1" if "--sync" in sys.argv else "0")
    js = js.replace("__ASSET__", json.dumps(asset)).replace("__PATH__", json.dumps(BUNDLE))
    s = frida.attach(pid)
    sc = s.create_script(js)
    sc.on("message", lambda m, d: print(json.dumps(m.get("payload", m), ensure_ascii=False)))
    sc.load()
    time.sleep(10)
    s.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
