"""用 old_wheelbarrow 复制一个摊位并挂 Shop 组件（运行时注入，不改客户端文件）。"""
import frida, sys, json, time

PID = int(sys.argv[1]) if len(sys.argv) > 1 else 19924

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');
const E=n=>ga.getExportByName(n), P=Process.pointerSize;
const f={
 dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cName:new NativeFunction(E('il2cpp_class_get_name'),'pointer',['pointer']),
 cType:new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']),
 tObj:new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer']),
 strNew:new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer']),
 cFields:new NativeFunction(E('il2cpp_class_get_fields'),'pointer',['pointer','pointer']),
 fName:new NativeFunction(E('il2cpp_field_get_name'),'pointer',['pointer']),
 fOff:new NativeFunction(E('il2cpp_field_get_offset'),'size_t',['pointer']),
};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull())return '';const n=p.add(0x10).readU32();return p.add(0x14).readUtf16String(n);}catch(e){return '';}}
function findMethod(cls,name,argc){
  const it=Memory.alloc(P);it.writePointer(ptr(0));
  for(let i=0;i<512;i++){const m=f.cMethods(cls,it);if(m.isNull())break;
    if(cs(f.mName(m))===name && (argc===undefined||f.mParamCount(m)===argc)) return m.add(P).readPointer();}
  return null;
}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null,core=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a),nm=cs(f.imgName(im));
  if(nm==='Assembly-CSharp.dll')game=im; if(nm==='UnityEngine.CoreModule.dll')core=im;}
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const TR=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Transform'));
const CAM=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Camera'));
const SHOP=f.fromName(game,Memory.allocUtf8String('RF4.Client.FishingScene'),Memory.allocUtf8String('Shop'));
const find=findMethod(GO,'Find',1), inst=findMethod(OBJ,'Instantiate',1);
const getT=findMethod(GO,'get_transform',0), setAct=findMethod(GO,'SetActive',1);
const addComp=findMethod(GO,'AddComponent',1);
const getPosI=findMethod(TR,'get_position_Injected',1), setPosI=findMethod(TR,'set_position_Injected',1);
const getRotI=findMethod(TR,'get_rotation_Injected',1);
const camMain=findMethod(CAM,'get_main',0);
send({log:'apis '+JSON.stringify({find:!!find,inst:!!inst,getT:!!getT,addComp:!!addComp,getPosI:!!getPosI,setPosI:!!setPosI,cam:!!camMain})});
if(!find||!inst||!getT||!addComp||!getPosI||!setPosI||!camMain||SHOP.isNull()){
  send({log:'缺少 API'}); 
}else{
  const NFfind=new NativeFunction(find,'pointer',['pointer']);
  const NFin=new NativeFunction(inst,'pointer',['pointer']);
  const NFgt=new NativeFunction(getT,'pointer',['pointer']);
  const NFadd=new NativeFunction(addComp,'pointer',['pointer','pointer']);
  const NFset=new NativeFunction(setAct,'void',['pointer','int']);
  const NFgp=new NativeFunction(getPosI,'void',['pointer','pointer']);
  const NFsp=new NativeFunction(setPosI,'void',['pointer','pointer']);
  const NFgr=new NativeFunction(getRotI,'void',['pointer','pointer']);
  const NFcam=new NativeFunction(camMain,'pointer',[]);
  let go=NFfind(f.strNew(Memory.allocUtf8String('old_wheelbarrow')));
  if(go.isNull()) go=NFfind(f.strNew(Memory.allocUtf8String('old_wheelbarrow (1)')));
  send({log:'wheelbarrow '+(go.isNull()?'null':'ok')});
  if(!go.isNull()){
    // 找一个现有 Shop，取 storeID 后缀与配置指针
    let suffix='006', cfg=ptr(0), sample=null;
    const objFind=findMethod(OBJ,'FindObjectsOfType',1);
    if(objFind){
      const NFof=new NativeFunction(objFind,'pointer',['pointer']);
      const arr=NFof(f.tObj(f.cType(SHOP)));
      if(!arr.isNull()){
        const len=arr.add(0x18).readU64().toNumber();
        for(let i=0;i<len;i++){
          const o=arr.add(0x20).add(i*P).readPointer();
          const sid=ilstr(o.add(80).readPointer());
          if(sid){ const m=sid.match(/_(\d+)$/); if(m){suffix=m[1]; cfg=o.add(104).readPointer(); sample=o; } break; }
        }
      }
    }
    const storeID='ny_bazaarStore_'+suffix;
    send({log:'storeID '+storeID+' sample '+(sample?ilstr(sample.add(80).readPointer()):'none')});
    const dup=NFin(go);
    send({log:'dup '+(dup.isNull()?'null':'ok')});
    if(!dup.isNull()){
      NFset(dup,0);
      const tr=NFgt(dup);
      const c=NFcam();
      let tx=0,ty=0,tz=0;
      if(!c.isNull()){
        const ct=NFgt(c); const buf=Memory.alloc(16);
        NFgp(ct,buf); const cx=buf.readFloat(), cy=buf.add(4).readFloat(), cz=buf.add(8).readFloat();
        const rbuf=Memory.alloc(16); NFgr(ct,rbuf);
        const qx=rbuf.readFloat(), qy=rbuf.add(4).readFloat(), qz=rbuf.add(8).readFloat(), qw=rbuf.add(12).readFloat();
        const fx=2*(qx*qz+qw*qy), fy=2*(qy*qz-qw*qx), fz=1-2*(qx*qx+qy*qy);
        tx=cx+fx*3; ty=cy+fy*3-1.2; tz=cz+fz*3;
        send({log:'cam '+cx.toFixed(2)+','+cy.toFixed(2)+','+cz.toFixed(2)+' -> '+tx.toFixed(2)+','+ty.toFixed(2)+','+tz.toFixed(2)});
      }
      const v=Memory.alloc(16); v.writeFloat(tx); v.add(4).writeFloat(ty); v.add(8).writeFloat(tz);
      NFsp(tr,v);
      const shopType=f.tObj(f.cType(SHOP));
      const comp=NFadd(dup,shopType);
      send({log:'shop comp '+(comp.isNull()?'null':'ok')});
      if(!comp.isNull()){
        comp.add(80).writePointer(f.strNew(Memory.allocUtf8String(storeID)));
        if(!cfg.isNull()) comp.add(104).writePointer(cfg);
        NFset(dup,1);
        send({log:'spawned '+storeID});
      }
    }
  }
}
"""
s=frida.attach(PID);sc=s.create_script(JS)
sc.on('message',lambda m,d: print(json.dumps(m.get('payload'),ensure_ascii=False)))
sc.load();time.sleep(4);s.detach()
