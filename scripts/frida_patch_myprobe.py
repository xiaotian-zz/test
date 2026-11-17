"""把 RF4.Client.MyProbe.mipcnipgejd(Int32) 替换为空实现，用于隔离闪退。"""
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
const cls=fromName(game,Memory.allocUtf8String('RF4.Client'),Memory.allocUtf8String('MyProbe'));
const it=Memory.alloc(P);it.writePointer(ptr(0));
let target=null,names=[];
for(let i=0;i<300;i++){
 const m=cMethods(cls,it);if(m.isNull())break;
 const nm=cs(mName(m));
 if(nm==='mipcnipgejd'&&mPC(m)===1)target=m.add(P).readPointer();else names.push(nm);
}
send({log:'target='+(target?target.toString():'null')+' methods='+names.join(',')});
if(target){
 const noop=new NativeCallback(function(self,i){},'void',['pointer','int']);
 globalThis._noop=noop;
 Interceptor.replace(target,noop);
 send({log:'replaced mipcnipgejd'});
}
"""

s = frida.attach(PID)
sc = s.create_script(JS)
sc.on('message', lambda m, d: print(json.dumps(m if m.get('type') != 'send' else m.get('payload'), ensure_ascii=False)))
sc.load()
time.sleep(120)
s.detach()
