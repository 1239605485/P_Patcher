"""Make a source-bound P14 evidence catalog from the completed 1.5.5 work files.

This is a development tool. Its output records evidence, never authorizes or
applies a patch. It requires the exact original reports, not an APK or key.
"""
import argparse
import hashlib
import json
from pathlib import Path

STABLE = 'ddf98eb02765129d8630cef0cf4f59f05560f35780305f3468cc53ea5fd3c371'
AUTHOR = '4a9614f1fa17215f52e807c8c2055ee68f64e3401f6facd0acec7cac72c203fe'
OLD_NATIVE = '5c88dd932fcb0d626f731ab54f897d8a80ddab4372da75c5a6b0af04c32466f6'
NEW_NATIVE = '127990c580d3e44e54f2e4febe7845cf98876802f2f88137fc4e9c185d80a0d0'


def read(path):
    raw = path.read_bytes()
    return json.loads(raw.decode('utf-8-sig')), hashlib.sha256(raw).hexdigest()


def json_fingerprint(value):
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def build(root):
    paths = {'decisions':'port155/native_review/final_hook_decisions.json',
             'direct':'port155/direct_features/direct_feature_plan.json',
             'data':'port155/data/data_port_report.json',
             'audited_paths':'MiniDayZ2_0.1.54_Port/analysis/table_merge_report.json',
             'inventory':'reports_155/inventory.json',
             'fields':'port155/native_review/generator_field_edits.json',
             'embedded_direct':'port155/native_review/embedded_original_patches.json',
             'hook_source':'MiniDayZ2_0.1.54_Port/analysis/injection_hooks.json',
             'verification':'port155/verification_summary.json'}
    files, digests = {}, {}
    for name, rel in paths.items():files[name],digests[name]=read(root/rel)
    d,p,data,a,inv,verify=(files[k] for k in ('decisions','direct','data','audited_paths','inventory','verification'))
    if (verify['stable_p14_apk_sha256']!=STABLE or verify['source_apk_sha256']!=AUTHOR or
        inv['apk_sha256']!=AUTHOR or p['source_native_sha256']!=OLD_NATIVE or p['target_native_sha256']!=NEW_NATIVE):
        raise ValueError('Input reports are not the expected P14 and 1.5.5 build')
    if (len(d['decisions'])!=116 or len({x['old_site'] for x in d['decisions']})!=116 or
        {int(x['site'],16) for x in files['hook_source']}!={x['old_site'] for x in d['decisions']}):
        raise ValueError('hook evidence incomplete or duplicated')
    paths=a['changed_paths']
    if len(paths)!=3090 or len(set(paths))!=3090:
        raise ValueError('audited data paths incomplete or duplicated')
    hooks=[]
    for x in d['decisions']:
        method=x['method']
        hooks.append({'source_site':x['old_site'],'payload_target':x['payload_target'],'kind':x['kind'],
                      'identity':{k:method[k] for k in ('assembly','type','method','params')},
                      'reference_decision':x['decision'],'reference_new_site':x.get('new_site'),
                      'reference_proof':x.get('proof','')})
    direct=[]
    for item in p['patches']:
        direct.append({k:item[k] for k in ('feature','source_site','new_site','before','after','method')})
    entries=inv['entries']
    components={name:entries[name] for name in ('lib/arm64-v8a/libil2cpp.so',
        'assets/bin/Data/Managed/Metadata/global-metadata.dat','assets/bin/Data/data.unity3d','classes.dex','AndroidManifest.xml')}
    table_names=('world','strings_zh_tw','strings_zh_cn','strings_en_us','ui_zh_tw','ui_zh_cn')
    table_fingerprints={}
    for role,folder in (('reference','reference_base'),('stable','p14')):
        table_fingerprints[role]={name:json_fingerprint(read(root/'port155/data'/folder/(name+'.json'))[0])
                                  for name in table_names}
    embedded=[{'source_site':x['site'],'reference_target_site':x.get('new_context_alignment',{}).get('target_site'),
               'stable_instruction':x['actual_stable_instruction'],'record_path':x['path']}
              for x in files['embedded_direct'] if not x['is_external_hook']]
    return {'format':'mdz-feature-catalog/1','catalog_id':'p14-stable-to-155-test001',
        'source':{'stable_apk_sha256':STABLE,'stable_native_sha256':OLD_NATIVE,
                  'identity_quality':'legacy_parameter_names_only_not_complete_abi'},
        'reference':{'author_apk_sha256':AUTHOR,'native_sha256':NEW_NATIVE,'components':components,
                     'status':'EXPERIMENTAL_TEST_BUILD','device_test':'NOT_RUN',
                     'original_input_sha256':data['input_apk_sha256']},
        'evidence_sha256':digests,'hooks':hooks,'direct_edits':direct,
        'additional_recorded_edits':embedded,'generator_field_edits':files['fields']['edits'],
        'data':{'audited_changed_paths':paths,'applied_counts':data['applied_counts'],
                'reference_scope':data['reference_scope'],'table_content_sha256':table_fingerprints,
                'device_test':'NOT_RUN'},
        'limitations':['This catalog is descriptive, not a runnable or signed patch.',
          'Source hook identities contain parameter names, not full types or return types.',
          'Direct edit addresses are scoped to the reference native SHA256.',
          'Recorded methods do not prove the full function inventory or future compatibility.',
          'Packaging/signing and Android runtime tests are separate requirements.']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():p.error('output must be a new file')
    catalog=build(a.evidence_root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Catalog created:',len(catalog['hooks']),'hooks,',len(catalog['direct_edits']),
          'direct edits,',len(catalog['data']['audited_changed_paths']),'audited data paths')


if __name__=='__main__':main()
