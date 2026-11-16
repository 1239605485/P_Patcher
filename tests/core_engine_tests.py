"""Run after tools/build.py. Optional --apk/--plugin/--key performs a temporary full build."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--apk', type=Path)
p.add_argument('--plugin', type=Path)
p.add_argument('--key', type=Path)
p.add_argument('--log', type=Path, action='append', default=[])
a = p.parse_args()
if any((a.apk, a.plugin, a.key)) and not all((a.apk, a.plugin, a.key)):
    p.error('--apk, --plugin and --key must be supplied together')
cp = os.pathsep.join(str(root / f) for f in ('build/classes', 'toolchain/json.jar', 'toolchain/android.jar'))
with tempfile.TemporaryDirectory(prefix='p-patcher-core-') as folder:
    subprocess.run(['javac', '-source', '8', '-target', '8', '-encoding', 'UTF-8', '-cp', cp, '-d', folder,
                    str(root/'tests/DiagnosticCli.java'), str(root/'tests/CoreCli.java')], check=True)
    args = [folder, str(a.apk), str(a.plugin), str(a.key), str(root/'assets/trust.der'), *map(str, a.log)] if a.apk else []
    subprocess.run(['java', '-Dfile.encoding=UTF-8', '-cp', folder+os.pathsep+cp,
                    'cn.minidayz.patcher.CoreCli', *args], check=True)
    if a.apk:
        from androguard.core.axml import AXMLPrinter
        from loguru import logger
        logger.remove()
        with zipfile.ZipFile(Path(folder)/'generated.apk') as z:
            xml = AXMLPrinter(z.read('AndroidManifest.xml')).get_xml_obj()
        ns = '{http://schemas.android.com/apk/res/android}'
        assert xml.get(ns+'versionName') == '1.5.5-coretest'
        assert xml.get(ns+'versionCode') == '2000000000'
        assert xml.find('application').get(ns+'label') == '核心版构建验证'
        print('PASS generated APK manifest contains edited name and both version fields')
