"""Build signed external engine and real JSON-rule feature ZIPs. No game assets embedded."""
import argparse, hashlib, json, zipfile, subprocess, os, shutil
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import UnityPy
from UnityPy.files.ObjectReader import ObjectReader
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parent
sha=lambda b:hashlib.sha256(b).hexdigest()
raw=lambda x:json.dumps(x,ensure_ascii=False,separators=(',',':')).encode()
FP='21fa47120af53f71b39e886eaf0d71a159c34a2d332646a1cf0820a59549ad10'
def diff(a,b,path=()):
    if type(a)==type(b) and isinstance(a,dict):
        for k in sorted(a.keys()|b.keys()):
            if k not in a: yield {'path':list(path+(k,)),'after':b[k]}
            elif k not in b: yield {'path':list(path+(k,)),'before':a[k],'remove':True}
            else: yield from diff(a[k],b[k],path+(k,))
    elif type(a)==type(b) and isinstance(a,list) and len(b)>len(a) and a and all(isinstance(v,dict) for v in a+b) and any(all(k in v for v in a+b) and [v[k] for v in a]==[v[k] for v in b[:len(a)]] for k in ('Id','OutputItem')):
        field=next(k for k in ('Id','OutputItem') if all(k in v for v in a+b) and [v[k] for v in a]==[v[k] for v in b[:len(a)]])
        for i,(x,y) in enumerate(zip(a,b)):yield from diff(x,y,path+(str(i),))
        for item in b[len(a):]:yield {'path':list(path),'append':item,'key_field':field,'key_value':str(item[field])}
    elif type(a)==type(b) and isinstance(a,list) and len(a)==len(b):
        for i,(x,y) in enumerate(zip(a,b)):yield from diff(x,y,path+(str(i),))
    elif a!=b:yield {'path':list(path),'before':a,'after':b}
