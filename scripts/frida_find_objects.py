"""遍历当前加载的 GameObject，查找可用作摊位的模型。"""
import frida, sys, json, time
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 19924
JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const f={dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cType:new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 tObj:new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer']),
};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull())return '';const n=p.add(0x10).readU32();return p.add(0x14).readUtf16String(n);}catch(e){return '';}}
function findMethod(cls,name,argc){const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<256;i++){const m=f.cMethods(cls,it);if(m.isNull())break;if(cs(f.mName(m))===name&&(argc===undefined||m.add(0).readU8()>=0))return m.add(P).readPointer();}return null;}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();let core=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a);if(cs(f.imgName(im))==='UnityEngine.CoreModule.dll')core=im;}
const RES=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Resources'));
const GO=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('GameObject'));
const OBJ=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
const getName=findMethod(OBJ,'get_name');
const NFname=new NativeFunction(getName,'pointer',['pointer']);
const find=findMethod(RES,'FindObjectsOfTypeAll');
const goType=f.tObj(f.cType(GO));
const arr=new NativeFunction(find,'pointer',['pointer'])(goType);
const len=arr.add(0x18).readU64().toNumber();
send({log:'gameobjects '+len});
const kws=['wheelbarrow','barrow','tent','cart','market','kiosk','shop','fair','bazaar','stall'];
let out=[];
for(let i=0;i<len;i++){
  const o=arr.add(0x20).add(i*P).readPointer();
  let nm='';try{nm=ilstr(NFname(o));}catch(e){}
  const low=nm.toLowerCase();
  if(kws.some(k=>low.indexOf(k)>=0)){
    let act=false;try{act=o.add(0).readPointer().isNull()?false:true;}catch(e){}
    out.push(nm);
  }
}
send({log:'hits '+out.length,names:out.slice(0,200)});
"""
s=frida.attach(PID);sc=s.create_script(JS)
sc.on('message',lambda m,d: print(json.dumps(m.get('payload'),ensure_ascii=False)))
sc.load();time.sleep(4);s.detach()
