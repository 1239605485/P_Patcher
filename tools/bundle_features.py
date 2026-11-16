"""Create an outer bundle from independently signed feature ZIPs."""
import argparse, json, zipfile, hashlib
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args(); items=[]
 for f in a.input:
  b=f.read_bytes();items.append({'id':f.stem,'file':f.name,'sha256':hashlib.sha256(b).hexdigest(),'size':len(b)})
 manifest={'format':'mdz-feature-bundle/1','modules':items,'install_order':[x['id'] for x in items]}
 with zipfile.ZipFile(a.out,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('bundle.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode());
  for f in a.input:z.write(f,f.name)
 print(a.out)
if __name__=='__main__':main()
