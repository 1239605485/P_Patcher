# AI Project Workflow

This project keeps the Android installer focused on signed, hash-checked patch execution. Persistent analysis belongs beside the project, not inside the APK.

## Create an index

```powershell
.\.venv\Scripts\python.exe tools\project_index.py `
  --apk .\author155.apk `
  --engine .\引擎包_1.5.5.zip `
  --module .\插件总包_1.5.5.zip `
  --out .\project\index.json
```

The index records the APK entry inventory and stable hashes for the engine and module packages. It is safe to rebuild because it never changes the input files.

## Export a task context

```powershell
.\.venv\Scripts\python.exe tools\task_context.py `
  --index .\project\index.json `
  --task "排查点击设置闪退" `
  --evidence .\project\build_manifest.json `
  --evidence .\project\diagnostic\report.json `
  --out .\project\task_context.json
```

Send `task_context.json` with the focused request. Do not send the whole APK when the project identity and relevant evidence are unchanged.

## Evidence rules

- Reuse an index only when the APK SHA-256 matches.
- Treat engine/module entry hashes as cache keys, not as proof of runtime compatibility.
- Keep `build_id`, selected features, changed files, before/after hashes, and test results for every output APK.
- Native and IL2CPP changes require version-bound evidence and manual review. The index tools do not authorize automatic native migration.
