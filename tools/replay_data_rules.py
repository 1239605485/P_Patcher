"""Replay cataloged JSON edits as a conservative three-way, ID-aware draft."""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from merge_feature_data import same, load

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'feature_catalog/p14_155_test001.json'
MISSING=object()
ID_KEYS={'Id','BuildingId','OutputItem','ItemId','StringId','Name','name','Key'}


def fingerprint(obj):
    raw=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def list_index(rows,token):
    if '=' not in token:raise ValueError('list path lacks stable ID')
    key,val=token.split('=',1)
    if key not in ID_KEYS:raise ValueError('unsupported list identity: '+key)
    candidates=[val]
    if val.lstrip('-').isdigit():candidates.append(int(val))
    hits=[i for i,row in enumerate(rows) if isinstance(row,dict) and key in row and
          any(type(row[key]) is type(c) and row[key]==c for c in candidates)]
    if len(hits)>1:raise ValueError('ambiguous list identity: '+token)
    return hits[0] if hits else None


def get(tree,tokens):
    for token in tokens:
        if tree is MISSING:return MISSING
        if isinstance(tree,dict):tree=tree.get(token,MISSING)
        elif isinstance(tree,list):
            index=list_index(tree,token)
            tree=MISSING if index is None else tree[index]
        else:return MISSING
    return tree


def put(tree,tokens,value):
    parent=get(tree,tokens[:-1])
    if parent is MISSING:raise ValueError('missing patch parent')
    last=tokens[-1]
    if isinstance(parent,dict):parent[last]=copy.deepcopy(value)
    elif isinstance(parent,list):
        index=list_index(parent,last)
        if index is None:parent.append(copy.deepcopy(value))
        else:parent[index]=copy.deepcopy(value)
    else:raise ValueError('patch parent is not a container')


def summary(value):
    if value is MISSING:return {'present':False}
    text=json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    return {'present':True,'sha256':fingerprint(value),'preview':text[:180],
            'truncated':len(text)>180}


def replay(catalog,base,feature,author):
    if catalog.get('format')!='mdz-feature-catalog/1':raise ValueError('unsupported catalog')
    expected=catalog['data']['table_content_sha256']
    names=set(expected['reference'])
    if names!=set(expected['stable']) or any(set(x)!=names for x in (base,feature,author)):
        raise ValueError('expected complete six-table sets')
    for role,values in (('reference',base),('stable',feature)):
        for name in names:
            if fingerprint(values[name])!=expected[role][name]:
                raise ValueError(role+' table identity mismatch: '+name)
    paths=catalog['data']['audited_changed_paths']
    if len(paths)!=len(set(paths)):raise ValueError('duplicate audited path')
    merged=copy.deepcopy(author);counts={'applied':0,'already_present':0,'unowned':0};conflicts=[]
    for path in paths:
        table,sep,key=path.partition('/')
        if not sep or table not in names or not key:raise ValueError('invalid audited path: '+path)
        tokens=key.split('/') if table=='world' else [key]
        try:
            before,desired,current=[get(x[table],tokens) for x in (base,feature,author)]
            if desired is MISSING:
                reason='feature value missing; deletion requires review'
            elif same(before,desired):counts['unowned']+=1;continue
            elif same(current,desired):counts['already_present']+=1;continue
            elif same(before,current):
                put(merged[table],tokens,desired);counts['applied']+=1;continue
            else:reason='author and feature both changed value'
        except ValueError as e:
            conflicts.append({'path':path,'reason':str(e)});continue
        conflicts.append({'path':path,'reason':reason,'base':summary(before),'feature':summary(desired),'author':summary(current)})
    report={'format':'mdz-data-replay/1','status':'CONFLICT' if conflicts else 'DATA_DRAFT_NOT_GAME_TESTED',
        'catalog_id':catalog['catalog_id'],'author_table_sha256':{k:fingerprint(v) for k,v in author.items()},
        'counts':counts,'conflicts':conflicts,'conflict_count':len(conflicts),
        'limitations':['Only catalog paths are replayed; previous manual conflict resolutions are not reused.',
            'No Unity bundle, APK, native code or signed module is created.',
            'A draft still requires semantic review, integration and device testing.']}
    return merged,report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for role in ('base','feature','author','out'):p.add_argument('--'+role,type=Path,required=True)
    p.add_argument('--catalog',type=Path,default=DEFAULT)
    a=p.parse_args()
    if a.out.exists():p.error('output directory must be new')
    catalog=load(a.catalog);names=catalog['data']['table_content_sha256']['reference']
    if not all(re.fullmatch(r'[A-Za-z0-9_]+',name) for name in names):
        raise ValueError('invalid table name in catalog')
    inputs=[{name:load(getattr(a,role)/(name+'.json')) for name in names} for role in ('base','feature','author')]
    merged,report=replay(catalog,*inputs)
    a.out.mkdir(parents=True)
    (a.out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if report['conflicts']:
        print('检测到冲突，未写入合并表。冲突数:',len(report['conflicts']))
        raise SystemExit(2)
    tables=a.out/'tables';tables.mkdir()
    for name,value in merged.items():
        (tables/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('已生成仅供检查的数据草稿；未生成 APK。',report['counts'])


if __name__=='__main__':main()
