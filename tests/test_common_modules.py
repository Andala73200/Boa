import bz2
import csv
import gzip
import hashlib
import hmac
import io
import json
import lzma
import os
from pathlib import Path
import pathlib
import shutil
import sys
import tarfile
import tempfile
import unittest
import zipfile
import zlib

from boa.core.common_specs import COMMON_SPECS
from boa.core.models import BLOCK_DEFINITIONS
from boa.core.module_registry import MODULE_SPECS
from boa.core.module_specs import module_has_selectable_outputs, resolved_module_ports
from boa.runtime.code_generator import generate_python
from boa.runtime.common_codegen import common_expr, helper_source


class CommonModuleTests(unittest.TestCase):
    def test_source_avoids_python_312_only_fstrings(self):
        source = (Path(__file__).parents[1] / "boa" / "runtime" / "common_codegen.py").read_text(encoding="utf-8")
        for number, line in enumerate(source.splitlines(), start=1):
            self.assertNotRegex(line, r'f"[^"\n]*\{[^}\n]*"', f"ligne {number}")
            self.assertNotRegex(line, r"f'[^'\n]*\{[^}\n]*'", f"ligne {number}")

    def test_every_choice_starts_unselected(self):
        for spec in COMMON_SPECS.values():
            for field in spec.fields:
                if field.kind == "choice":
                    expected = "french" if (spec.key, field.key) == ("datetime_weekday", "language") else ""
                    self.assertEqual(field.default, expected, f"{spec.key}.{field.key}")

    def test_multi_output_blocks_can_hide_unneeded_outputs(self):
        parts = COMMON_SPECS["datetime_parts"]
        self.assertTrue(module_has_selectable_outputs(parts))
        inputs, outputs = resolved_module_ports(parts, {"_enabled_outputs": ["year", "day"]})
        self.assertEqual([port.key for port in inputs], ["value"])
        self.assertEqual([port.key for port in outputs], ["year", "day"])
        _, legacy_outputs = resolved_module_ports(parts, {})
        self.assertEqual(len(legacy_outputs), 6)

    def test_every_multi_output_configuration_generates_each_output_alone(self):
        checked = 0
        checked_blocks = set()
        for key, spec in MODULE_SPECS.items():
            if spec.hidden:
                continue
            variants = list(spec.variants) if spec.variants else [""]
            for variant in variants:
                config = {field.key: field.default for field in spec.fields}
                if variant:
                    config[spec.variant_field] = variant
                _, all_outputs = resolved_module_ports(spec, config)
                value_outputs = [port for port in all_outputs if port.value_type != "flow"]
                if len(value_outputs) <= 1:
                    continue
                checked += 1
                checked_blocks.add(key)
                for selected in value_outputs:
                    selected_config = {**config, "_enabled_outputs": [selected.key]}
                    _, outputs = resolved_module_ports(spec, selected_config)
                    self.assertEqual(
                        [port.key for port in outputs if port.value_type != "flow"],
                        [selected.key],
                        f"{key}.{variant}.{selected.key}",
                    )
                    blocks = [
                        {"id": "run", "key": "run", "title": "RUN"},
                        {"id": "module", "key": key, "module_config": selected_config},
                        {"id": "value", "key": "variable", "variable_name": "value", "variable_type": selected.value_type},
                    ]
                    connections = [
                        {"source": "module", "source_port": selected.key, "target": "value", "target_port": "in"},
                    ]
                    if spec.flow:
                        connections.insert(0, {"source": "run", "source_port": "out", "target": "module", "target_port": "start"})
                    code = generate_python({"context": {}, "graph": {"blocks": blocks, "connections": connections}})
                    compile(code, f"<{key}.{selected.key}>", "exec")
        self.assertEqual(len(checked_blocks), 19)
        self.assertEqual(checked, 20)

    def test_datetime_create_uses_defaults_and_optional_inputs(self):
        spec = COMMON_SPECS["datetime_create"]
        config = {
            "mode": "date",
            "year": 2024,
            "month": 2,
            "day": 29,
            "_enabled_inputs": [],
        }
        inputs, outputs = resolved_module_ports(spec, config)
        self.assertEqual(inputs, ())
        self.assertEqual([port.key for port in outputs], ["result"])
        expression = common_expr(
            {"key": "datetime_create", "module_config": config},
            "result",
            lambda _name, default: default,
        )
        self.assertEqual(expression, "datetime.date(2024, 2, 29)")

    def test_flow_module_can_keep_only_one_of_several_outputs(self):
        graph = {
            "blocks": [
                {"id": "run", "key": "run", "title": "RUN"},
                {
                    "id": "program",
                    "key": "run_program",
                    "module_config": {"_enabled_outputs": ["return_code"]},
                },
                {"id": "code", "key": "variable", "variable_name": "code", "variable_type": "int"},
            ],
            "connections": [
                {"source": "run", "source_port": "out", "target": "program", "target_port": "start"},
                {"source": "program", "source_port": "return_code", "target": "code", "target_port": "in"},
            ],
        }
        code = generate_python({"context": {}, "graph": graph})
        compile(code, "<selected-flow-output>", "exec")
        self.assertIn("_outputs = __boa_run_program", code)
        self.assertIn("_return_code = __boa_program_outputs[2]", code)

    def test_all_visible_blocks_are_translated_in_both_languages(self):
        catalogs = {}
        root = Path(__file__).parents[1] / "boa" / "i18n"
        for language in ("fr", "en"):
            catalog = {}
            for path in root.glob(f"{language}*.json"):
                catalog.update(json.loads(path.read_text(encoding="utf-8")))
            catalogs[language] = catalog
            for definition in BLOCK_DEFINITIONS:
                self.assertIn(f"block.{definition.key}.title", catalog)
                self.assertIn(f"block.{definition.key}.description", catalog)
        self.assertEqual(set(catalogs["fr"]), set(catalogs["en"]))

    def test_all_common_blocks_generate_valid_python(self):
        blocks = [{"id": "run", "key": "run", "title": "RUN"}]
        connections = []
        number = 0
        for key, spec in COMMON_SPECS.items():
            config = {field.key: field.default for field in spec.fields}
            for field in spec.fields:
                if field.kind == "choice" and field.choices:
                    config[field.key] = field.choices[0].key
            _, outputs = resolved_module_ports(spec, config)
            number += 1
            uid = f"m{number}"
            blocks.append({"id": uid, "key": key, "title": spec.title, "module_config": config})
            if spec.flow:
                connections.append({"source": "run", "source_port": "out", "target": uid, "target_port": "start"})
                continue
            value_outputs = [port for port in outputs if port.value_type != "flow"]
            if not value_outputs:
                continue
            number += 1
            variable = f"value_{number}"
            blocks.append({"id": f"v{number}", "key": "variable", "variable_name": variable, "variable_type": value_outputs[0].value_type})
            connections.append({"source": uid, "source_port": value_outputs[0].key, "target": f"v{number}", "target_port": "in"})
        code = generate_python({"context": {}, "graph": {"blocks": blocks, "connections": connections}})
        compile(code, "<all-common-blocks>", "exec")
        self.assertNotIn("import security", code)
        self.assertNotIn("import text\n", code)
        self.assertNotIn("import types", code)

    def test_conflicting_data_links_never_choose_one(self):
        graph = {
            "blocks": [
                {"id": "one", "key": "value", "value_type": "int", "value_value": "1"},
                {"id": "two", "key": "value", "value_type": "int", "value_value": "2"},
                {"id": "test", "key": "type_test", "module_config": {"mode": "int"}},
                {"id": "result", "key": "variable", "variable_name": "result", "variable_type": "bool"},
            ],
            "connections": [
                {"source": "one", "source_port": "value", "target": "test", "target_port": "value"},
                {"source": "two", "source_port": "value", "target": "test", "target_port": "value"},
                {"source": "test", "source_port": "result", "target": "result", "target_port": "in"},
            ],
        }
        code = generate_python({"context": {}, "graph": graph})
        self.assertIn("isinstance(None, int)", code)
        self.assertNotIn("isinstance(1, int)", code)
        self.assertNotIn("isinstance(2, int)", code)

    def test_file_csv_json_digest_and_archive_helpers(self):
        namespace = globals().copy()
        names = {"scalar", "bytes", "path", "json_file", "csv_memory", "csv_file", "digest", "archive"}
        exec(helper_source(names), namespace)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            text = root / "hello.txt"
            namespace["__boa_text_file"]("write", text, "bonjour", "utf-8", True)
            self.assertEqual(namespace["__boa_text_file"]("read", text, encoding="utf-8"), "bonjour")

            json_path = root / "data.json"
            namespace["__boa_json_write"](json_path, {"é": 2}, "utf-8", 2, False, False, True)
            self.assertEqual(namespace["__boa_json_read"](json_path, "utf-8"), {"é": 2})

            csv_path = root / "data.csv"
            namespace["__boa_csv_write"](csv_path, [{"a": 1}], ";", "utf-8", True, False, True)
            rows, headers = namespace["__boa_csv_read"](csv_path, ";", "utf-8", True, True)
            self.assertEqual((rows, headers), ([{"a": 1}], ["a"]))

            digest = namespace["__boa_digest"]("calculate", "data", "sha256", "abc", "")
            self.assertTrue(namespace["__boa_digest"]("verify", "data", "sha256", "abc", digest)[0])

            source = root / "source"
            source.mkdir()
            (source / "x.txt").write_text("x", encoding="utf-8")
            archive = root / "test.zip"
            namespace["__boa_archive_create"]("folder", "zip", source, archive, "refuse", True, 6)
            destination = root / "out"
            namespace["__boa_archive_extract"]("auto", "extract_all", archive, destination, [], "refuse")
            self.assertEqual((destination / "source" / "x.txt").read_text(encoding="utf-8"), "x")


if __name__ == "__main__":
    unittest.main()
