#!/usr/bin/env python3
"""Frida 运行时内存注入：用导出的 OBJ/PNG 在游戏里重建活动物件。

用法:
  py -3.12 scripts/frida_export_inject.py [PID]

流程: Python 把 OBJ 转成紧凑二进制(vcount,tcount,pos,uv,idx)，JS 在主线程
(Time.get_time hook) 里 new Mesh + 数组 memcpy + Texture2D.LoadImage + GameObject。
"""
from __future__ import annotations

import json
import os
import struct
import sys

import frida

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT = os.path.join(ROOT, "artifacts", "xmas_export")
WORK = os.path.join(ROOT, "artifacts", "inject")

# 第一批：level26 圣诞树
MESH_NAME = "christmas_tree_LOD0"
OBJ = os.path.join(EXPORT, "christmas_tree_LOD0.obj")
PNG = os.path.join(EXPORT, "christmas_tree_LOD0_christmas_tree_Atlas.png")
POS = (232.71, 2.02, 156.78)
YAW = 90.7
SCALE = 1.0
BIN = os.path.join(WORK, "tree.bin")

JS_TMPL = r"""
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
 tObj:new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer']),
 strNew:new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer']),
 getParam:new NativeFunction(E('il2cpp_method_get_param'),'pointer',['pointer','uint']),
 typeName:new NativeFunction(E('il2cpp_type_get_name'),'pointer',['pointer']),
 objNew:new NativeFunction(E('il2cpp_object_new'),'pointer',['pointer']),
 arrClass:new NativeFunction(E('il2cpp_array_class_get'),'pointer',['pointer','int']),
 arrNew:new NativeFunction(E('il2cpp_array_new'),'pointer',['pointer','uint64'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function findMethod(cls,name,argc){if(cls.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<600;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&(argc===undefined||f.mParamCount(m)===argc))return m.add(P).readPointer();}return null;}
function findMethodType(cls,name,argc,want){if(cls.isNull())return null;const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<600;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&f.mParamCount(m)===argc&&cs(f.typeName(f.getParam(m,0)))===want)return m.add(P).readPointer();}return null;}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null,imgm=null,mscor=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
 if(nm==='Assembly-CSharp.dll')game=im;if(nm==='UnityEngine.CoreModule.dll')core=im;if(nm==='UnityEngine.ImageConversionModule.dll')imgm=im;
 if(nm==='mscorlib.dll'||nm==='System.Private.CoreLib.dll')mscor=im;}
function cls(ns,nm){return f.fromName(core,Memory.allocUtf8String(ns),Memory.allocUtf8String(nm));}
const GO=cls('UnityEngine','GameObject'),OBJ=cls('UnityEngine','Object'),TR=cls('UnityEngine','Transform');
const TIME=cls('UnityEngine','Time'),MESH=cls('UnityEngine','Mesh'),MATERIAL=cls('UnityEngine','Material');
const SHADER=cls('UnityEngine','Shader'),TEX=cls('UnityEngine','Texture2D');
const MF=cls('UnityEngine','MeshFilter'),MR=cls('UnityEngine','MeshRenderer'),REND=cls('UnityEngine','Renderer');
const V3=cls('UnityEngine','Vector3'),V2=cls('UnityEngine','Vector2');
const I32=mscor.isNull()?f.fromName(core,Memory.allocUtf8String('System'),Memory.allocUtf8String('Int32')):f.fromName(mscor,Memory.allocUtf8String('System'),Memory.allocUtf8String('Int32'));
const BYTE=mscor.isNull()?f.fromName(core,Memory.allocUtf8String('System'),Memory.allocUtf8String('Byte')):f.fromName(mscor,Memory.allocUtf8String('System'),Memory.allocUtf8String('Byte'));
const IMGCONV=imgm.isNull()?null:f.fromName(imgm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('ImageConversion'));
const IOFILE=mscor.isNull()?null:f.fromName(mscor,Memory.allocUtf8String('System.IO'),Memory.allocUtf8String('File'));
const m={
 meshCtor:findMethod(MESH,'.ctor',0),setV:findMethod(MESH,'set_vertices',1),setUV:findMethod(MESH,'set_uv',1),
 setT:findMethod(MESH,'set_triangles',1),recN:findMethod(MESH,'RecalculateNormals',0),recB:findMethod(MESH,'RecalculateBounds',0),
 goCtor:findMethod(GO,'.ctor',1),addComp:findMethodType(GO,'AddComponent',1,'System.Type'),
 getT:findMethod(GO,'get_transform',0),setPos:findMethod(TR,'set_position_Injected',1),setRot:findMethod(TR,'set_rotation_Injected',1),
 mfSet:findMethod(MF,'set_mesh',1),mrSet:findMethod(REND,'set_sharedMaterial',1),
 matCtor:findMethod(MATERIAL,'.ctor',1),matTex:findMethod(MATERIAL,'set_mainTexture',1),
 shFind:findMethod(SHADER,'Find',1),texCtor:findMethod(TEX,'.ctor',4),texCtor2:findMethod(TEX,'.ctor',2),
 loadImg:IMGCONV?findMethod(IMGCONV,'LoadImage',2):null,
 readAll:IOFILE?findMethod(IOFILE,'ReadAllBytes',1):null,
 memcpy:(function(){for(const mn of ['msvcrt.dll','ucrtbase.dll','kernel32.dll']){try{const mod=Process.getModuleByName(mn);const e=mod.getExportByName(mn==='kernel32.dll'?'RtlMoveMemory':'memcpy');return new NativeFunction(e,'pointer',['pointer','pointer','uint64']);}catch(e){}}return null;})(),
 tick:['get_deltaTime','get_time','get_realtimeSinceStartup','get_unscaledDeltaTime','get_smoothDeltaTime','get_timeSinceLevelLoad'].map(n=>findMethod(TIME,n,0)).filter(Boolean),
 setFloat:findMethod(MATERIAL,'SetFloat',2),setInt:findMethod(MATERIAL,'SetInt',2),kw:findMethod(MATERIAL,'EnableKeyword',1)};
const flags={};for(const k in m)flags[k]=!!m[k];
send({log:'apis '+JSON.stringify(flags)});
send({log:'cls '+JSON.stringify({core:!core.isNull(),img:!imgm.isNull(),GO:!GO.isNull(),MESH:!MESH.isNull(),MATERIAL:!MATERIAL.isNull(),TEX:!TEX.isNull(),V3:!V3.isNull(),V2:!V2.isNull(),I32:!I32.isNull(),BYTE:!BYTE.isNull(),MF:!MF.isNull(),MR:!MR.isNull()})});
function V3P(x,y,z){const p=Memory.alloc(12);p.writeFloat(x);p.add(4).writeFloat(y);p.add(8).writeFloat(z);return p;}
let done=false;
if(m.tick&&m.tick.length&&m.meshCtor&&m.setV&&m.setT&&m.goCtor&&m.addComp&&m.mfSet&&m.mrSet&&m.matCtor&&m.shFind&&m.texCtor&&m.loadImg&&m.setPos&&m.getT&&m.recN&&m.recB&&m.readAll&&m.memcpy){
 try{f.attach(dom);}catch(e){}
 function spawn(){
  if(done)return;done=true;
  send({log:'spawn tid='+Process.getCurrentThreadId()});
  try{
   const VC=__VC__,TC=__TC__;
   send({log:'arr alloc'});
   const posArr=f.arrNew(f.arrClass(V3,1),VC), uvArr=f.arrNew(f.arrClass(V2,1),VC), triArr=f.arrNew(f.arrClass(I32,1),TC*3);
   send({log:'arr ok '+posArr+' '+uvArr+' '+triArr});
   const blob=new NativeFunction(m.readAll,'pointer',['pointer'])(f.strNew(Memory.allocUtf8String('__BIN__')));
   if(blob.isNull()||blob.compare(ptr(0x10000))<0){send({log:'read bin fail'});return;}
   send({log:'blob '+blob});
   // 注意: 托管数组数据在 +0x20, bin 文件本身还有 8 字节头(vcount,tcount)
   const src=blob.add(0x28);
   m.memcpy(posArr.add(0x20),src,VC*12);
   m.memcpy(uvArr.add(0x20),src.add(VC*12),VC*8);
   m.memcpy(triArr.add(0x20),src.add(VC*20),TC*12);
   let maxI=0,minI=1e9;
   for(let i=0;i<TC*3;i++){const v=triArr.add(0x20).add(i*4).readS32();if(v>maxI)maxI=v;if(v<minI)minI=v;}
   send({log:'data copied v0='+src.readFloat().toFixed(2)+','+src.add(4).readFloat().toFixed(2)+','+src.add(8).readFloat().toFixed(2)+' i['+minI+','+maxI+']'});
   const mesh=f.objNew(MESH);new NativeFunction(m.meshCtor,'void',['pointer'])(mesh);
   send({log:'mesh ctor '+mesh});
   new NativeFunction(m.setV,'void',['pointer','pointer'])(mesh,posArr);
   new NativeFunction(m.setUV,'void',['pointer','pointer'])(mesh,uvArr);
   new NativeFunction(m.setT,'void',['pointer','pointer'])(mesh,triArr);
   send({log:'channels set'});
   new NativeFunction(m.recN,'void',['pointer'])(mesh);
   new NativeFunction(m.recB,'void',['pointer'])(mesh);
   send({log:'mesh ok v='+VC+' t='+TC});
   // 贴图
   const png=new NativeFunction(m.readAll,'pointer',['pointer'])(f.strNew(Memory.allocUtf8String('__PNG__')));
   let tex=ptr(0),mat=ptr(0);
   if(__USE_TEX__&&!m.texCtor.isNull()&&(png.isNull()===false)&&png.compare(ptr(0x10000))>=0){
    const t=f.objNew(TEX);
    try{new NativeFunction(m.texCtor,'void',['pointer','int','int','int','int'])(t,4,4,4,0);}
    catch(e){if(m.texCtor2)new NativeFunction(m.texCtor2,'void',['pointer','int','int'])(t,4,4);}
    try{const ok=new NativeFunction(m.loadImg,'int',['pointer','pointer'])(t,png);send({log:'loadimage '+ok});}catch(e){send({log:'loadimage err '+e});}
    tex=t;
   }
   let sh=ptr(0),shname='';
   for(const nm of ['Standard','Legacy Shaders/Diffuse','Unlit/Texture','Sprites/Default']){
    const s=new NativeFunction(m.shFind,'pointer',['pointer'])(f.strNew(Memory.allocUtf8String(nm)));
    if(!s.isNull()&&s.compare(ptr(0x10000))>=0){sh=s;shname=nm;break;}
   }
   send({log:'shader '+shname});
   if(!sh.isNull()){
    mat=f.objNew(MATERIAL);new NativeFunction(m.matCtor,'void',['pointer','pointer'])(mat,sh);
    if(!tex.isNull()&&m.matTex)new NativeFunction(m.matTex,'void',['pointer','pointer'])(mat,tex);
    if(shname==='Standard'&&m.setFloat){
     try{const sf=new NativeFunction(m.setFloat,'void',['pointer','pointer','float']);
      sf(mat,f.strNew(Memory.allocUtf8String('_Mode')),1);
      sf(mat,f.strNew(Memory.allocUtf8String('_Cutoff')),0.5);
      const si=new NativeFunction(m.setInt,'void',['pointer','pointer','int']);
      si(mat,f.strNew(Memory.allocUtf8String('_SrcBlend')),1);
      si(mat,f.strNew(Memory.allocUtf8String('_DstBlend')),0);
      si(mat,f.strNew(Memory.allocUtf8String('_ZWrite')),1);
      new NativeFunction(m.kw,'void',['pointer','pointer'])(mat,f.strNew(Memory.allocUtf8String('_ALPHATEST_ON')));
     }catch(e){send({log:'alpha setup err '+e});}
    }
   }
   // 物件
   const go=f.objNew(GO);new NativeFunction(m.goCtor,'void',['pointer','pointer'])(go,f.strNew(Memory.allocUtf8String('__NAME__')));
   const t=new NativeFunction(m.getT,'pointer',['pointer'])(go);
   new NativeFunction(m.setPos,'void',['pointer','pointer'])(t,V3P(__PX__,__PY__,__PZ__));
   const yaw=__YAW__*Math.PI/180, q=Memory.alloc(16);
   q.writeFloat(0);q.add(4).writeFloat(Math.sin(yaw/2));q.add(8).writeFloat(0);q.add(12).writeFloat(Math.cos(yaw/2));
   new NativeFunction(m.setRot,'void',['pointer','pointer'])(t,q);
   const mf=new NativeFunction(m.addComp,'pointer',['pointer','pointer'])(go,f.tObj(f.cType(MF)));
   if(!mf.isNull()&&mf.compare(ptr(0x10000))>=0)new NativeFunction(m.mfSet,'void',['pointer','pointer'])(mf,mesh);
   const mr=new NativeFunction(m.addComp,'pointer',['pointer','pointer'])(go,f.tObj(f.cType(MR)));
   if(!mr.isNull()&&!mat.isNull())new NativeFunction(m.mrSet,'void',['pointer','pointer'])(mr,mat);
   send({log:'spawned __NAME__ mf='+(!mf.isNull())+' mr='+(!mr.isNull())+' at __PX__,__PY__,__PZ__'});
  }catch(e){send({log:'EXC '+e+'\n'+e.stack});}
 }
 for(let hi=0;hi<m.tick.length;hi++){Interceptor.attach(m.tick[hi],{onEnter(){spawn();}});}
 send({log:'hooked x'+m.tick.length});
}else send({log:'api missing '+JSON.stringify(flags)});
"""


