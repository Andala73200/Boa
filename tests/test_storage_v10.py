import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from boa.core.project_files import write_script
from boa.core.project_storage import empty_project, load_project, save_project


class StorageV10Tests(unittest.TestCase):
    def test_manifest_uses_physical_graph_and_never_rewrites_python(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "main.py"
            raw = b"# coding: latin-1\r\nmessage = 'caf\xe9'\r\n"
            source.write_bytes(raw)
            before = source.stat().st_mtime_ns
            project = empty_project()
            project["scripts"] = {"script_main": {"name": "main.py", "path": "main.py"}}
            files = project["tree"]["children"][0]
            files["children"].insert(0, {
                "name": "main.py", "kind": "script", "id": "script_main",
                "protected": False, "children": [],
            })
            manifest = root / "Boa_project.boa"
            save_project(manifest, project)
            self.assertEqual(source.read_bytes(), raw)
            self.assertEqual(source.stat().st_mtime_ns, before)
            self.assertTrue((root / "main.boa").is_file())
            stored = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertNotIn("graph", stored["graphs"]["main"])
            loaded = load_project(manifest)
            self.assertIn("café", loaded["scripts"]["script_main"]["content"])
            self.assertEqual(loaded["scripts"]["script_main"]["newline"], "\r\n")

    def test_explicit_script_save_preserves_bom_and_newlines(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "main.py"
            source.write_bytes(b"\xef\xbb\xbfvalue = 1\r\n")
            project = empty_project()
            project["scripts"] = {"script_main": {"name": "main.py", "path": "main.py"}}
            files = project["tree"]["children"][0]
            files["children"].insert(0, {
                "name": "main.py", "kind": "script", "id": "script_main",
                "protected": False, "children": [],
            })
            manifest = root / "Boa_project.boa"
            save_project(manifest, project)
            item = load_project(manifest)["scripts"]["script_main"]
            item["content"] = "value = 2\nprint(value)\n"
            write_script(manifest, item)
            result = source.read_bytes()
            self.assertTrue(result.startswith(b"\xef\xbb\xbf"))
            self.assertIn(b"value = 2\r\nprint(value)\r\n", result)

    def test_explicit_save_refuses_to_overwrite_external_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "main.py"
            source.write_text("value = 1\n", encoding="utf-8")
            project = empty_project()
            project["scripts"] = {"script_main": {"name": "main.py", "path": "main.py"}}
            project["tree"]["children"][0]["children"].insert(0, {
                "name": "main.py", "kind": "script", "id": "script_main",
                "protected": False, "children": [],
            })
            manifest = root / "Boa_project.boa"
            save_project(manifest, project)
            item = load_project(manifest)["scripts"]["script_main"]
            source.write_text("external = True\n", encoding="utf-8")
            item["content"] = "value = 2\n"
            with self.assertRaises(RuntimeError):
                write_script(manifest, item)
            self.assertEqual(source.read_text(encoding="utf-8"), "external = True\n")

    def test_invalid_manifest_recovers_from_atomic_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / "Boa_project.boa"
            project = empty_project()
            save_project(manifest, project)
            project["context"]["variables"].append({"name": "ok", "type": "int", "initial": "1"})
            save_project(manifest, project)
            manifest.write_text("{broken", encoding="utf-8")
            recovered = load_project(manifest)
            self.assertEqual(recovered["version"], 10)

    def test_legacy_embedded_project_migrates_with_original_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = Path(folder) / "Boa_project.boa"
            legacy = empty_project()
            legacy.pop("kind", None)
            legacy["version"] = 9
            manifest.write_text(json.dumps(legacy), encoding="utf-8")
            loaded = load_project(manifest)
            save_project(manifest, loaded)
            backup = json.loads((Path(folder) / "Boa_project.boa.bak").read_text(encoding="utf-8"))
            self.assertEqual(backup["version"], 9)
            self.assertTrue((Path(folder) / "main.boa").is_file())


if __name__ == "__main__":
    unittest.main()
