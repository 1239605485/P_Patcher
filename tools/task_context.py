"""Export a bounded AI handoff from a project index and evidence files."""
import argparse
import json
from pathlib import Path


def read(path, limit):
    if not path or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8-sig")
    if len(text) <= limit:
        return text
    head = max(1, limit * 2 // 3)
    tail = max(1, limit - head)
    return text[:head] + "\n...[truncated; full evidence remains local]...\n" + text[-tail:]


def export(index, task, evidence, out, limit):
    project = json.loads(index.read_text(encoding="utf-8-sig"))
    context = {
        "format": "mdz-task-context/1",
        "project_id": project.get("project_id"),
        "project_identity": {
            "apk_sha256": project["apk"]["sha256"],
            "engine_sha256": project.get("engine", {}).get("sha256") if project.get("engine") else None,
            "module_sha256": project.get("module", {}).get("sha256") if project.get("module") else None,
        },
        "task": task,
        "capabilities": project.get("capabilities", {}),
        "limitations": project.get("limitations", []),
        "evidence": {},
    }
    for path in evidence:
        value = read(path, limit)
        if value is not None:
            context["evidence"][path.name] = value
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return context


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index", type=Path, required=True)
    p.add_argument("--task", required=True)
    p.add_argument("--evidence", type=Path, action="append", default=[])
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--limit", type=int, default=24000)
    args = p.parse_args()
    if args.out.exists():
        p.error("output file already exists; choose a new path")
    context = export(args.index, args.task, args.evidence, args.out, args.limit)
    print(json.dumps({"format": context["format"], "project_id": context["project_id"],
                      "evidence_files": sorted(context["evidence"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
