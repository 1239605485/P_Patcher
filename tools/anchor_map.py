"""Conservative native anchor alignment. Produces plans, never writes a game binary."""
from pathlib import Path
import bisect,csv,io,json,collections,difflib,re
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
class Image:
 def __init__(self,raw,rows):
  self.raw=raw;self.elf=ELFFile(io.BytesIO(raw));self.segments=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD'];self.cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);self.rows=[dict(r,rva=int(r['rva'],16)) for r in rows if r.get('rva')];self.starts=sorted(set(r['rva'] for r in self.rows));self.by=collections.defaultdict(list)
  for r in self.rows:self.by[(r['assembly'],r['type'],r['method'],r['params'])].append(r)
 def offset(self,va):
  for s in self.segments:
   if s['p_vaddr']<=va<s['p_vaddr']+s['p_filesz']:return s['p_offset']+va-s['p_vaddr']
  raise ValueError('unmapped '+hex(va))
 def method_at(self,va):
  i=bisect.bisect_right(self.starts,va)-1
  if i<0:raise ValueError('no containing method')
  start=self.starts[i];return [r for r in self.rows if r['rva']==start]
 def instructions(self,rva):
  i=bisect.bisect_right(self.starts,rva);end=self.starts[i] if i<len(self.starts) else rva+4096
  return list(self.cs.disasm(self.raw[self.offset(rva):self.offset(rva)+min(end-rva,262144)],rva))

def normalize(i):
 s=i.op_str
 if i.mnemonic.startswith('b') or i.mnemonic in ['cbz','cbnz','tbz','tbnz','adr','adrp']:
  s=re.sub(r'#?0x[0-9a-f]+(?=\s*$)','<address>',s)
 return i.mnemonic+' '+s

def align(old,new,site):
 rows=old.method_at(site);choices=[]
 for row in rows:
  key=(row['assembly'],row['type'],row['method'],row['params']);targets={r['rva'] for r in new.by.get(key,[])}
  if len(targets)!=1:continue
  target=next(iter(targets));oi=old.instructions(row['rva']);ni=new.instructions(target);index=(site-row['rva'])//4
  if index>=len(oi):continue
  # Patched instructions at the requested site are excluded from scoring.
  a=[normalize(x) for x in oi];b=[normalize(x) for x in ni];lo=max(0,index-8);hi=min(len(a),index+9);rank=[]
  for j in range(len(b)):
   before=min(index-lo,j);after=min(hi-index-1,len(b)-j-1)
   if before+after<4:continue
   score=sum(a[index-k]==b[j-k] for k in range(1,before+1))+sum(a[index+k]==b[j+k] for k in range(1,after+1));total=before+after;rank.append((score/total,score,total,j))
  rank.sort(reverse=True)
  if not rank:continue
  best=rank[0];ties=[x for x in rank if x[:3]==best[:3]];margin=best[0]-rank[1][0] if len(rank)>1 else 1.0
  choices.append({'source_method':row,'target_method':next(r for r in new.rows if r['rva']==target),'source_site':site,'target_site':ni[best[3]].address,'source_instruction':oi[index].mnemonic+' '+oi[index].op_str,'target_instruction':ni[best[3]].mnemonic+' '+ni[best[3]].op_str,'context_score':best[0],'context_instructions':best[2],'top_ties':len(ties),'margin':margin,'status':'CONTEXT_CANDIDATE' if len(ties)==1 and best[0]>=0.9 and margin>=0.08 else 'REVIEW_REQUIRED'})
 if not choices:return {'source_site':site,'status':'MISSING_OR_AMBIGUOUS_METHOD'}
 sites={x['target_site'] for x in choices}
 if len(sites)!=1:return {'source_site':site,'status':'CONFLICTING_ALIAS_METHODS','choices':choices}
 return max(choices,key=lambda x:x['context_score'])

def main():
 import zipfile
 root=Path(__file__).resolve().parents[2];old=Image(zipfile.ZipFile(root/'source/output/MiniDayZ2_0.1.53_P14_InfoFix.apk').read('lib/arm64-v8a/libil2cpp.so'),list(csv.DictReader(open(root/'analysis/methods.csv'))));new=Image((root/'author_update/extracted/libil2cpp.so').read_bytes(),list(csv.DictReader(open(root/'author_update/analysis/methods.csv'))));hooks=json.load(open(root/'author_update/analysis/injection_hooks.json'));result=[]
 for i,h in enumerate(hooks):
  r=align(old,new,int(h['site'],16));r['injected_target']=h['target'];result.append(r)
  if i%20==0:print('Aligned',i,'/',len(hooks),flush=True)
 report={'status':'PLAN_ONLY_NOT_APPLIED','source_hook_count':len(hooks),'counts':dict(collections.Counter(r['status'] for r in result)),'anchors':result,'limitation':'Context candidates are not approval to patch. Author code, field offsets, references and behavior still require validation.'};(root/'author_update/analysis/native_anchor_plan.json').write_text(json.dumps(report,indent=2));print(report['counts'])
if __name__=='__main__':main()
