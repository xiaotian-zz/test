#!/usr/bin/env python3
"""一次性加载 xmas_stalls.bundle，在相机前方实例化并检查结果。

用法:
  py -3.12 scripts/frida_load_bundle.py <PID> [--dist 6] [--no-mat]
"""
from __future__ import annotations

import json
import sys
import time

import frida

PATH = "F:\\rea\\artifacts\\xmas_stalls.bundle"
ASSET = "assets/rf4local/xmas_stalls.prefab"

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 attach:new NativeFunction(E('il2cpp_thread_attach'),'pointer',['pointer']),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cType:new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']),
 getParam:new NativeFunction(E('il2cpp_method_get_param'),'pointer',['pointer','uint']),
 typeName:new NativeFunction(E('il2cpp_type_get_name'),'pointer',['pointer']),
 tObj:new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer']),
 strNew:new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function findMethod(cls,name,argc){if(cls.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<700;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&(argc===undefined||f.mParamCount(m)===argc))return m.add(P).readPointer();}return null;}
function findMethodType(cls,name,argc,want){if(cls.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<700;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&f.mParamCount(m)===argc&&cs(f.typeName(f.getParam(m,0)))===want)return m.add(P).readPointer();}return null;}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null,abm=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.AssetBundleModule.dll')abm=im;}
function cls(ns,nm){return f.fromName(core,Memory.allocUtf8String(ns),Memory.allocUtf8String(nm));}
const GO=cls('UnityEngine','GameObject'),OBJ=cls('UnityEngine','Object'),TR=cls('UnityEngine','Transform');
const CAM=cls('UnityEngine','Camera'),TIME=cls('UnityEngine','Time');
const SHADER=cls('UnityEngine','Shader'),MATERIAL=cls('UnityEngine','Material'),REND=cls('UnityEngine','Renderer');
const COMP=cls('UnityEngine','Component');
const AB=abm.isNull()?null:f.fromName(abm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('AssetBundle'));
try{f.attach(dom);}catch(e){}
// MyProbe 补丁，避免进图时 UI 重建崩溃
let probe=false;
try{const MP=f.fromName(game,Memory.allocUtf8String('RF4.Client'),Memory.allocUtf8String('MyProbe'));
 if(!MP.isNull()){const mi=findMethod(MP,'mipcnipgejd',1);if(mi){Interceptor.replace(mi,new NativeCallback(function(){},'void',['pointer','int']));probe=true;}}}catch(e){}
const m={abLoad:findMethod(AB,'LoadFromFile',1),abAsset:findMethod(AB,'LoadAsset',2),
 inst:findMethod(OBJ,'Instantiate',1),destroy:findMethod(OBJ,'Destroy',1),
 getT:findMethod(GO,'get_transform',0),setAct:findMethod(GO,'SetActive',1),
 camMain:findMethod(CAM,'get_main',0),tick:findMethod(TIME,'get_time',0),
 gp:findMethod(TR,'get_position_Injected',1),fwd:findMethod(TR,'get_forward_Injected',1),
 sp:findMethod(TR,'set_position_Injected',1),sr:findMethod(TR,'set_rotation_Injected',1),gr:findMethod(TR,'get_rotation_Injected',1),
 getChild:findMethod(TR,'GetChild',1),childCount:findMethod(TR,'get_childCount',0),
 getGO:findMethod(TR,'get_gameObject',0),getComp:findMethodType(GO,'GetComponent',1,'System.Type'),
 getCompC:findMethodType(COMP,'GetComponent',1,'System.Type'),
 shFind:findMethod(SHADER,'Find',1),getShader:findMethod(MATERIAL,'get_shader',0),setShader:findMethod(MATERIAL,'set_shader',1),
 matCtor:findMethod(MATERIAL,'.ctor',1),setColor:findMethod(MATERIAL,'set_color',2),getColor:findMethod(MATERIAL,'get_color',0),
 getMat:findMethod(REND,'get_sharedMaterial',0),setMat:findMethod(REND,'set_sharedMaterial',1),
 getMats:findMethod(REND,'get_sharedMaterials',0),getName:findMethod(OBJ,'get_name',0)};
