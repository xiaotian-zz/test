"""探测 Transform 字段/方法与常用 API。"""
import frida, sys, json
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 19924
JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');
const E=n=>ga.getExportByName(n), P=Process.pointerSize;
const f={dom:new NativeFunction(E('il2cpp_domain_get'),'pointer',[]),
 asms:new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer']),
 asmImg:new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']),
 imgName:new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']),
 fromName:new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']),
 cName:new NativeFunction(E('il2cpp_class_get_name'),'pointer',['pointer']),
 cFields:new NativeFunction(E('il2cpp_class_get_fields'),'pointer',['pointer','pointer']),
 cMethods:new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']),
 fName:new NativeFunction(E('il2cpp_field_get_name'),'pointer',['pointer']),
 fOff:new NativeFunction(E('il2cpp_field_get_offset'),'size_t',['pointer']),
 fType:new NativeFunction(E('il2cpp_field_get_type'),'pointer',['pointer']),
 tName:new NativeFunction(E('il2cpp_type_get_name'),'pointer',['pointer']),
 mName:new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']),
 mParamCount:new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']),
};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let core=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a);if(cs(f.imgName(im))==='UnityEngine.CoreModule.dll')core=im;}
for(const [cls,ns,cn] of [['Transform','UnityEngine','Transform'],['Object','UnityEngine','Object'],['GameObject','UnityEngine','GameObject'],['Camera','UnityEngine','Camera']]){
  const k=f.fromName(core,Memory.allocUtf8String(ns),Memory.allocUtf8String(cn));
  if(k.isNull()){send({log:cn+' null'});continue;}
  const it=Memory.alloc(P);it.writePointer(ptr(0));const fs=[];
  for(let i=0;i<64;i++){const fl=f.cFields(k,it);if(fl.isNull())break;fs.push({n:cs(f.fName(fl)),t:cs(f.tName(f.fType(fl))),o:String(f.fOff(fl))});}
  const mit=Memory.alloc(P);mit.writePointer(ptr(0));const ms=[];
  for(let i=0;i<200;i++){const m=f.cMethods(k,mit);if(m.isNull())break;ms.push(cs(f.mName(m))+'/'+f.mParamCount(m));}
  send({log:cn,fields:fs,methods:ms});
}
"""
s=frida.attach(PID);sc=s.create_script(JS)
sc.on('message',lambda m,d: print(json.dumps(m.get('payload'),ensure_ascii=False)))
sc.load()
import time;time.sleep(3);s.detach()
