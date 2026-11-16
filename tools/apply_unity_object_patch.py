"""Apply mdz-unity-object-patch/1 to a Unity bundle and rebuild it.

This is the desktop fallback used until the Android UnityFS writer is bundled.
"""
import argparse, hashlib, json, zipfile
from pathlib import Path
import UnityPy

def sha(b): return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--patch',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 with zipfile.ZipFile(a.patch) as z:
  manifest=json.loads(z.read('object_patch.json')); env=UnityPy.load(a.bundle.read_bytes()); changed=0
  for item in manifest['objects']:
   payload=json.loads(z.read(item['payload'])); target=None
   for obj in env.objects:
    if obj.type.name!='TextAsset': continue
    asset=obj.read()
    if asset.m_Name==item['name']:
     target=asset;break
   if target is None: raise SystemExit('missing TextAsset: '+item['name'])
   current=target.m_Script.encode('utf-8') if isinstance(target.m_Script,str) else bytes(target.m_Script)
   if sha(current)!=item['before_sha256']: raise SystemExit('preimage mismatch: '+item['name'])
   target.m_Script=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8');target.save();changed+=1
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(env.file.save());print(json.dumps({'changed_objects':changed,'output':str(a.out),'sha256':sha(a.out.read_bytes())},ensure_ascii=False))
if __name__=='__main__':raise SystemExit('Deprecated experimental format. Use the signed external engine and mdz-feature/1 packages.')
