"""Decode a GitHub secret into temporary storage; never upload signing keys."""
import base64
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    secret = os.environ.get('SIGNING_PEM_BASE64', '')
    if not secret:
        raise SystemExit('Missing GitHub Actions secret SIGNING_PEM_BASE64')
    try:
        pem = base64.b64decode(''.join(secret.split()), validate=True)
    except ValueError:
        raise SystemExit('SIGNING_PEM_BASE64 must contain base64-encoded combined PEM')
    with tempfile.TemporaryDirectory(prefix='p-patcher-sign-') as folder:
        key = Path(folder)/'signing.pem'
        key.write_bytes(pem)
        key.chmod(0o600)
        cmd = [sys.executable, str(Path(__file__).with_name('build.py')), '--key', str(key)]
        fp = os.environ.get('SIGNING_CERT_SHA256', '').strip()
        if fp:
            cmd += ['--expected-cert-sha256', fp]
        env = os.environ.copy()
        env.pop('SIGNING_PEM_BASE64', None)
        subprocess.run(cmd, env=env, check=True)


if __name__ == '__main__':
    main()
