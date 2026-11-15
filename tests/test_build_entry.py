import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('apk_builder', ROOT/'tools/build.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuildEntryTests(unittest.TestCase):
    def test_release_requires_secret(self):
        env = os.environ.copy()
        env.pop('SIGNING_PEM_BASE64', None)
        p = subprocess.run([sys.executable, str(ROOT/'tools/ci_release.py')], env=env,
                           capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('Missing GitHub Actions secret', p.stderr)

    def test_wrong_release_certificate_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            key = Path(d)/'test.pem'
            builder.debug_key(key)
            p = subprocess.run([sys.executable, str(ROOT/'tools/build.py'), '--key', str(key),
                                '--expected-cert-sha256', '0'*64], capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn('fingerprint does not match', p.stderr)

    def test_local_test_identity_persists(self):
        with tempfile.TemporaryDirectory() as d:
            key = Path(d)/'test.pem'
            builder.debug_key(key)
            before = key.read_bytes()
            builder.debug_key(key)
            self.assertEqual(before, key.read_bytes())


if __name__ == '__main__':
    unittest.main()
