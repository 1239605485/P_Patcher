"""Three-way merge of decoded JSON. Conflicts produce a report, never an output table."""
import argparse
import copy
import json
from pathlib import Path

MISSING = object()


def same(a, b):
    # bool and int must not silently compare equal in JSON data.
    if a is MISSING or b is MISSING:
        return a is b
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def clone(x):
    return MISSING if x is MISSING else copy.deepcopy(x)


def merge(base, feature, author, conflicts, path='', id_key=None):
    if same(base, feature) or same(feature, author):
        return clone(author)
    if all(isinstance(x, dict) for x in (base, feature, author)):
        out = {}
        for k in dict.fromkeys([*author, *feature, *base]):
            token = k.replace('~', '~0').replace('/', '~1')
            v = merge(base.get(k, MISSING), feature.get(k, MISSING), author.get(k, MISSING), conflicts, path+'/'+token, id_key)
            if v is not MISSING:
                out[k] = v
        return out
    if id_key and all(isinstance(x, list) for x in (base, feature, author)):
        maps = []
        for rows in (base, feature, author):
            mapped = {}
            for row in rows:
                if not isinstance(row, dict) or id_key not in row or type(row[id_key]) not in (str, int):
                    raise ValueError('missing or invalid ID at ' + path)
                ident = (type(row[id_key]).__name__, row[id_key])
                if ident in mapped:
                    raise ValueError('duplicate ID at ' + path)
                mapped[ident] = row
            maps.append(mapped)
        out = []
        for ident in dict.fromkeys([*maps[2], *maps[1], *maps[0]]):
            v = merge(*(m.get(ident, MISSING) for m in maps), conflicts, path+'/'+str(ident), id_key)
            if v is not MISSING:
                out.append(v)
        return out
    # Evaluate containers first so a nested deletion cannot bypass review.
    if feature is not MISSING and same(base, author):
        return clone(feature)
    conflicts.append({'path': path or '/', 'reason': 'deletion or overlapping change',
        **{k: {'present': v is not MISSING, 'value': None if v is MISSING else v}
           for k, v in (('base', base), ('feature', feature), ('author', author))}})
    return clone(author)


def load(path):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError('duplicate JSON key: ' + k)
            out[k] = v
        return out
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError('invalid JSON constant '+x)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'feature', 'author', 'out', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--id-key', help='explicit stable list key; lists otherwise merge atomically')
    args = p.parse_args()
    if args.out.resolve() == args.report.resolve() or args.out.exists() or args.report.exists():
        p.error('output and report must be distinct new files')
    conflicts = []
    result = merge(load(args.base), load(args.feature), load(args.author), conflicts, id_key=args.id_key)
    args.report.write_text(json.dumps({'status': 'CONFLICT' if conflicts else 'DATA_MERGED_NOT_GAME_TESTED',
        'conflicts': conflicts}, ensure_ascii=False, indent=2), encoding='utf-8')
    if conflicts:
        raise SystemExit(2)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