def main():
    p=argparse.ArgumentParser();p.add_argument('--key',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--base-apk',type=Path,required=True);p.add_argument('--target-bundle',type=Path,required=True);p.add_argument('--native-module',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    key=serialization.load_pem_private_key(a.key.read_bytes(),None)
    def signed(path,kind,meta,files):
        data=raw(meta)
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            z.writestr(kind+'.json',data);z.writestr(kind+'.sig',key.sign(data,padding.PKCS1v15(),hashes.SHA256()))
            for n,b in files.items():z.writestr(n,b)
    positions={}
    original=ObjectReader.from_reader.__func__
    def capture(cls,af,r):
        obj=original(cls,af,r)
        # version >=22: aligned path64, offset64, size32, type32.
        if af.header.version>=22:positions[(af.name,obj.path_id)]=(r.Position-16,r.Position-8)
        return obj
    ObjectReader.from_reader=classmethod(capture)
    with zipfile.ZipFile(a.base_apk) as z:base=z.read('assets/bin/Data/data.unity3d')
    before=UnityPy.load(base)
    locators={}
    objects={}
    names={'world','strings_zh_tw','strings_zh_cn','strings_en_us','ui_zh_tw','ui_zh_cn'}
    for o in before.objects:
        if o.type.name!='TextAsset':continue
        asset=o.read()
        if asset.m_Name not in names:continue
        af=o.assets_file
        off,sz=positions[(af.name,o.path_id)]
        locators[asset.m_Name]={'node':af.name,'path_id':str(o.path_id),'start':o.byte_start,'size':o.byte_size,'sha256':sha(o.get_raw_data()),'offset_field':off,'size_field':sz,'offset_width':8,'data_offset':af.header.data_offset,'file_size_field':24,'file_size_width':8,'little':af.header.endian=='<'}
        objects[asset.m_Name]=json.loads(asset.m_Script)
    ObjectReader.from_reader=classmethod(original)
    target=UnityPy.load(str(a.target_bundle))
    groups={}
    for o in target.objects:
        if o.type.name!='TextAsset':continue
        asset=o.read()
        if asset.m_Name not in names:continue
        for rule in diff(objects[asset.m_Name],json.loads(asset.m_Script)):
            rule['object']=asset.m_Name
            if asset.m_Name!='world':ident='localization-'+asset.m_Name
            elif rule['path'][0]=='AreaPresetDatabase':ident='loot-guaranteed'
            elif rule['path'][0]=='ItemDatabase' and not rule.get('append'):ident='disassembly-returns'
            else:ident='crafting-and-custom-items'
            groups.setdefault(ident,[]).append(rule)
    build=ROOT/'build/engine';build.mkdir(parents=True,exist_ok=True)
    tools=ROOT/'toolchain'
    subprocess.run(['java','-jar',str(tools/'ecj.jar'),'-8','-warn:none','-encoding','UTF-8','-cp',str(tools/'json.jar'),'-d',str(build),str(ROOT/'engine-src/mdz/engine/UnityEngine.java')],check=True)
    jar=build/'engine.jar'
    with zipfile.ZipFile(jar,'w') as z:
        for f in build.rglob('*.class'):z.write(f,f.relative_to(build).as_posix())
    dex=build/'dex';dex.mkdir(exist_ok=True)
    subprocess.run(['java','-cp',str(tools/'r8.jar'),'com.android.tools.r8.D8','--min-api','26','--lib',str(tools/'android.jar'),'--output',str(dex),str(jar)],check=True)
    mapping={'input_sha256':sha(base),'objects':locators}
    (build/'map.json').write_bytes(raw(mapping))
    all_rules=[r for k in sorted(groups) for r in groups[k]]
    (build/'rules.json').write_bytes(raw(all_rules))
    (build/'input.unity3d').write_bytes(base)
    files={'classes.dex':(dex/'classes.dex').read_bytes(),'locators.json':raw(mapping)}
    engine={'format':'mdz-engine/1','id':'unityfs-json-155','version':'1.0.0','api':1,'entry_class':'mdz.engine.UnityEngine','name':'UnityFS JSON 定位与重建 · 作者1.5.5','signer_sha256':FP,'files':{n:{'size':len(b),'sha256':sha(b)} for n,b in files.items()}}
    signed(a.out/'引擎包_1.5.5.zip','engine',engine,files)
    old=a.native_module
    with zipfile.ZipFile(old) as z:
        oldmeta=json.loads(z.read('module.json'));profile=oldmeta['profiles'][0]
        ops=[op for m in profile['modules'] for op in m['operations'] if op['entry']!='assets/bin/Data/data.unity3d' and not op['entry'].startswith('assets/diagnostics/')]
        # All native hooks and Android isolation plumbing are coupled. Keep honest atomic dependency.
        core=dict(oldmeta);core.pop('assistant',None);core['engine_min']=3;core['name']='原生功能与隔离基础（不可拆分依赖）';core['version']='1.6.0';profile=dict(profile);profile['modules']=[{'id':'isolation-core','name':core['name'],'mandatory':True,'depends_on':[],'operations':ops}];core['profiles']=[profile]
        refs={c['data'] for op in ops for c in op['commands'] if 'data' in c};core['payloads']={n:v for n,v in oldmeta['payloads'].items() if n in refs}
        corefiles={n:z.read(n) for n in refs}
    features=a.out/'功能分包';shutil.rmtree(features,ignore_errors=True);features.mkdir(exist_ok=True)
    signed(features/'00_原生与隔离基础.zip','module',core,corefiles)
    catalog=[{'file':'00_原生与隔离基础.zip','id':'isolation-core','name':core['name'],'required':True}]
    labels={'world':'世界数据','localization':'翻译'}
    for index,ident in enumerate(sorted(groups),1):
        name={'loot-guaranteed':'地图物品掉落概率调整','disassembly-returns':'物品拆解回收调整','crafting-and-custom-items':'制作配方与配套新增物品','localization-strings_en_us':'英文物品说明','localization-strings_zh_cn':'简体中文物品说明','localization-strings_zh_tw':'繁体中文物品说明','localization-ui_zh_cn':'简体中文界面','localization-ui_zh_tw':'繁体中文界面'}[ident]
        meta={'format':'mdz-feature/1','id':ident,'name':name,'version':'1.0.0','engine_id':engine['id'],'depends_on':['isolation-core'],'signer_sha256':FP,'rules':groups[ident]}
        filename=f'{index:02d}_{ident}.zip';signed(features/filename,'feature',meta,{})
        catalog.append({'file':filename,'id':ident,'name':name,'rules':len(groups[ident])})
    bundle={'format':'mdz-bundle/1','name':'MiniDayZ2 1.5.5 功能整合包','version':'1.6.0','engine_id':engine['id'],'signer_sha256':FP,'features':[]}
    content={}
    for item in catalog:
        data=(features/item['file']).read_bytes();path='features/'+item['file'];content[path]=data;bundle['features'].append(dict(item,path=path,size=len(data),sha256=sha(data)))
    signed(a.out/'插件总包_1.5.5.zip','bundle',bundle,content)
    (a.out/'功能清单.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    print('features',len(catalog),'rules',len(all_rules),'sizes',[(p.name,p.stat().st_size) for p in a.out.glob('*.zip')])
if __name__=='__main__':main()
