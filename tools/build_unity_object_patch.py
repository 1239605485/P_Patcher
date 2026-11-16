"""Build a small TextAsset/object patch from extracted Unity tables."""
import argparse,hashlib,json,zipfile
from pathlib import Path
TABLES=('world','strings_zh_tw','strings_zh_cn','strings_en_us','ui_zh_tw','ui_zh_cn')
def h(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--target',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True); items=[]
 with zipfile.ZipFile(a.out,'w',zipfile.ZIP_DEFLATED) as z:
  for name in TABLES:
   b=(a.base/(name+'.json')).read_bytes();t=(a.target/(name+'.json')).read_bytes()
   if b==t: continue
   path='objects/'+name+'.json';z.writestr(path,t);items.append({'name':name,'type':'TextAsset','payload':path,'before_sha256':h(b),'after_sha256':h(t),'size':len(t)})
  manifest={'format':'mdz-unity-object-patch/1','entry':'assets/bin/Data/data.unity3d','objects':items,'requires_installer_engine':'unity-textasset-rebuild/1'}
  z.writestr('object_patch.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode())
 print(json.dumps({'output':str(a.out),'objects':len(items),'bytes':a.out.stat().st_size},ensure_ascii=False))
if __name__=='__main__':raise SystemExit('Deprecated experimental format. Use tools/build_delivery.py; extracted JSON hashes are not Unity object hashes.')
