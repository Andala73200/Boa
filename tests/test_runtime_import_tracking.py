import contextlib
import io
import unittest

from boa.python_importer import convert_python_source
from boa.runtime.code_generator import generate_python


def converted_code(source: str) -> str:
    result = convert_python_source(source, "tracking.py")
    return generate_python({
        "graph": result.graph,
        "context": {"imports": result.imports, "variables": result.variables},
        "functions": result.functions,
        "classes": result.classes,
    })


class RuntimeImportTrackingTests(unittest.TestCase):
    def test_alias_and_from_import_are_not_reimported_in_function_scope(self):
        source = (
            "import pathlib as p\n"
            "from datetime import datetime\n"
            "def values():\n"
            "    return p.Path('x').name, datetime(2020, 1, 1).year\n"
            "print(values())\n"
        )
        code = converted_code(source)
        self.assertNotIn("    import p", code)
        self.assertNotIn("    import datetime", code)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile(code, "tracking.py", "exec"), {})
        self.assertEqual(output.getvalue().strip(), "('x', 2020)")

    def test_multi_assignment_receiver_is_not_treated_as_module(self):
        source = "class X:\n    def m(self): return 7\na, b = X(), 0\nprint(a.m())\n"
        code = converted_code(source)
        self.assertNotIn("import a", code)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile(code, "tracking.py", "exec"), {})
        self.assertEqual(output.getvalue().strip(), "7")

    def test_compact_branch_body_generates_valid_python(self):
        source = "def f(kind):\n    if kind == 1: return 1\n    elif kind == 2: return 2\n    return 0\nprint(f(2))\n"
        code = converted_code(source)
        compile(code, "compact.py", "exec")


if __name__ == "__main__":
    unittest.main()
