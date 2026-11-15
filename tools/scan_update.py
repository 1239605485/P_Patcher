"""Single entry point for a compact, source-bound update report; read-only."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from migration_audit import inventory
from feature_report import read, make_report, compact, DEFAULT_CATALOG


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--new-apk',type=Path,required=True)
    p.add_argument('--stable-apk',type=Path,help='original stable P14 APK; needed to scan a new native version')
    p.add_argument('--catalog',type=Path,default=DEFAULT_CATALOG)
    p.add_argument('--force-analysis',action='store_true',help='also rescan a known identical reference APK')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():p.error('output directory must be new')
    if a.force_analysis and a.stable_apk is None:p.error('--force-analysis needs --stable-apk')
    catalog,catsha=read(a.catalog)
    target=inventory(a.new_apk)
    a.out.mkdir(parents=True)
    inventory_path=a.out/'inventory.json'
    inventory_path.write_text(json.dumps(target,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    _,invsha=read(inventory_path)
    ev=anc=None;digests={'catalog_sha256':catsha,'inventory_sha256':invsha}
    is_reference=target['apk_sha256']==catalog['reference']['author_apk_sha256']
    if a.stable_apk and (not is_reference or a.force_analysis):
        env=os.environ.copy();env['PYTHONUTF8']='1'
        tool=Path(__file__).with_name('prepare_version.py')
        proc=subprocess.run([sys.executable,str(tool),'--stable-apk',str(a.stable_apk),'--new-apk',str(a.new_apk),
                             '--out',str(a.out/'evidence')],capture_output=True,text=True,encoding='utf-8',errors='replace',env=env)
        (a.out/'scan.log').write_text(proc.stdout+'\n'+proc.stderr,encoding='utf-8')
        if proc.returncode:
            (a.out/'status.json').write_text(json.dumps({'status':'FAILED_NOT_RELEASEABLE','exit_code':proc.returncode},indent=2),encoding='utf-8')
            raise SystemExit('扫描未完成，请查看 scan.log。没有产生适配方案。')
        ev,evsha=read(a.out/'evidence/status.json');anc,ancsha=read(a.out/'evidence/anchors.json')
        digests.update(status_sha256=evsha,anchors_sha256=ancsha)
    report=make_report(catalog,target,ev,anc,digests)
    if is_reference and ev is None:
        report['issues']=[]
        report['reference_note']='目标与已记录的 1.5.5 原版完全一致；本次只查阅历史静态记录，没有重新扫描。'
    (a.out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    text=compact(report)
    (a.out/'给AI的精简报告.txt').write_text(text,encoding='utf-8')
    (a.out/'status.json').write_text(json.dumps({'status':'ANALYSIS_ONLY','target_apk_sha256':target['apk_sha256'],
        'full_scan':ev is not None,'device_test':'NOT_RUN'},indent=2),encoding='utf-8')
    print(text)


if __name__=='__main__':main()
