import copy
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import feature_report
import replay_data_rules as replay
import migration_audit


class FeatureWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.base={'world':{'items':[{'Id':1,'amount':1}]},'text':{'a/b':'old'}}
        self.feature={'world':{'items':[{'Id':1,'amount':2}]},'text':{'a/b':'new'}}
        self.author=copy.deepcopy(self.base)
        self.catalog={'format':'mdz-feature-catalog/1','catalog_id':'fixture',
            'source':{'stable_apk_sha256':'a'*64,'stable_native_sha256':'b'*64},
            'reference':{'author_apk_sha256':'c'*64,'native_sha256':'d'*64,'device_test':'NOT_RUN','components':{
                feature_report.NATIVE:{'size':4,'sha256':'d'*64},
                'assets/bin/Data/data.unity3d':{'size':8,'sha256':'e'*64}}},
            'evidence_sha256':{'hook_source':'f'*64},
            'hooks':[{'source_site':100,'reference_decision':'MAP','identity':{'assembly':'A','type':'T','method':'M','params':'arg'}}],
            'direct_edits':[],'additional_recorded_edits':[],
            'data':{'audited_changed_paths':['world/items/Id=1/amount','text/a/b'],
                'table_content_sha256':{'reference':{k:replay.fingerprint(v) for k,v in self.base.items()},
                                         'stable':{k:replay.fingerprint(v) for k,v in self.feature.items()}}}}
        self.inventory={'format':'mdz-migration-inventory/1','apk_sha256':'c'*64,
            'entries':{feature_report.NATIVE:{'size':4,'sha256':'d'*64},
                       'assets/bin/Data/data.unity3d':{'size':8,'sha256':'e'*64}}}
        self.evidence={'status':'PLAN_ONLY_NOT_APPLIED','inputs':{'stable':'a'*64,'new':'c'*64}}
        self.anchor={'format':'mdz-native-migration-plan/1','status':'PLAN_ONLY_NOT_APPLIED','release_ready':False,
            'source_binary_sha256':'b'*64,'target_binary_sha256':'d'*64,'source_hooks_sha256':'f'*64,
            'anchors':[{'source_site':100,'source_method':{'assembly':'A','type':'T','method':'M','params':'arg'},
                'source_hook_bytes_verified':True,'target_site':200,'status':'CONTEXT_CANDIDATE'}]}

    def test_bound_candidate_remains_review_only(self):
        report=feature_report.make_report(self.catalog,self.inventory,self.evidence,self.anchor)
        self.assertTrue(report['evidence_bound'])
        self.assertEqual(report['hooks'][0]['state'],'CONTEXT_CANDIDATE')
        self.assertEqual(report['release_gates']['android_device'],'NOT_RUN')
        self.assertNotIn('candidate_site',feature_report.compact(report))

    def test_mismatched_binary_or_legacy_report_cannot_release_offset(self):
        self.anchor['target_binary_sha256']='9'*64
        report=feature_report.make_report(self.catalog,self.inventory,self.evidence,self.anchor)
        self.assertFalse(report['evidence_bound'])
        self.assertEqual(report['hooks'][0]['state'],'NO_EVIDENCE')
        self.assertNotIn('candidate_site',report['hooks'][0])
        del self.anchor['target_binary_sha256']
        self.assertFalse(feature_report.make_report(self.catalog,self.inventory,self.evidence,self.anchor)['evidence_bound'])

    def test_duplicate_or_wrong_method_is_blocked(self):
        self.anchor['anchors'].append(copy.deepcopy(self.anchor['anchors'][0]))
        report=feature_report.make_report(self.catalog,self.inventory,self.evidence,self.anchor)
        self.assertEqual(report['hooks'][0]['state'],'DUPLICATE_SOURCE_SITE')
        self.anchor['anchors'].pop();self.anchor['anchors'][0]['source_method']['method']='Other'
        report=feature_report.make_report(self.catalog,self.inventory,self.evidence,self.anchor)
        self.assertEqual(report['hooks'][0]['state'],'IDENTITY_MISMATCH')
        self.assertNotIn('candidate_site',report['hooks'][0])

    def test_data_merge_preserves_author_additions_and_key_with_slash(self):
        self.author['world']['items'].append({'Id':2,'amount':9})
        merged,report=replay.replay(self.catalog,self.base,self.feature,self.author)
        self.assertEqual(report['conflict_count'],0)
        self.assertEqual(merged['world']['items'],[{'Id':1,'amount':2},{'Id':2,'amount':9}])
        self.assertEqual(merged['text']['a/b'],'new')
        self.assertEqual(self.author['world']['items'][0]['amount'],1)

    def test_conflict_report_and_reference_fingerprint_gate(self):
        self.author['world']['items'][0]['amount']=3
        merged,report=replay.replay(self.catalog,self.base,self.feature,self.author)
        self.assertEqual(report['status'],'CONFLICT')
        self.assertEqual(report['conflicts'][0]['path'],'world/items/Id=1/amount')
        self.assertEqual(merged['world']['items'][0]['amount'],3)
        self.base['text']['a/b']='tampered'
        with self.assertRaisesRegex(ValueError,'identity mismatch'):
            replay.replay(self.catalog,self.base,self.feature,self.author)

    def test_ambiguous_id_is_conflict(self):
        self.author['world']['items'].append({'Id':'1','amount':1})
        _,report=replay.replay(self.catalog,self.base,self.feature,self.author)
        self.assertEqual(report['conflict_count'],1)
        self.assertIn('ambiguous',report['conflicts'][0]['reason'])

    def test_conflicting_cli_does_not_emit_tables(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            for name,data in (('base',self.base),('feature',self.feature),('author',self.author)):
                (d/name).mkdir()
                for table,value in data.items():(d/name/(table+'.json')).write_text(json.dumps(value),encoding='utf-8')
            (d/'author/world.json').write_text(json.dumps({'items':[{'Id':1,'amount':4}]}),encoding='utf-8')
            (d/'catalog.json').write_text(json.dumps(self.catalog),encoding='utf-8')
            p=subprocess.run([sys.executable,str(ROOT/'tools/replay_data_rules.py'),'--catalog',str(d/'catalog.json'),
                '--base',str(d/'base'),'--feature',str(d/'feature'),'--author',str(d/'author'),'--out',str(d/'out')],
                capture_output=True,text=True)
            self.assertEqual(p.returncode,2,p.stderr)
            self.assertFalse((d/'out/tables').exists())
            self.assertEqual(json.loads((d/'out/report.json').read_text(encoding='utf-8'))['status'],'CONFLICT')

    def test_known_apk_shortcut_records_history_without_claiming_scan(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);apk=d/'fixture.apk'
            with zipfile.ZipFile(apk,'w') as z:z.writestr(feature_report.NATIVE,b'fake ELF')
            inv=migration_audit.inventory(apk)
            self.catalog['reference']['author_apk_sha256']=inv['apk_sha256']
            self.catalog['reference']['native_sha256']=inv['entries'][feature_report.NATIVE]['sha256']
            self.catalog['reference']['components']={feature_report.NATIVE:inv['entries'][feature_report.NATIVE]}
            cat=d/'catalog.json';cat.write_text(json.dumps(self.catalog),encoding='utf-8')
            p=subprocess.run([sys.executable,str(ROOT/'tools/scan_update.py'),'--new-apk',str(apk),
                '--catalog',str(cat),'--out',str(d/'out')],capture_output=True,encoding='utf-8',errors='replace')
            self.assertEqual(p.returncode,0,p.stderr)
            status=json.loads((d/'out/status.json').read_text(encoding='utf-8'))
            report=json.loads((d/'out/report.json').read_text(encoding='utf-8'))
            self.assertFalse(status['full_scan'])
            self.assertFalse(report['evidence_bound'])
            self.assertTrue(report['reference_apk_same'])
            self.assertEqual(report['previous_reference_review']['device_test'],'NOT_RUN')
            self.assertFalse((d/'out/evidence').exists())


if __name__=='__main__':unittest.main()
