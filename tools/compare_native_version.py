"""Compare recorded stable hooks with a new build. Candidates are never applied."""
import argparse
import collections
import csv
import hashlib
import json
import struct
from pathlib import Path
from anchor_map import Image, align


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('old-binary', 'new-binary', 'old-methods', 'new-methods', 'hooks', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        p.error('report must not already exist')
    old = Image(a.old_binary.read_bytes(), list(csv.DictReader(a.old_methods.open(encoding='utf-8'))))
    new = Image(a.new_binary.read_bytes(), list(csv.DictReader(a.new_methods.open(encoding='utf-8'))))
    hooks = json.loads(a.hooks.read_text(encoding='utf-8'))
    results = []
    for h in hooks:
        site, target = int(h['site'], 16), int(h['target'], 16)
        word = struct.unpack_from('<I', old.raw, old.offset(site))[0]
        imm = word & 0x3ffffff
        if imm & (1 << 25):
            imm -= 1 << 26
        if word & 0x7c000000 != 0x14000000 or site + imm * 4 != target:
            results.append({'source_site': site, 'status': 'SOURCE_HOOK_BYTES_MISMATCH'})
            continue
        result = align(old, new, site)
        result['legacy_target'] = target
        result['source_hook_bytes_verified'] = True
        results.append(result)
    report = {'format': 'mdz-native-migration-plan/1', 'status': 'PLAN_ONLY_NOT_APPLIED',
              'release_ready': False, 'hook_entries': len(hooks),
              'source_binary_sha256': hashlib.sha256(old.raw).hexdigest(),
              'target_binary_sha256': hashlib.sha256(new.raw).hexdigest(),
              'source_methods_sha256': hashlib.sha256(a.old_methods.read_bytes()).hexdigest(),
              'target_methods_sha256': hashlib.sha256(a.new_methods.read_bytes()).hexdigest(),
              'source_hooks_sha256': hashlib.sha256(a.hooks.read_bytes()).hexdigest(),
              'counts': dict(collections.Counter(x['status'] for x in results)),
              'anchors': results,
              'limitations': ['Legacy keys use parameter names, not full signatures.',
                  'Unique context is a candidate only; ABI, fields, return types and references remain unchecked.',
                  'Recorded hooks do not cover every direct instruction edit.']}
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report['counts']))


if __name__ == '__main__':
    main()
