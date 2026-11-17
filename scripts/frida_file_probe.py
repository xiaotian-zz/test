import frida, sys, json
pid = int(sys.argv[1])
JS = r"""
const out={};
out.writeByteArray=typeof Memory.writeByteArray;
try{
 const fl=new File('f:/rea/artifacts/inject/tree.bin','rb');
 out.fileOk=true;
 out.seek=typeof fl.seek;
 out.readBytes=typeof fl.readBytes;
 fl.seek(0,0);
 const b=fl.readBytes(12);
 out.len=b.byteLength;
 out.slice=typeof b.slice;
 fl.close();
}catch(e){out.fileErr=String(e);}
send(out);
"""
s=frida.attach(pid); sc=s.create_script(JS)
sc.on('message', lambda m,d: print(json.dumps(m, ensure_ascii=False)))
sc.load(); s.detach()
