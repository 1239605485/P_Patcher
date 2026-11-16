"""Split a signed module into isolation-core plus one functional module.

The result keeps the original payloads and profile hashes. Each output is
re-signed with the supplied P identity, so the Android installer can verify it
without adding a new installation path.
"""
import argparse, hashlib, json, zipfile
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.hashes import SHA256

def sha(b): return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--module',type=Path,required=True);p.add_argument('--key',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--module-id');p.add_argument('--all',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.module) as z:
        raw=z.read('module.json'); meta=json.loads(raw.decode('utf-8'))
        ids=[a.module_id] if a.module_id else ['native-features','data-features','diagnostic-resources']
        selected=[]
        for profile in meta.get('profiles',[]):
            mods=profile.get('modules',[]); core=next((m for m in mods if m.get('id')=='isolation-core'),None); source=next((m for m in mods if m.get('id')=='p14-features'),None)
            if core is None or source is None: raise SystemExit(f'profile {profile.get("id")} lacks source modules')
            for mid in ids:
                if mid=='native-features': entries={'lib/arm64-v8a/libil2cpp.so'}
                elif mid=='data-features': entries={'assets/bin/Data/data.unity3d'}
                else: entries={'AndroidManifest.xml','assets/diagnostics/README.txt','assets/diagnostics/build_info.json','assets/diagnostics/data_reference.json','classes.dex','classes2.dex','res/xml/p13_isolation_backup.xml','resources.arsc'}
                feature=json.loads(json.dumps(source));feature['id']=mid;feature['name']={'native-features':'原生功能移植','data-features':'Unity 数据功能','diagnostic-resources':'隔离与诊断资源'}[mid];feature['operations']=[op for op in feature['operations'] if op.get('entry') in entries]; clone=json.loads(json.dumps(profile));clone['modules']=[core,feature]; selected.append((mid,clone))
        if not selected: raise SystemExit('no matching profiles')
        if a.all:
            for mid,_ in selected: pass
            print('Use --module-id for one package; --all is reserved for bundle generation.'); return
        mid,profile=selected[0];outmeta=dict(meta);outmeta['profiles']=[profile];outmeta['split_from']=sha(raw);outmeta['split_module_id']=mid
        refs=set()
        for m in profile['modules']:
            for op in m.get('operations',[]):
                for cmd in op.get('commands',[]):
                    if 'data' in cmd: refs.add(cmd['data'])
        outmeta['payloads']={k:v for k,v in meta.get('payloads',{}).items() if k in refs}
        newraw=json.dumps(outmeta,ensure_ascii=False,indent=2,separators=(',', ': ')).encode()
        key=serialization.load_pem_private_key(a.key.read_bytes(),password=None)
        sig=key.sign(newraw,padding.PKCS1v15(),SHA256())
        out=a.out/(mid+'.zip')
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as w:
            for info in z.infolist():
                if info.filename in ('module.json','module.sig'): continue
                if info.filename.startswith('payload/') and info.filename not in refs: continue
                w.writestr(info,z.read(info.filename))
            w.writestr('module.json',newraw);w.writestr('module.sig',sig)
        (a.out/(mid+'.json')).write_text(json.dumps({'module_id':mid,'source':str(a.module),'source_sha256':sha(a.module.read_bytes()),'output':str(out),'output_sha256':sha(out.read_bytes()),'profiles':1},ensure_ascii=False,indent=2),encoding='utf-8')
        print(out)
if __name__=='__main__': main()
