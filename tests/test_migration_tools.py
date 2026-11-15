import importlib.util
import struct
import tempfile
import unittest
import zipfile
import subprocess
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'tools'/f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


a = module('migration_audit')
m = module('merge_feature_data')


class Tests(unittest.TestCase):
    def test_metadata_108_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'game.apk'
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('assets/global-metadata.dat', struct.pack('<II', 0xfab11baf, 108))
            scan = a.inventory(p)
            self.assertFalse(scan['metadata'][0]['supported_layout'])
            self.assertTrue(a.audit(scan)['blockers'])

    def test_zip_repacking_and_androidx(self):
        with tempfile.TemporaryDirectory() as d:
            scans = []
            for i, compression in enumerate((zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                p = Path(d)/f'{i}.apk'
                with zipfile.ZipFile(p, 'w', compression=compression) as z:
                    z.writestr('META-INF/androidx.version', b'1')
                    z.writestr('META-INF/X.SF', b'signature')
                    z.writestr('classes.dex', b'content')
                scans.append(a.inventory(p))
            self.assertIn('META-INF/androidx.version', scans[0]['entries'])
            self.assertNotIn('META-INF/X.SF', scans[0]['entries'])
            self.assertEqual(a.compare(*scans)['changed'], [])

    def test_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'bad.apk'
            with zipfile.ZipFile(p, 'w') as z:
                z.writestr('../bad', 'bad')
            with self.assertRaises(ValueError):
                a.inventory(p)

    def test_author_update_preserved(self):
        c = []
        v = m.merge({'a': 1, 'b': 2}, {'a': 3, 'b': 2}, {'a': 1, 'b': 8, 'c': 9}, c)
        self.assertEqual(v, {'a': 3, 'b': 8, 'c': 9})
        self.assertFalse(c)

    def test_overlap_conflicts(self):
        c = []
        self.assertEqual(m.merge(1, 2, 3, c), 3)
        self.assertEqual(len(c), 1)

    def test_null_and_missing_distinct(self):
        c = []
        m.merge({'a': None}, {}, {'a': None}, c)
        self.assertFalse(c[0]['feature']['present'])
        self.assertTrue(c[0]['base']['present'])

    def test_boolean_not_integer(self):
        c = []
        self.assertIs(m.merge(1, True, 1, c), True)

    def test_id_order_and_author_additions(self):
        c = []
        b = [{'Id': 1, 'n': 1}, {'Id': 2, 'n': 1}]
        f = [{'Id': 1, 'n': 4}, {'Id': 2, 'n': 1}]
        n = [{'Id': 2, 'n': 3}, {'Id': 1, 'n': 1}, {'Id': 3, 'n': 8}]
        v = m.merge(b, f, n, c, id_key='Id')
        self.assertEqual(v, [{'Id': 2, 'n': 3}, {'Id': 1, 'n': 4}, {'Id': 3, 'n': 8}])
        self.assertFalse(c)

    def test_conflicting_ids(self):
        with self.assertRaises(ValueError):
            m.merge([{'Id': 1}], [{'Id': 1}, {'Id': 1}], [{'Id': 1, 'x': 3}], [], id_key='Id')

    def test_cli_conflict_never_writes_table(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            for name, value in (('base', 1), ('feature', 2), ('author', 3)):
                (d/name).write_text(json.dumps({'value': value}), encoding='utf-8')
            args = [sys.executable, str(ROOT/'tools/merge_feature_data.py')]
            for name in ('base', 'feature', 'author', 'out', 'report'):
                args += ['--'+name, str(d/name)]
            r = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertFalse((d/'out').exists())
            self.assertEqual(json.loads((d/'report').read_text())['status'], 'CONFLICT')

    def test_custom_metadata_bounds(self):
        parser = module('dump_il2cpp_v108')
        header = bytearray(600)
        struct.pack_into('<iii', header, 8, 500, 80, 10)
        self.assertEqual(parser.table_layout(header, 0), (500, 8, 10))
        struct.pack_into('<iii', header, 8, 590, 80, 10)
        with self.assertRaises(ValueError):
            parser.table_layout(header, 0)


if __name__ == '__main__':
    unittest.main()
