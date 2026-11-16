"""Create a persistent, hash-bound project index for incremental analysis.

The index is deliberately read-only. It records APK entries, engine/module
identity, and reusable cache keys without attempting to infer native patches.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


FORMAT = "mdz-project-index/1"


def digest_stream(stream, chunk=1024 * 1024):
    h = hashlib.sha256()
    size = 0
    while True:
        data = stream.read(chunk)
        if not data:
            break
        h.update(data)
        size += len(data)
    return size, h.hexdigest()


def read_json_zip(z, name):
    try:
        return json.loads(z.read(name).decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def index_zip(path: Path):
    entries = {}
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            with z.open(info) as stream:
                size, digest = digest_stream(stream)
            entries[info.filename] = {
                "size": size,
                "sha256": digest,
                "compress_type": info.compress_type,
            }
    raw = path.read_bytes()
    return {
        "path": str(path),
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "entries": entries,
    }


def load_manifest(path: Path):
    if not path:
        return None
    with zipfile.ZipFile(path) as z:
        for name in ("engine.json", "bundle.json", "module.json", "feature.json"):
            value = read_json_zip(z, name)
            if value is not None:
                return {"entry": name, "manifest": value}
    return None


def build_index(apk: Path, engine=None, module=None):
    apk_index = index_zip(apk)
    result = {
        "format": FORMAT,
        "schema_version": 1,
        "apk": apk_index,
        "engine": index_zip(engine) if engine else None,
        "module": index_zip(module) if module else None,
        "manifests": {
            "engine": load_manifest(engine) if engine else None,
            "module": load_manifest(module) if module else None,
        },
        "capabilities": {
            "apk_inventory": True,
            "content_hash_reuse": True,
            "unity_object_index": False,
            "dex_symbol_index": False,
            "il2cpp_symbol_index": False,
            "automatic_native_migration": False,
        },
        "limitations": [
            "Entry hashes permit safe cache reuse but do not prove runtime compatibility.",
            "Native and IL2CPP changes require version-bound evidence and manual review.",
        ],
    }
    result["project_id"] = "mdz-" + apk_index["sha256"][:16]
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apk", type=Path, required=True)
    p.add_argument("--engine", type=Path)
    p.add_argument("--module", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        p.error("output file already exists; choose a new path")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    data = build_index(args.apk, args.engine, args.module)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"project_id": data["project_id"], "apk_sha256": data["apk"]["sha256"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
