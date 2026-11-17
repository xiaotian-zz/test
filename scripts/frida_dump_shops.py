"""列出当前场景中所有 RF4.Client.FishingScene.Shop 实例及 storeID。"""
import frida, sys, json

PID = int(sys.argv[1]) if len(sys.argv) > 1 else 19924

JS = r"""
const ga = Process.getModuleByName('GameAssembly.dll');
const E = n => ga.getExportByName(n);
const P = Process.pointerSize;
const f = {
  dom: new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
  asms: new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
  asmImg: new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
  imgName: new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
  fromName: new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
  cName: new NativeFunction(E('il2cpp_class_get_name'),'pointer',['pointer']),
  cNs: new NativeFunction(E('il2cpp_class_get_namespace'),'pointer',['pointer']),
  cType: new NativeFunction(E('il2cpp_class_get_type'),'pointer',['pointer']),
  cMethods: new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
  cFields: new NativeFunction(E('il2cpp_class_get_fields'),'pointer',['pointer','pointer']),
  mName: new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
  fName: new NativeFunction(E('il2cpp_field_get_name'),'pointer',['pointer']),
  fOff: new NativeFunction(E('il2cpp_field_get_offset'),'size_t',['pointer']),
  fType: new NativeFunction(E('il2cpp_field_get_type'),'pointer',['pointer']),
  tName: new NativeFunction(E('il2cpp_type_get_name'),'pointer',['pointer']),
  tObj: new NativeFunction(E('il2cpp_type_get_object'),'pointer',['pointer']),
};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
function ilstr(p){try{if(p.isNull())return '';const n=p.add(0x10).readU32();return p.add(0x14).readUtf16String(n);}catch(e){return '';}}
const dom=f.dom(), cnt=Memory.alloc(8);
const asms=f.asms(dom,cnt), n=cnt.readUInt();
let img=null, core=null;
for(let i=0;i<n;i++){
  const a=asms.add(i*P).readPointer(), im=f.asmImg(a), nm=cs(f.imgName(im));
  if(nm==='Assembly-CSharp.dll') img=im;
  if(nm==='UnityEngine.CoreModule.dll') core=im;
}
const shop=f.fromName(img,Memory.allocUtf8String('RF4.Client.FishingScene'),Memory.allocUtf8String('Shop'));
send({log:'Shop class '+(shop.isNull()?'null':'ok')});
if(!shop.isNull()){
  const it=Memory.alloc(P); it.writePointer(ptr(0));
  const fields=[];
  for(let i=0;i<64;i++){
    const fl=f.cFields(shop,it); if(fl.isNull()) break;
    const nm=cs(f.fName(fl)), tn=cs(f.tName(f.fType(fl)));
    let off=0; try{off=f.fOff(fl);}catch(e){}
    fields.push({nm:nm,tn:tn,off:off});
  }
  send({log:'fields '+JSON.stringify(fields)});
  const mit=Memory.alloc(P); mit.writePointer(ptr(0));
  const methods=[];
  for(let i=0;i<64;i++){
    const m=f.cMethods(shop,mit); if(m.isNull()) break;
    methods.push(cs(f.mName(m)));
  }
  send({log:'methods '+JSON.stringify(methods)});

  // Resources.FindObjectsOfTypeAll(Type)
  const res=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Resources'));
  let find=null;
  if(!res.isNull()){
    const it2=Memory.alloc(P); it2.writePointer(ptr(0));
    for(let i=0;i<64;i++){
      const m=f.cMethods(res,it2); if(m.isNull()) break;
      if(cs(f.mName(m))==='FindObjectsOfTypeAll'){ find=m.add(P).readPointer(); break; }
    }
  }
  send({log:'find '+(find?find:'null')});
  let nameNF=null;
  const objc=f.fromName(core,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('Object'));
  if(!objc.isNull()){
    const it3=Memory.alloc(P); it3.writePointer(ptr(0));
    for(let i=0;i<64;i++){
      const m=f.cMethods(objc,it3); if(m.isNull()) break;
      if(cs(f.mName(m))==='get_name'){ nameNF=new NativeFunction(m.add(P).readPointer(),'pointer',['pointer']); break; }
    }
  }
  if(find && nameNF){
    const type=f.tObj(f.cType(shop));
    const arr=new NativeFunction(find,'pointer',['pointer'])(type);
    if(!arr.isNull()){
      const len=arr.add(0x18).readU64().toNumber();
      send({log:'Shop instances '+len});
      for(let i=0;i<len;i++){
        const o=arr.add(0x20).add(i*P).readPointer();
        const nm=ilstr(nameNF(o));
        const vals={};
        for(const fd of fields){
          if(fd.tn==='System.String'){
            try{ vals[fd.nm]=ilstr(o.add(fd.off).readPointer()); }catch(e){}
          }
        }
        send({name:nm, fields:vals});
      }
    } else send({log:'arr null'});
  }
}
"""

session = frida.attach(PID)
script = session.create_script(JS)
def on_msg(m, d):
    if m.get("type") == "send":
        print(json.dumps(m.get("payload"), ensure_ascii=False))
    else:
        print("[frida]", m)
script.on("message", on_msg)
script.load()
import time
time.sleep(3)
session.detach()
