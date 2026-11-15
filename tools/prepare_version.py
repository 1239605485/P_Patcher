"""One command: source-bound native migration evidence. Does not build a patched APK."""
import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from migration_audit import inventory


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('stable-apk', 'new-apk', 'port-work', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        p.error('output must be a new directory')
    # Resolve required dependencies before creating partial output.
    import elftools
    import capstone
    from field_offsets import extract
    a.out.mkdir(parents=True)
    tools = Path(__file__).resolve().parent
    state = {'status': 'IN_PROGRESS', 'installable_module': False, 'release_ready': False, 'inputs': {}}

    def save():
        (a.out/'status.json').write_text(json.dumps(state, indent=2), encoding='utf-8')

    try:
        for tag, apk in (('stable', a.stable_apk), ('new', a.new_apk)):
            folder = a.out/tag
            folder.mkdir()
            inv = inventory(apk)
            state['inputs'][tag] = inv['apk_sha256']
            (folder/'inventory.json').write_text(json.dumps(inv, indent=2), encoding='utf-8')
            with zipfile.ZipFile(apk) as z:
                for name in ('lib/arm64-v8a/libil2cpp.so', 'assets/bin/Data/Managed/Metadata/global-metadata.dat'):
                    with z.open(name) as src, (folder/Path(name).name).open('wb') as dst:
                        import shutil
                        shutil.copyfileobj(src, dst, 1024*1024)
            subprocess.run([sys.executable, str(tools/'dump_il2cpp_v108.py'),
                '--metadata', str(folder/'global-metadata.dat'), '--binary', str(folder/'libil2cpp.so'),
                '--out', str(folder/'parsed')], check=True)
            parsed = json.loads((folder/'parsed/types.json').read_text(encoding='utf-8'))
            fields = extract((folder/'libil2cpp.so').read_bytes(), (folder/'global-metadata.dat').read_bytes(), parsed)
            (folder/'fields.json').write_text(json.dumps(fields, indent=2), encoding='utf-8')
            save()
        subprocess.run([sys.executable, str(tools/'compare_native_version.py'),
            '--old-binary', str(a.out/'stable/libil2cpp.so'), '--new-binary', str(a.out/'new/libil2cpp.so'),
            '--old-methods', str(a.out/'stable/parsed/methods.csv'), '--new-methods', str(a.out/'new/parsed/methods.csv'),
            '--hooks', str(a.port_work/'analysis/injection_hooks.json'), '--out', str(a.out/'anchors.json')], check=True)
        state.update(status='PLAN_ONLY_NOT_APPLIED',
            limitations=['Legacy method keys omit full parameter types; candidates require ABI and semantic verification.',
                         'Field output distinguishes duplicate type names by index but does not establish field type/static semantics.',
                         'Direct instruction changes and data merge require the exact unmodified author baseline.',
                         'No APK or signed module generated.'])
    except Exception as e:
        state.update(status='FAILED_NOT_RELEASEABLE', error=str(e))
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
