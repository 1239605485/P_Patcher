"""Sign one edited mdz-feature/1 manifest without rebuilding all packages."""
import argparse,json,zipfile
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import serialization,hashes
from cryptography.hazmat.primitives.asymmetric import padding
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--key',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 m=json.loads(a.manifest.read_text(encoding='utf-8-sig'));assert m['format']=='mdz-feature/1' and m['rules']
 pem=a.key.read_bytes();key=serialization.load_pem_private_key(pem,None);cert=x509.load_pem_x509_certificate(pem[pem.index(b'-----BEGIN CERTIFICATE-----'):]);fp=cert.fingerprint(hashes.SHA256()).hex()
 assert fp=='21fa47120af53f71b39e886eaf0d71a159c34a2d332646a1cf0820a59549ad10','wrong signing identity'
 m['signer_sha256']=fp;raw=json.dumps(m,ensure_ascii=False,separators=(',',':')).encode();a.output.parent.mkdir(parents=True,exist_ok=True)
 signature=key.sign(raw,padding.PKCS1v15(),hashes.SHA256());cert.public_key().verify(signature,raw,padding.PKCS1v15(),hashes.SHA256())
 with zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:z.writestr('feature.json',raw);z.writestr('feature.sig',signature)
 print(str(a.output),a.output.stat().st_size)
if __name__=='__main__':main()
