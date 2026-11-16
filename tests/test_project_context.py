import json
import tempfile
import unittest
import zipfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import project_index
import task_context


class ProjectContextTests(unittest.TestCase):
    def test_index_is_hash_bound_and_records_entries(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            apk = d / "game.apk"
            with zipfile.ZipFile(apk, "w") as z:
                z.writestr("classes.dex", b"dex")
                z.writestr("assets/bin/Data/data.unity3d", b"unity")
            result = project_index.build_index(apk)
            self.assertEqual(result["format"], "mdz-project-index/1")
            self.assertEqual(result["project_id"], "mdz-" + result["apk"]["sha256"][:16])
            self.assertEqual(result["apk"]["entries"]["classes.dex"]["sha256"], project_index.hashlib.sha256(b"dex").hexdigest())
            self.assertFalse(result["capabilities"]["automatic_native_migration"])

    def test_context_is_bounded_and_keeps_identity(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            apk = d / "game.apk"
            with zipfile.ZipFile(apk, "w") as z:
                z.writestr("classes.dex", b"dex")
            index = d / "index.json"
            index.write_text(json.dumps(project_index.build_index(apk)), encoding="utf-8")
            evidence = d / "report.json"
            evidence.write_text("x" * 1000, encoding="utf-8")
            out = d / "context.json"
            data = task_context.export(index, "inspect crash", [evidence], out, 120)
            self.assertEqual(data["format"], "mdz-task-context/1")
            self.assertIn("report.json", data["evidence"])
            self.assertIn("truncated", data["evidence"]["report.json"])


if __name__ == "__main__":
    unittest.main()
