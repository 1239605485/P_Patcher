"""Portable APK build: Python 3.12 + JDK 17/21; no Android SDK needed."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRUSTED_CERT = '21fa47120af53f71b39e886eaf0d71a159c34a2d332646a1cf0820a59549ad10'


def fetch(url, path, expected):
    if not path.exists():
        pending = path.with_suffix(path.suffix + '.pending')
        try:
            with urllib.request.urlopen(url, timeout=120) as src, pending.open('wb') as dst:
                shutil.copyfileobj(src, dst)
            if hashlib.sha256(pending.read_bytes()).hexdigest() != expected:
                raise ValueError('Downloaded tool digest mismatch: ' + path.name)
            pending.replace(path)
        finally:
            pending.unlink(missing_ok=True)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('Cached tool digest mismatch: ' + path.name)


def debug_key(path):
    if path.exists():
        return
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'P Patcher local test build')])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=3650))
            .sign(key, hashes.SHA256()))
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()) + cert.public_bytes(serialization.Encoding.PEM))
    path.chmod(0o600)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--debug', action='store_true')
    mode.add_argument('--key', type=Path, help='Combined PKCS8 RSA private key + certificate PEM')
    p.add_argument('--expected-cert-sha256', default=TRUSTED_CERT)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    if shutil.which('java') is None:
        p.error('Install JDK 17 or 21 and put java on PATH.')
    build, tools = ROOT/'build', ROOT/'toolchain'
    build.mkdir(exist_ok=True)
    tools.mkdir(exist_ok=True)
    from apk_signing import identity, rebuild_and_sign, verify_signature
    from cryptography.hazmat.primitives import hashes
    key = build/'debug-signing.pem' if a.debug else a.key.resolve()
    if a.debug:
        debug_key(key)
    _, cert = identity(key)
    fp = cert.fingerprint(hashes.SHA256()).hex()
    if not a.debug and fp != a.expected_cert_sha256.lower():
        p.error('Signing certificate fingerprint does not match --expected-cert-sha256')
    for t in json.loads((ROOT/'toolchain.json').read_text(encoding='utf-8')):
        fetch(t['url'], tools/t['file'], t['sha256'])
    public = tools/'android15_public.xml'
    fetch('https://raw.githubusercontent.com/aosp-mirror/platform_frameworks_base/android-15.0.0_r1/core/res/res/values/public-final.xml',
        public, json.loads((ROOT/'public_resource_pin.json').read_text())['sha256'])
    classes, dex = build/'classes', build/'dex'
    for folder in (classes, dex):
        # Both are fixed children of this repository's build directory.
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir()
    cp = os.pathsep.join(str(tools/n) for n in ('android.jar', 'json.jar'))
    subprocess.run(['java', '-jar', str(tools/'ecj.jar'), '-8', '-warn:none', '-encoding', 'UTF-8',
        '-cp', cp, '-d', str(classes), *map(str, sorted((ROOT/'src').rglob('*.java')))], check=True)
    jar = build/'app-classes.jar'
    with zipfile.ZipFile(jar, 'w') as z:
        for f in sorted(classes.rglob('*.class')):
            z.write(f, f.relative_to(classes).as_posix())
    subprocess.run(['java', '-cp', str(tools/'r8.jar'), 'com.android.tools.r8.D8', '--min-api', '26',
        '--lib', str(tools/'android.jar'), '--output', str(dex), str(jar)], check=True)
    from android_binary import manifest, resources, backup_rules
    unsigned = build/'unsigned.apk'
    with zipfile.ZipFile(unsigned, 'w') as z:
        z.writestr('AndroidManifest.xml', manifest(public.read_text(encoding='utf-8')))
        z.writestr('resources.arsc', resources('cn.minidayz.patcher', [
            ('xml', 'res/xml/local_backup_rules.xml', 'local_backup_rules'),
            ('drawable', 'res/drawable/icon.png', 'icon')]))
        z.writestr('res/xml/local_backup_rules.xml', backup_rules())
        z.write(ROOT/'assets/icon.png', 'res/drawable/icon.png')
        z.write(dex/'classes.dex', 'classes.dex')
        z.write(ROOT/'assets/trust.der', 'assets/trust.der')
    kind = 'debug' if a.debug else 'release'
    out = a.output.resolve() if a.output else ROOT/f'output/P_Patcher_1.6.0-{kind}.apk'
    out.parent.mkdir(parents=True, exist_ok=True)
    pending = out.with_suffix('.pending.apk')
    try:
        rebuild_and_sign(unsigned, pending, {}, key, fp)
        report = verify_signature(pending, fp)
        from androguard.core.axml import AXMLPrinter, ARSCParser
        from loguru import logger
        logger.remove()
        with zipfile.ZipFile(pending) as z:
            if z.testzip() is not None:
                raise ValueError('APK ZIP CRC verification failed')
            x = AXMLPrinter(z.read('AndroidManifest.xml')).get_xml_obj()
            ns = '{http://schemas.android.com/apk/res/android}'
            if (x.get('package') != 'cn.minidayz.patcher' or x.find('uses-sdk').get(ns+'targetSdkVersion') != '35'
                    or x.find('application').get(ns+'allowBackup') != 'false'):
                raise ValueError('APK manifest validation failed')
            if ARSCParser(z.read('resources.arsc')).get_packages_names() != ['cn.minidayz.patcher']:
                raise ValueError('APK resource validation failed')
        report.update(sha256=hashlib.sha256(pending.read_bytes()).hexdigest(), package='cn.minidayz.patcher',
            version='1.6.0', build_type=kind, apk_signer_sha256=fp, module_trust_sha256=TRUSTED_CERT,
            target_sdk=35, device_test='NOT_RUN')
        pending.replace(out)
        out.with_suffix('.verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        out.with_suffix('.apk.sha256').write_text(report['sha256']+'  '+out.name+'\n', encoding='utf-8')
        print('Built and verified: ' + str(out))
    finally:
        pending.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
