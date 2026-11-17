"""只在主菜单阶段挂 MyProbe 补丁，防止进图时 UI 重建闪退。

用法:
  py -3.12 scripts/frida_patch_probe.py <PID> [持续秒数]
"""
import frida
import json
import sys
import time

PID = int(sys.argv[1])
DURATION = float(sys.argv[2]) if len(sys.argv) > 2 else 600

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');const E=n=>ga.getExportByName(n),P=Process.pointerSize;
const dom=new NativeFunction(E('il2cpp_domain_get'),'pointer',[])();
const cnt=Memory.alloc(8);
const asms=new NativeFunction(E('il2cpp_domain_get_assemblies'),'pointer',['pointer','pointer'])(dom,cnt);
const n=cnt.readUInt();
const asmImg=new NativeFunction(E('il2cpp_assembly_get_image'),'pointer',['pointer']);
const imgName=new NativeFunction(E('il2cpp_image_get_name'),'pointer',['pointer']);
let game=null;
for(let i=0;i<n;i++){const a=asms.add(i*P).readPointer();const nm=imgName(asmImg(a)).readUtf8String();if(nm==='Assembly-CSharp.dll')game=asmImg(a);}
function cs(p){try{return p.isNull()?'':p.readUtf8String();}catch(e){return '';}}
const fromName=new NativeFunction(E('il2cpp_class_from_name'),'pointer',['pointer','pointer','pointer']);
const cMethods=new NativeFunction(E('il2cpp_class_get_methods'),'pointer',['pointer','pointer']);
const mName=new NativeFunction(E('il2cpp_method_get_name'),'pointer',['pointer']);
const mParams=new NativeFunction(E('il2cpp_method_get_param_count'),'uint',['pointer']);
function findMethod(cls,name,argc){const it=Memory.alloc(P);it.writePointer(ptr(0));for(let i=0;i<512;i++){const m=cMethods(cls,it);if(m.isNull())break;if(cs(mName(m))===name&&mParams(m)===argc)return m.add(P).readPointer();}return null;}
let ok=false;
try{
 const MP=fromName(game,Memory.allocUtf8String('RF4.Client'),Memory.allocUtf8String('MyProbe'));
 if(!MP.isNull()){
  const mi=findMethod(MP,'mipcnipgejd',1);
  if(mi){Interceptor.replace(mi,new NativeCallback(function(){},'void',['pointer','int']));ok=true;}
 }
}catch(e){send({log:'err '+e});}
send({log:'myprobe patched='+ok});
"""

s = frida.attach(PID)
sc = s.create_script(JS)
sc.on('message', lambda m, d: print(json.dumps(m.get('payload', m), ensure_ascii=False)))
sc.load()
time.sleep(DURATION)
s.detach()
