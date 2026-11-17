import frida, sys, json, time

JS = r"""
const ga=Process.getModuleByName('GameAssembly.dll');
function E(n){return ga.getExportByName(n);}
const dom=new NativeFunction(E('il2cpp_domain_get'),'pointer',[])();
send({log:'dom '+(dom.isNull()?'null':'ok')});
try{
  const at=new NativeFunction(E('il2cpp_thread_attach'),'pointer',['pointer']);
  const r=at(dom);
  send({log:'attach '+(r.isNull()?'null':'ok')});
}catch(e){send({log:'attach err '+e});}
try{
  const sn=new NativeFunction(E('il2cpp_string_new'),'pointer',['pointer']);
  const p=Memory.allocUtf8String('hello');
  const s=sn(p);
  send({log:'strNew '+(s.isNull()?'NULL':'ok '+s)});
  if(!s.isNull()){
    send({log:'len '+s.add(0x10).readU32()+' chars '+(s.add(0x14).readU16())+','+(s.add(0x16).readU16())});
  }
}catch(e){send({log:'strNew err '+e});}
try{
  const sn2=new NativeFunction(E('il2cpp_string_new_utf16'),'pointer',['pointer','int']);
  const buf=Memory.alloc(16);
  buf.writeU16('A'.charCodeAt(0));buf.add(2).writeU16('B'.charCodeAt(0));
  const s2=sn2(buf,2);
  send({log:'strNew16 '+(s2.isNull()?'NULL':'ok')});
}catch(e){send({log:'strNew16 err '+e});}
"""

pid = int(sys.argv[1])
s = frida.attach(pid)
sc = s.create_script(JS)
sc.on('message', lambda m, d: print(json.dumps(m.get('payload', m), ensure_ascii=False)))
sc.load()
time.sleep(2)
s.detach()
