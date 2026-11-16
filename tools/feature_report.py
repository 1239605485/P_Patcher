"""Summarize source-bound version evidence; never applies or approves patches."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_CATALOG=ROOT/'feature_catalog/p14_155_test001.json'
NATIVE='lib/arm64-v8a/libil2cpp.so'
PRIORITY={'SOURCE_HOOK_BYTES_MISMATCH':0,'IDENTITY_MISMATCH':0,'DUPLICATE_SOURCE_SITE':0,
          'MISSING_OR_AMBIGUOUS_METHOD':1,'CONFLICTING_ALIAS_METHODS':1,'NO_EVIDENCE':1,
          'REVIEW_REQUIRED':2,'CONTEXT_CANDIDATE':3}


def read(path):
    raw=path.read_bytes()
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('duplicate JSON key in '+str(path)+': '+k)
            out[k]=v
        return out
    return json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs),hashlib.sha256(raw).hexdigest()


def make_report(catalog, inventory, evidence=None, anchor=None, digests=None):
    if catalog.get('format')!='mdz-feature-catalog/1':raise ValueError('unsupported catalog')
    if inventory.get('format')!='mdz-migration-inventory/1':raise ValueError('unsupported inventory')
    apk=inventory.get('apk_sha256')
    if not isinstance(apk,str) or len(apk)!=64:raise ValueError('invalid input APK identity')
    entries=inventory.get('entries',{})
    baseline=catalog['reference']['components']
    components={name:('missing' if name not in entries else
                      'unchanged' if entries[name]==old else 'changed') for name,old in baseline.items()}
    native=entries.get(NATIVE,{}).get('sha256')
    issues=[]
    evidence_bound=False
    if evidence is not None and anchor is not None:
        sin=evidence.get('inputs',{}).get('stable');tin=evidence.get('inputs',{}).get('new')
        evidence_bound=(evidence.get('status')=='PLAN_ONLY_NOT_APPLIED' and sin==catalog['source']['stable_apk_sha256']
            and tin==apk and anchor.get('format')=='mdz-native-migration-plan/1'
            and anchor.get('status')=='PLAN_ONLY_NOT_APPLIED' and anchor.get('release_ready') is False
            and anchor.get('source_binary_sha256')==catalog['source']['stable_native_sha256']
            and native and anchor.get('target_binary_sha256')==native
            and anchor.get('source_hooks_sha256')==catalog['evidence_sha256']['hook_source'])
        if not evidence_bound:issues.append('迁移证据与当前 APK、旧版 native 或钩子清单哈希不一致；不可使用其候选地址。')
    else:issues.append('尚无身份绑定的钩子扫描结果；先运行 prepare_version.py。')
    indexed=collections.defaultdict(list)
    if evidence_bound:
        for a in anchor.get('anchors',[]):indexed[a.get('source_site')].append(a)
    groups={}
    checks=[]
    for hook in catalog['hooks']:
        ident=hook['identity'];key=tuple(ident[k] for k in ('assembly','type','method','params'))
        result={'source_site':hook['source_site'],'identity':ident,'state':'NO_EVIDENCE'}
        if apk==catalog['reference']['author_apk_sha256']:
            result['historical_reference']={'decision':hook.get('reference_decision'),
                'candidate_site':hook.get('reference_new_site'),'proof':hook.get('reference_proof',''),
                'scope':'THIS_EXACT_APK_NOT_RUNTIME_VERIFIED'}
        rows=indexed.get(hook['source_site'],[])
        if len(rows)>1:result['state']='DUPLICATE_SOURCE_SITE'
        elif len(rows)==1:
            row=rows[0];state=row.get('status','NO_EVIDENCE')
            valid={'SOURCE_HOOK_BYTES_MISMATCH','MISSING_OR_AMBIGUOUS_METHOD','CONFLICTING_ALIAS_METHODS','REVIEW_REQUIRED','CONTEXT_CANDIDATE'}
            if state not in valid:state='NO_EVIDENCE'
            if state in ('REVIEW_REQUIRED','CONTEXT_CANDIDATE'):
                method=row.get('source_method',{})
                same=tuple(method.get(k) for k in ('assembly','type','method','params'))==key
                target=row.get('target_site')
                if (not same or row.get('source_hook_bytes_verified') is not True or
                    type(target) is not int or target<0 or target%4):state='IDENTITY_MISMATCH'
                else:
                    # Candidate goes only in full evidence, not as a patch or success state.
                    result['candidate_site']=target
                    result['context_score']=row.get('context_score')
            result['state']=state
        checks.append(result)
        group=groups.setdefault(key,{'identity':ident,'counts':collections.Counter(),'source_sites':[]})
        group['counts'][result['state']]+=1;group['source_sites'].append(hook['source_site'])
    for g in groups.values():g['counts']=dict(g['counts'])
    native_same=bool(native and native==catalog['reference']['native_sha256'])
    reference_same=apk==catalog['reference']['author_apk_sha256']
    report={'format':'mdz-feature-report/1','status':'ANALYSIS_ONLY_NEVER_INSTALLABLE',
        'catalog_id':catalog['catalog_id'],'target_apk_sha256':apk,'evidence_bound':bool(evidence_bound),
        'evidence_digests':digests or {},'reference_apk_same':reference_same,
        'previous_reference_review':({'counts':dict(collections.Counter(h['reference_decision'] for h in catalog['hooks'])),
            'device_test':catalog['reference']['device_test'],
            'note':'Historical review for this exact author APK, not a new runtime test or automatic patch permission.'}
            if reference_same else None),
        'components':components,'known_native_same_bytes':native_same,'issues':issues,
        'hook_counts':dict(collections.Counter(x['state'] for x in checks)),
        'method_groups':list(groups.values()),'hooks':checks,
        'direct_edits':{'recorded_count':len(catalog['direct_edits'])+len(catalog['additional_recorded_edits']),
            'status':'REFERENCE_BYTES_MATCH_RECHECK_PREIMAGES' if native_same else 'NEW_VERSION_MANUAL_REVIEW_REQUIRED'},
        'data':{'audited_paths':len(catalog['data']['audited_changed_paths']),
            'status':'REFERENCE_DATA_UNCHANGED' if components.get('assets/bin/Data/data.unity3d')=='unchanged' else 'THREE_WAY_MERGE_REQUIRED'},
        'release_gates':{'signature':'NOT_CHECKED','native_abi_and_calls':'NOT_CHECKED',
            'data_integration':'NOT_CHECKED','android_device':'NOT_RUN'},
        'limitations':['Legacy parameter names do not establish full types or calling convention.',
            'A context candidate is not a validated offset, an installed feature, or release authorization.',
            'Same component bytes do not prove complete APK compatibility or runtime behavior.']}
    return report


def compact(report,limit=12):
    lines=['P14 版本迁移分析（只读，不生成补丁）',
           '目标 APK SHA256: '+report['target_apk_sha256'],
           '与已记录 1.5.5 原版完全相同: '+('是' if report['reference_apk_same'] else '否'),
           '钩子扫描证据身份: '+('已绑定' if report['evidence_bound'] else '未绑定'),
           '关键文件: '+', '.join(name.rsplit('/',1)[-1]+'='+state for name,state in report['components'].items()),
           ('本次钩子扫描: 未运行；仅参考历史复核' if report.get('reference_note') else
            '钩子统计: '+json.dumps(report['hook_counts'],ensure_ascii=False,sort_keys=True)),
           '直接指令: '+report['direct_edits']['status']+'；数据: '+report['data']['status']]
    lines += ['阻碍: '+x for x in report['issues']]
    if report.get('reference_note'):lines.append(report['reference_note'])
    if report['previous_reference_review'] is not None:
        previous=report['previous_reference_review']
        lines.append('该完整 APK 的历史静态复核: '+json.dumps(previous['counts'],ensure_ascii=False,sort_keys=True)+'；真机测试 '+previous['device_test'])
    groups=sorted(report['method_groups'],key=lambda g:(min(PRIORITY.get(k,9) for k in g['counts']),g['identity']['type'],g['identity']['method']))
    if report.get('reference_note'):
        lines.append('历史逐项记录见 report.json；需要重新检查时使用 --force-analysis。')
    else:
        lines.append('优先查看的方法（候选均需复核；完整列表在 report.json）：')
        for g in groups[:limit]:
            i=g['identity'];lines.append('- '+i['type']+'.'+i['method']+'('+i['params']+'): '+
                                          ', '.join(k+'='+str(v) for k,v in sorted(g['counts'].items())))
        if len(groups)>limit:lines.append('其他方法组: '+str(len(groups)-limit))
    lines+=['必要步骤：核对完整参数/返回类型、字段、调用和分支；完成数据合并与真机测试。',
            '本报告不应用地址，不修改APK，也不证明兼容或游戏功能可用。']
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inventory',type=Path,required=True,help='new/inventory.json or migration_audit inventory.json')
    p.add_argument('--evidence-dir',type=Path,help='prepare_version output containing status.json and anchors.json')
    p.add_argument('--catalog',type=Path,default=DEFAULT_CATALOG)
    p.add_argument('--out',type=Path,required=True,help='new report directory')
    a=p.parse_args()
    if a.out.exists():p.error('output directory must be new')
    catalog,catsha=read(a.catalog);inv,invsha=read(a.inventory)
    ev=anc=None;digests={'catalog_sha256':catsha,'inventory_sha256':invsha}
    if a.evidence_dir:
        ev,evsha=read(a.evidence_dir/'status.json');anc,ancsha=read(a.evidence_dir/'anchors.json')
        digests.update(status_sha256=evsha,anchors_sha256=ancsha)
    report=make_report(catalog,inv,ev,anc,digests)
    a.out.mkdir(parents=True)
    (a.out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    text=compact(report)
    (a.out/'精简诊断报告.txt').write_text(text,encoding='utf-8')
    print(text)


if __name__=='__main__':main()
