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
 imgClassCount:new NativeFunction(E('il2cpp_image_get_class_count'),'uint',['pointer']),
 imgClass:new NativeFunction(E('il2cpp_image_get_class'),'pointer',['pointer','uint'])};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();
let game=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a);if(cs(f.imgName(im))==='Assembly-CSharp.dll')game=im;}
send({log:'base='+ga.base});
const names=__CLASSES__;
for(const name of names){
 const k=f.fromName(game,Memory.allocUtf8String(''),Memory.allocUtf8String(name));
 if(k.isNull()){send({log:'MISS '+name});continue;}
 const it=Memory.alloc(P);it.writePointer(ptr(0));
 for(let j=0;j<400;j++){
  const mi=f.cMethods(k,it);if(mi.isNull())break;
  const mp=mi.readPointer(),inv=mi.add(P).readPointer();
  let t=(!mp.isNull()&&mp.compare(ptr(0x10000))>=0)?mp:inv;
  send({cls:name,method:cs(f.mName(mi)),argc:f.mParamCount(mi),rva:t.sub(ga.base).toInt32()});
 }
}
send({log:'done'});
"""

pid = int(sys.argv[1])
classes = sys.argv[2:] or ["lnepoeakhib", "pgohfpicjjd"]
js = JS.replace("__CLASSES__", json.dumps(classes))
s = frida.attach(pid)
sc = s.create_script(js)
sc.on("message", lambda m, d: print(json.dumps(m.get("payload", m), ensure_ascii=False)))
sc.load()
time.sleep(4)
s.detach()
