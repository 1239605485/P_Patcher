"""Read-only, dependency-free migration inventory. Never applies old native offsets."""
import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path, PurePosixPath

SUPPORTED_METADATA = {24, 27, 29, 31, 39}


def digest(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(block)
    return h.hexdigest()


def signature(name):
    # Other META-INF resources (AndroidX etc.) remain part of the inventory.
    return bool(re.fullmatch(r'META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))', name, re.I))


def inventory(apk):
    entries = {}
    metadata = []
    with zipfile.ZipFile(apk) as z:
        names = set()
        for e in z.infolist():
            n = e.filename
            if n in names or '\\' in n or n.startswith('/') or ':' in n or any(x in ('', '.', '..') for x in n.rstrip('/').split('/')):
                raise ValueError('unsafe or duplicate ZIP entry: ' + n)
            names.add(n)
            if e.is_dir() or signature(n):
                continue
            if e.flag_bits & 1:
                raise ValueError('encrypted ZIP entry: ' + n)
            with z.open(e) as f:
                sha = digest(f)  # Streams through CRC verification as well.
            entries[n] = {'size': e.file_size, 'sha256': sha}
            if n.endswith('/global-metadata.dat') or n == 'global-metadata.dat':
                with z.open(e) as f:
                    b = f.read(8)
                magic, version = struct.unpack('<II', b) if len(b) == 8 else (None, None)
                metadata.append({'entry': n, 'magic': magic, 'version': version,
                                 'supported_layout': magic == 0xFAB11BAF and version in SUPPORTED_METADATA})
    with open(apk, 'rb') as f:
        sha = digest(f)
    return {'format': 'mdz-migration-inventory/1', 'apk_sha256': sha,
            'entries': entries, 'metadata': metadata}


def compare(old, new):
    a, b = old['entries'], new['entries']
    return {state: [n for n in sorted(set(a) | set(b)) if (
        'added' if n not in a else 'removed' if n not in b else
        'unchanged' if a[n] == b[n] else 'changed') == state]
        for state in ('added', 'removed', 'unchanged', 'changed')}


def audit(current, baseline=None, port=None):
    result = {'format': 'mdz-migration-audit/1', 'input_sha256': current['apk_sha256'],
              'status': 'ANALYSIS_ONLY', 'installable_module': False,
              'automatic_native_migration': False, 'metadata': current['metadata'],
              'blockers': [], 'tasks': []}
    if not current['metadata'] or any(not x['supported_layout'] for x in current['metadata']):
        result['blockers'].append('METADATA_LAYOUT_UNSUPPORTED: recover and validate the actual layout before resolving methods')
    if baseline:
        result['baseline_sha256'] = baseline['apk_sha256']
        result['entry_diff'] = compare(baseline, current)
    if port:
        compatibility = json.loads((port / 'analysis/compatibility.json').read_text(encoding='utf-8-sig'))
        result['previous_port_source_sha256'] = compatibility['source_sha256']
        result['previous_port_baseline_matches'] = compatibility['source_sha256'] == current['apk_sha256']
        result['previous_port_status'] = json.loads((port / 'analysis/migration_progress.json').read_text(encoding='utf-8-sig'))
        result['reference_components'] = {}
        for suffix, key in (('/libil2cpp.so', 'source_native_sha256'), ('/global-metadata.dat', 'source_metadata_sha256')):
            for n, entry in current['entries'].items():
                if n.endswith(suffix):
                    result['reference_components'][n] = {'reference_sha256': compatibility[key],
                        'current_sha256': entry['sha256'], 'same_bytes': compatibility[key] == entry['sha256']}
        hooks = json.loads((port / 'analysis/injection_hooks.json').read_text(encoding='utf-8-sig'))
        groups = {}
        for hook in hooks:
            method = hook['method']
            identity = tuple(method.get(k, '') for k in ('assembly', 'type', 'method', 'params'))
            group = groups.setdefault(identity, {'identity': dict(zip(('assembly', 'type', 'method', 'params'), identity)),
                'identity_quality': 'legacy_parameter_names_not_full_signature', 'legacy_sites': [],
                'status': 'UNRESOLVED', 'target_rva': None,
                'required_checks': ['full parameter and return types', 'unique method and hook context',
                                    'instance/static fields and ABI', 'external calls and PC-relative references',
                                    'branch range', 'feature regression on device']})
            group['legacy_sites'].append(hook['site'])
        result['tasks'] = list(groups.values())
        result['hook_entries'] = len(hooks)
        result['blockers'].append('NATIVE_FEATURES_UNRESOLVED: task list covers recorded hooks only; direct instruction edits require a separate inventory')
        result['blockers'].append('SOURCE_FEATURE_PACKAGE_MISSING: supplied port work is not a signed module or complete stable feature source')
    result['release_checks'] = {'native_port': 'NOT_RUN', 'data_merge': 'NOT_RUN',
        'isolation_and_save_identity': 'NOT_RUN', 'module_signature': 'NOT_RUN', 'device_regression': 'NOT_RUN'}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apk', type=Path, required=True)
    p.add_argument('--baseline-inventory', type=Path)
    p.add_argument('--port-work', type=Path)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error('output directory must be new; existing reports are not overwritten')
    current = inventory(args.apk)
    baseline = json.loads(args.baseline_inventory.read_text(encoding='utf-8')) if args.baseline_inventory else None
    report = audit(current, baseline, args.port_work)
    args.out.mkdir(parents=True)
    for name, value in (('inventory.json', current), ('migration.json', report)):
        (args.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'input_sha256': current['apk_sha256'], 'entries': len(current['entries']),
                      'metadata': current['metadata'], 'tasks': len(report['tasks']),
                      'status': report['status']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
