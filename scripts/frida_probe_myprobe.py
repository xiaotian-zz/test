"""探测 RF4.Client.MyProbe 类结构，打印方法列表。"""
import frida
import json
import sys
import time

PID = int(sys.argv[1])

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const dom=new NativeFunction(E('il2cpp_domain_get'),'pointer',[])();
const cnt=Memory.alloc(8);
const asms=new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer'])(dom,cnt);
const n=cnt.readUInt();
const asmImg=new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']);
const imgName=new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']);
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
let game=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer(),im=asmImg(a),nm=cs(imgName(im));if(nm==='Assembly-CSharp.dll')game=im;}
const fromName=new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']);
const cMethods=new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']);
const mName=new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']);
const mPC=new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']);
const typeName=new NativeFunction(E('il2cpp_type_get_name'),'pointer',['pointer']);
const getParam=new NativeFunction(E('il2cpp_method_get_param'),'pointer',['pointer','uint']);
function dump(ns,name){
 const cls=fromName(game,Memory.allocUtf8String(ns),Memory.allocUtf8String(name));
 send({log:name+' cls='+(cls.isNull()?'null':cls.toString())});
 if(cls.isNull())return;
 const it=Memory.alloc(P);it.writePointer(ptr(0));
 const out=[];
 for(let i=0;i<300;i++){
  const m=cMethods(cls,it);if(m.isNull())break;
  const pc=mPC(m);
  const ps=[];
  for(let k=0;k<pc;k++)ps.push(cs(typeName(getParam(m,k))));
  out.push(cs(mName(m))+'('+ps.join(',')+')');
 }
 send({log:name+' methods: '+out.slice(0,60).join(' | ')});
 send({log:name+' totalMethods='+out.length});
}
dump('RF4.Client','MyProbe');
send({log:'done'});
"""

s = frida.attach(PID)
sc = s.create_script(JS)
sc.on('message', lambda m, d: print(json.dumps(m if m.get('type') != 'send' else m.get('payload'), ensure_ascii=False)))
sc.load()
time.sleep(4)
s.detach()