send({log:'probe='+probe+' apis='+JSON.stringify({load:!!m.abLoad,asset:!!m.abAsset,inst:!!m.inst,mat:!!m.matCtor,shader:!!m.shFind,rend:!!m.getMat})});
let fired=false;
const probes=[];
if(m.abLoad&&m.abAsset&&m.inst&&m.camMain&&m.tick){
 function V3(x,y,z){const p=Memory.alloc(12);p.writeFloat(x);p.add(4).writeFloat(y);p.add(8).writeFloat(z);return p;}
 function run(){
  if(fired)return;fired=true;
  try{const th=f.attach(dom);send({log:'attach '+(th.isNull()?'null':'ok')});}catch(e){send({log:'attach err '+e});}
  const t0=Date.now();
  let NFl,NFa,NFi,NFcam,NFgt,NFgp=null,NFfwd=null,NFgr=null,NFsp=null,NFsetr=null,NFact,NFcc,NFgc,NFgo;
  try{
  NFl=new NativeFunction(m.abLoad,'pointer',['pointer']);
  NFa=new NativeFunction(m.abAsset,'pointer',['pointer','pointer','pointer']);
  NFi=new NativeFunction(m.inst,'pointer',['pointer']);
  NFcam=new NativeFunction(m.camMain,'pointer',[]);
  NFgt=new NativeFunction(m.getT,'pointer',['pointer']);
  const camOk = m.gp && !m.gp.isNull() && m.fwd && !m.fwd.isNull() && m.gr && !m.gr.isNull();
  if(camOk){NFgp=new NativeFunction(m.gp,'void',['pointer','pointer']);NFfwd=new NativeFunction(m.fwd,'void',['pointer','pointer']);NFgr=new NativeFunction(m.gr,'void',['pointer','pointer']);}
  if(m.sp&&!m.sp.isNull())NFsp=new NativeFunction(m.sp,'void',['pointer','pointer']);
  if(m.sr&&!m.sr.isNull())NFsetr=new NativeFunction(m.sr,'void',['pointer','pointer']);
  send({log:'built basic setAct='+m.setAct+' cc='+m.childCount+' child='+m.getChild+' compC='+m.getCompC});
  NFact=new NativeFunction(m.setAct,'void',['pointer','int']);
  NFcc=new NativeFunction(m.childCount,'int',['pointer']);
  NFgc=new NativeFunction(m.getChild,'pointer',['pointer','int']);
  }catch(e){send({log:'construct err '+e});return;}
  send({log:'constructed'});

  let bundle=null;
  try{const sp=f.strNew(Memory.allocUtf8String('__PATH__'));send({log:'pathstr '+(sp.isNull()?'NULL':sp.add(0x14).readUtf16String(sp.add(0x10).readU32()))});bundle=NFl(sp);}catch(e){send({log:'load err '+e});return;}
  send({log:'LoadFromFile -> '+(bundle.isNull()?'NULL':'ok')});
  if(bundle.isNull())return;
  const asset=NFa(bundle,f.strNew(Memory.allocUtf8String('__ASSET__')),f.tObj(f.cType(GO)));
  send({log:'LoadAsset -> '+(asset.isNull()?'NULL':'ok')});
  if(asset.isNull())return;
  const obj=NFi(asset);
  send({log:'Instantiate -> '+(obj.isNull()?'NULL':'ok')});
  if(obj.isNull())return;

  const cam=NFcam();
  const t=NFgt(obj);
  if(!cam.isNull()&&camOk){
   const camT=NFgt(cam);
   const cp=Memory.alloc(12),cf=Memory.alloc(12),cr=Memory.alloc(16);
   NFgp(camT,cp);NFfwd(camT,cf);NFgr(camT,cr);
   const px=cp.readFloat(),py=cp.add(4).readFloat(),pz=cp.add(8).readFloat();
   const fx=cf.readFloat(),fy=cf.add(4).readFloat(),fz=cf.add(8).readFloat();
   const d=__DIST__;
   if(NFsp)NFsp(t,V3(px+fx*d,py+fy*d-1.2,pz+fz*d));
   if(NFsetr)NFsetr(t,cr);
  }else send({log:'camera unavailable, keep origin'});
  NFact(obj,1);

  // 统计渲染器并替换材质 shader
  let nRend=0,nSet=0,shaderOk=false;
  const NMmat=Memory.alloc(4);
  const std=m.shFind?new NativeFunction(m.shFind,'pointer',['pointer'])(f.strNew(Memory.allocUtf8String('Standard'))):ptr(0);
  shaderOk=!std.isNull();
  const NFcomp=(m.getCompC&&!m.getCompC.isNull())?new NativeFunction(m.getCompC,'pointer',['pointer','pointer']):null;
  const NFmatGet=(m.getMat&&!m.getMat.isNull())?new NativeFunction(m.getMat,'pointer',['pointer']):null;
  const NFmatCtor=(m.matCtor&&!m.matCtor.isNull())?new NativeFunction(m.matCtor,'pointer',['pointer']):null;
  const NFcolGet=(m.getColor&&!m.getColor.isNull())?new NativeFunction(m.getColor,'void',['pointer','pointer']):null;
  const NFcolSet=(m.setColor&&!m.setColor.isNull())?new NativeFunction(m.setColor,'void',['pointer','pointer']):null;
  const NFmatSet=(m.setMat&&!m.setMat.isNull())?new NativeFunction(m.setMat,'void',['pointer','pointer']):null;
  function walk(tr,depth){
   const cc=NFcc(tr);
   for(let i=0;i<cc;i++){
    const c=NFgc(tr,i);
    const comp=(NFcomp&&m.getCompC)?NFcomp(c,f.tObj(f.cType(REND))):ptr(0);
    if(!comp.isNull()&&comp.compare(ptr(0x10000))>=0){
     nRend++;
     if(__NOMAT__===0&&shaderOk&&NFmatGet&&NFmatCtor&&NFmatSet&&NFcolGet&&NFcolSet){
      const oldM=NFmatGet(comp);
      if(!oldM.isNull()&&oldM.compare(ptr(0x10000))>=0){
       const nm=NFmatCtor(std);
       if(!nm.isNull()&&nm.compare(ptr(0x10000))>=0){
        const col=Memory.alloc(16);
        NFcolGet(oldM,col);
        NFcolSet(nm,col);
        NFmatSet(comp,nm);
        nSet++;
       }
      }
     }
    }
    walk(c,depth+1);
   }
  }
  walk(t,0);
  send({log:'instantiated childCount='+NFcc(t)+' renderers='+nRend+' matSet='+nSet+' stdShader='+shaderOk+' ms='+(Date.now()-t0)});
 }
 // 备用钩子：Time.get_time
 try{probes.push(Interceptor.attach(m.tick,{onEnter(){if(!fired)run();}}));}catch(e){}
 // 主策略：hook Assembly-CSharp 所有无参 Update
 try{
  const getCls=new NativeFunction(E('il2cpp_image_get_class'),'pointer',['pointer','uint']);
  const cName=new NativeFunction(E('il2cpp_class_get_name'),'pointer',['pointer']);
  const cNs=new NativeFunction(E('il2cpp_class_get_namespace'),'pointer',['pointer']);
  const total=new NativeFunction(E('il2cpp_image_get_class_count'),'uint',['pointer'])(game);
  let cntUpd=0;
  for(let i=0;i<total;i++){
   const k=getCls(game,i);if(k.isNull())continue;
   const it=Memory.alloc(P);it.writePointer(ptr(0));
   for(let j=0;j<800;j++){
    const mm=f.cMethods(k,it);if(mm.isNull())break;
    if(cs(f.mName(mm))!=='Update'||f.mParamCount(mm)!==0)continue;
    let mp;try{mp=mm.add(P).readPointer();}catch(e){continue;}
    if(mp.isNull()||mp.compare(ptr(0x10000))<0)continue;
    try{probes.push(Interceptor.attach(mp,{onEnter(){if(!fired)run();}}));cntUpd++;}catch(e){}
   }
  }
  send({log:'update hooks='+cntUpd});
 }catch(e){send({log:'update scan fail '+e});}
 send({log:'hooked'});
}else send({log:'missing api'});
"""


def main() -> int:
    pid = int(sys.argv[1])
    dist = 6.0
    nomat = 0
    path = PATH
    asset = ASSET
    for i, a in enumerate(sys.argv):
        if a == "--dist":
            dist = float(sys.argv[i + 1])
        elif a == "--no-mat":
            nomat = 1
        elif a == "--path":
            path = sys.argv[i + 1]
        elif a == "--asset":
            asset = sys.argv[i + 1]
    js = JS.replace("__PATH__", path.replace("\\", "\\\\")).replace("__ASSET__", asset)
    js = js.replace("__DIST__", str(dist)).replace("__NOMAT__", str(nomat))
    s = frida.attach(pid)
    sc = s.create_script(js)
    sc.on("message", lambda m, d: print(json.dumps(m.get("payload", m), ensure_ascii=False)))
    sc.load()
    time.sleep(12)
    s.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
