"""Collect individually signed feature ZIPs without needing a private key."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.hashes import SHA256
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--features',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 cert=x509.load_der_x509_certificate((ROOT/'assets/trust.der').read_bytes());parts={};items=[];ids=set();core=0
 for f in sorted(a.features.glob('*.zip')):
  with zipfile.ZipFile(f) as z:
   kind='module' if 'module.json' in z.namelist() else 'feature'
   raw=z.read(kind+'.json');cert.public_key().verify(z.read(kind+'.sig'),raw,padding.PKCS1v15(),SHA256());m=json.loads(raw)
   ident='isolation-core' if kind=='module' else m['id'];assert ident not in ids,'duplicate feature: '+ident;ids.add(ident);core+=kind=='module'
  data=f.read_bytes();name='features/'+f.name;parts[name]=data;items.append({'path':name,'id':ident,'name':m['name'],'size':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 assert core==1,'exactly one native/isolation core package is required'
 meta={'format':'mdz-bundle/1','name':'MiniDayZ2 自定义功能整合包','version':'1.6.0','features':items}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  z.writestr('bundle.json',json.dumps(meta,ensure_ascii=False,separators=(',',':')))
  for n,data in parts.items():z.writestr(n,data)
 print(str(a.output),a.output.stat().st_size)
if __name__=='__main__':main()
