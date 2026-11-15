from pathlib import Path
import io,struct,json,zipfile,sys
from elftools.elf.elffile import ELFFile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'source/tools'));from dump_il2cpp_v108 import table_layout
ROOT=Path(__file__).resolve().parents[2]
def extract(raw,meta,types):
 e=ELFFile(io.BytesIO(raw));segs=[s for s in e.iter_segments() if s['p_type']=='PT_LOAD'];rela=e.get_section_by_name('.rela.dyn');rel={r['r_offset']:r['r_addend'] for r in rela.iter_relocations() if r['r_info_type']==1027}
 def off(v):
  for s in segs:
   if s['p_vaddr']<=v<s['p_vaddr']+s['p_filesz']:return s['p_offset']+v-s['p_vaddr']
 def addr(f):
  for s in segs:
   if s['p_offset']<=f<s['p_offset']+s['p_filesz']:return s['p_vaddr']+f-s['p_offset']
 t,ts,count=table_layout(meta,19);f,fs,fn=table_layout(meta,11);st,sz,_=table_layout(meta,2)
 def name(i):return meta[st+i:meta.index(0,st+i)].decode(errors='replace')
 needle=struct.pack('<Q',count);pos=raw.find(needle);candidates=[]
 while pos>=0:
  v=addr(pos);ptr=rel.get(v+8) if v is not None else None
  if ptr and off(ptr) is not None:
   score=sum(ptr+i*8 in rel for i in range(count));candidates.append((score,v,ptr))
  pos=raw.find(needle,pos+1)
 print('candidates',[(n,hex(a),hex(b)) for n,a,b in sorted(candidates,reverse=True)[:5]],flush=True)
 item=next(x for x in types if x['namespace']=='MDZ2.Items' and x['name']=='ItemStack')
 valid=[]
 for score,site,array in candidates:
  pointer=rel.get(array+item['index']*8)
  if pointer and off(pointer) is not None and struct.unpack_from('<3i',raw,off(pointer))==(16,24,28):valid.append((score,site,array))
 assert len(valid)==1,'ambiguous field-offset registration'
 score,site,array=valid[0];assert score>count//2
 out={}
 for x in types:
  row=meta[t+x['index']*ts:t+(x['index']+1)*ts];start=struct.unpack_from('<H',row,20)[0];ptr=rel.get(array+x['index']*8)
  if not x['field_count']:continue
  if not ptr or off(ptr) is None:continue
  offsets=struct.unpack_from('<'+'i'*x['field_count'],raw,off(ptr));fields=[name(struct.unpack_from('<i',meta,f+(start+i)*fs)[0]) for i in range(x['field_count'])]
  type_key=x['namespace']+'.'+x['name'];type_key=type_key if type_key not in out else type_key+'#'+str(x['index'])
  out[type_key]=[{'name':n,'offset':o} for n,o in zip(fields,offsets)]
 return {'registration_site':site,'array':array,'types':out}
if __name__=='__main__':
 for tag,raw,meta,typ in [('old',zipfile.ZipFile(ROOT/'source/output/MiniDayZ2_0.1.53_P14_InfoFix.apk').read('lib/arm64-v8a/libil2cpp.so'),zipfile.ZipFile(ROOT/'source/output/MiniDayZ2_0.1.53_P14_InfoFix.apk').read('assets/bin/Data/Managed/Metadata/global-metadata.dat'),'analysis/types.json'),('new',(ROOT/'author_update/extracted/libil2cpp.so').read_bytes(),(ROOT/'author_update/extracted/metadata.dat').read_bytes(),'author_update/analysis/types.json')]:
  r=extract(raw,meta,json.load(open(ROOT/typ)));(ROOT/'author_update/analysis'/('field_offsets_'+tag+'.json')).write_text(json.dumps(r,indent=2));print(tag,'types',len(r['types']))
