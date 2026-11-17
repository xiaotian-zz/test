"""列出 UnityEngine.AssetBundle 的方法签名。"""
import frida
import json
import sys
import time

PID = int(sys.argv[1]) if len(sys.argv) > 1 else 25668

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
 getParam:new NativeFunction(E('il2cpp_method_get_param'),'pointer',['pointer','uint']),
 typeName:new NativeFunction(E('il2cpp_type_get_name'),'pointer',['pointer']),
};
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
const dom=f.dom(),cnt=Memory.alloc(8),asms=f.asms(dom,cnt),n=cnt.readUInt();let abm=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=f.asmImg(a);if(cs(f.imgName(im))==='UnityEngine.AssetBundleModule.dll')abm=im;}
const AB=f.fromName(abm,Memory.allocUtf8String('UnityEngine'),Memory.allocUtf8String('AssetBundle'));
const it=Memory.alloc(P);it.writePointer(ptr(0));
for(let i=0;i<200;i++){const m=f.cMethods(AB,it);if(m.isNull())break;
 const nm=cs(f.mName(m));const pc=f.mParamCount(m);let ps=[];
 for(let j=0;j<pc;j++)ps.push(cs(f.typeName(f.getParam(m,j))));
 send({log:nm+'('+ps.join(', ')+')'});
}
"""

s = frida.attach(PID)
sc = s.create_script(JS)
sc.on('message', lambda m, d: print(json.dumps(m if m.get('type') != 'send' else m.get('payload'), ensure_ascii=False)))
sc.load()
time.sleep(3)
s.detach()
