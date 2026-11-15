"""APK v2 signing and independent content/signature verification; retains supplied identity."""
import copy, hashlib, struct, zipfile
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

u32=lambda n:struct.pack('<I',n)
u64=lambda n:struct.pack('<Q',n)
lp=lambda b:u32(len(b))+b

def is_signature(name):
    n=name.upper()
    return n.startswith('META-INF/') and n.endswith(('.SF','.RSA','.DSA','.EC','MANIFEST.MF'))

def content_digest(parts):
    digests=[]
    for section in parts:
        for i in range(0,len(section),1048576):
            chunk=section[i:i+1048576]
            digests.append(hashlib.sha256(b'\xa5'+u32(len(chunk))+chunk).digest())
    return hashlib.sha256(b'\x5a'+u32(len(digests))+b''.join(digests)).digest()

def identity(path):
    pem=Path(path).read_bytes()
    key=serialization.load_pem_private_key(pem,password=None)
    cert=x509.load_pem_x509_certificate(pem[pem.index(b'-----BEGIN CERTIFICATE-----'):])
    assert key.public_key().public_numbers()==cert.public_key().public_numbers()
    return key,cert

def rebuild_and_sign(source,output,replacements,key_path,expected_fingerprint):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_name(output.name+'.unsigned.tmp')
    try:
        with zipfile.ZipFile(source) as src,zipfile.ZipFile(temp,'w',allowZip64=True) as dst:
            assert not (replacements.keys()-set(src.namelist())), 'Missing replacement path'
            for item in src.infolist():
                if is_signature(item.filename):continue
                info=copy.copy(item)
                data=replacements.get(item.filename)
                if data is None:data=src.read(item)
                if info.compress_type==zipfile.ZIP_STORED:
                    offset=dst.fp.tell()+30+len(info._encodeFilenameFlags()[0])+len(info.extra)
                    if offset%4:
                        pad=(-offset-4)%4
                        info.extra+=struct.pack('<HH',0xffff,pad)+bytes(pad)
                dst.writestr(info,data,compress_type=info.compress_type)
        raw=temp.read_bytes();e=raw.rfind(b'PK\x05\x06')
        assert e>=0 and e+22+struct.unpack_from('<H',raw,e+20)[0]==len(raw)
        cd=struct.unpack_from('<I',raw,e+16)[0];parts=(raw[:cd],raw[cd:e],raw[e:])
        key,cert=identity(key_path)
        assert cert.fingerprint(hashes.SHA256()).hex()==expected_fingerprint
        pub=key.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
        alg=0x0103;digests=lp(u32(alg)+lp(content_digest(parts)))
        signed=lp(digests)+lp(lp(cert.public_bytes(serialization.Encoding.DER)))+lp(b'')
        sig=key.sign(signed,padding.PKCS1v15(),hashes.SHA256())
        signer=lp(signed)+lp(lp(u32(alg)+lp(sig)))+lp(pub)
        value=lp(lp(signer));pair=u64(4+len(value))+u32(0x7109871a)+value
        size=len(pair)+24;block=u64(size)+pair+u64(size)+b'APK Sig Block 42'
        end=bytearray(parts[2]);struct.pack_into('<I',end,16,cd+len(block))
        output.write_bytes(parts[0]+block+parts[1]+end)
    finally:
        temp.unlink(missing_ok=True)

def verify_signature(path,expected_fingerprint):
    raw=Path(path).read_bytes();e=raw.rfind(b'PK\x05\x06');assert e>=0
    cd=struct.unpack_from('<I',raw,e+16)[0]
    assert raw[cd-16:cd]==b'APK Sig Block 42'
    size=struct.unpack_from('<Q',raw,cd-24)[0];start=cd-size-8
    assert struct.unpack_from('<Q',raw,start)[0]==size
    pairlen=struct.unpack_from('<Q',raw,start+8)[0]
    assert struct.unpack_from('<I',raw,start+16)[0]==0x7109871a
    value=memoryview(raw)[start+20:start+16+pairlen]
    def take(v):
        n=struct.unpack_from('<I',v)[0];assert len(v)>=4+n
        return v[4:4+n],v[4+n:]
    signers,_=take(value);signer,_=take(signers)
    signed,rest=take(signer);sigs,rest=take(rest);pub,_=take(rest)
    sigrec,_=take(sigs);assert struct.unpack_from('<I',sigrec)[0]==0x103
    sig,_=take(sigrec[4:])
    serialization.load_der_public_key(bytes(pub)).verify(bytes(sig),bytes(signed),padding.PKCS1v15(),hashes.SHA256())
    digests,rest=take(signed);certs,rest=take(rest);cert,_=take(certs)
    actual=x509.load_der_x509_certificate(bytes(cert));fp=actual.fingerprint(hashes.SHA256()).hex()
    assert fp==expected_fingerprint,'Certificate identity differs'
    assert actual.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)==bytes(pub)
    record,_=take(digests);stored,_=take(record[4:])
    end=bytearray(raw[e:]);struct.pack_into('<I',end,16,start)
    assert bytes(stored)==content_digest((raw[:start],raw[cd:e],end))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for ent in z.infolist():
            if ent.compress_type==zipfile.ZIP_STORED:
                namelen,extralen=struct.unpack_from('<HH',raw,ent.header_offset+26)
                assert (ent.header_offset+30+namelen+extralen)%4==0,ent.filename
    return {'certificate_sha256':fp,'apk_v2_signature':'PASS','content_digest':'PASS','zip_crc':'PASS','stored_entry_alignment':'4-byte PASS'}
