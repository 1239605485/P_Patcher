"""Read six specific JSON TextAssets from a user-supplied APK, without modifying it."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

TABLES=('world','strings_zh_tw','strings_zh_cn','strings_en_us','ui_zh_tw','ui_zh_cn')
ENTRY='assets/bin/Data/data.unity3d'


def pairs(items):
    out={}
    for k,v in items:
        if k in out:raise ValueError('duplicate JSON key '+k)
        out[k]=v
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apk',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():p.error('output must be a new directory')
    import UnityPy
    h=hashlib.sha256()
    with a.apk.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    with zipfile.ZipFile(a.apk) as z:
        if len([x for x in z.infolist() if x.filename==ENTRY])!=1:raise ValueError('missing or duplicate Unity bundle')
        bundle=z.read(ENTRY)
    env=UnityPy.load(bundle);result={}
    for obj in env.objects:
        if obj.type.name!='TextAsset':continue
        asset=obj.read()
        if asset.m_Name not in TABLES:continue
        if asset.m_Name in result:raise ValueError('duplicate TextAsset name: '+asset.m_Name)
        result[asset.m_Name]=json.loads(asset.m_Script,object_pairs_hook=pairs,
            parse_constant=lambda c:(_ for _ in ()).throw(ValueError('invalid JSON constant '+c)))
    if set(result)!=set(TABLES):raise ValueError('missing required TextAssets: '+str(sorted(set(TABLES)-set(result))))
    a.out.mkdir(parents=True)
    for name,value in result.items():
        (a.out/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (a.out/'extraction.json').write_text(json.dumps({'format':'mdz-table-extraction/1','apk_sha256':h.hexdigest(),
        'bundle_sha256':hashlib.sha256(bundle).hexdigest(),'tables':sorted(result),
        'status':'READ_ONLY_NO_APK_MODIFICATION'},indent=2),encoding='utf-8')
    print('提取完成:',len(result),'个表；源APK未修改。')


if __name__=='__main__':main()