def build_bin(obj_path: str, out_path: str) -> tuple[int, int]:
    verts: list[tuple[float, float, float]] = []
    uvs: list[tuple[float, float]] = []
    faces: list[str] = []
    with open(obj_path, "r", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("v "):
                p = line.split()
                verts.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith("vt "):
                p = line.split()
                uvs.append((float(p[1]), float(p[2])))
            elif line.startswith("f "):
                faces.append(line.strip()[2:])

    key_map: dict[tuple[int, int], int] = {}
    order: list[tuple[int, int]] = []
    indices: list[int] = []
    for face in faces:
        for tok in face.split():
            parts = tok.split("/")
            vi = int(parts[0]) - 1
            ti = int(parts[1]) - 1 if len(parts) > 1 and parts[1] else -1
            k = (vi, ti)
            if k not in key_map:
                key_map[k] = len(order)
                order.append(k)
            indices.append(key_map[k])

    if not uvs:  # 没有 vt 时全 0
        uvs = [(0.0, 0.0)] * len(verts)
    vc, tc = len(order), len(indices) // 3
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as fh:
        fh.write(struct.pack("<II", vc, tc))
        for vi, ti in order:
            fh.write(struct.pack("<3f", *verts[vi]))
        for vi, ti in order:
            u = uvs[ti] if ti >= 0 else (0.0, 0.0)
            fh.write(struct.pack("<2f", *u))
        fh.write(struct.pack("<%di" % len(indices), *indices))
    return vc, tc


def main() -> int:
    pid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    use_tex = "--tex" in sys.argv
    if not pid:
        raise SystemExit("需要游戏 PID")
    vc, tc = build_bin(OBJ, BIN)
    bin_size = os.path.getsize(BIN)
    png_size = os.path.getsize(PNG)
    print(f"mesh {MESH_NAME} verts={vc} tris={tc} bin={bin_size} png={png_size}")

    js = (JS_TMPL
          .replace("__VC__", str(vc)).replace("__TC__", str(tc))
          .replace("__BIN__", BIN.replace("\\", "/")).replace("__BINSIZE__", str(bin_size))
          .replace("__PNG__", PNG.replace("\\", "/")).replace("__PNGSIZE__", str(png_size))
          .replace("__NAME__", MESH_NAME)
          .replace("__USE_TEX__", "true" if use_tex else "false")
          .replace("__PX__", str(POS[0])).replace("__PY__", str(POS[1])).replace("__PZ__", str(POS[2]))
          .replace("__YAW__", str(YAW)))

    session = frida.attach(pid)
    script = session.create_script(js)
    script.on("message", lambda m, d: print(json.dumps(m if m.get("type") != "send" else m.get("payload"), ensure_ascii=False)))
    script.load()
    import time
    time.sleep(12)
    session.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
