"""Validate mdz-engine/1 manifest and payload identities without loading code."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.hashes import SHA256
def main():
 p=argparse.ArgumentParser();p.add_argument('package',type=Path);a=p.parse_args()
 with zipfile.ZipFile(a.package) as z:
  raw=z.read('engine.json');m=json.loads(raw); assert m.get('format')=='mdz-engine/1' and m['api']==1
  cert=x509.load_der_x509_certificate((Path(__file__).resolve().parents[1]/'assets/trust.der').read_bytes())
  cert.public_key().verify(z.read('engine.sig'),raw,padding.PKCS1v15(),SHA256())
  assert m['signer_sha256']==cert.fingerprint(SHA256()).hex()
  assert set(m['files'])=={'classes.dex','locators.json'}
  for name,r in m['files'].items():
   b=z.read(name); assert len(b)==r['size']; assert hashlib.sha256(b).hexdigest()==r['sha256']
  print(json.dumps({'id':m['id'],'version':m['version'],'status':'SIGNATURE_AND_PAYLOADS_VALID'},ensure_ascii=False))
if __name__=='__main__':main()
