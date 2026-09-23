import tempfile
import unittest
from pathlib import Path

from boa.python_importer import convert_python_source
from boa.runtime.code_generator import generate_python
from boa.core.project_storage import empty_project, load_project, save_project


def generated(source: str):
    result = convert_python_source(source, "converted.py")
    code = generate_python({
        "context": {"imports": result.imports, "variables": []},
        "functions": result.functions,
        "classes": result.classes,
        "graph": result.graph,
    })
    return result, code


def _recursive_blocks(graph: dict) -> list[dict]:
    result = []
    graph_fields = (
        "inner_graph",
        "try_graph",
        "try_else_graph",
        "try_finally_graph",
        "with_graph",
    )
    for block in graph.get("blocks", []):
        result.append(block)
        for field in graph_fields:
            nested = block.get(field)
            if isinstance(nested, dict):
                result.extend(_recursive_blocks(nested))
        for item in block.get("try_handlers", []):
            nested = item.get("graph")
            if isinstance(nested, dict):
                result.extend(_recursive_blocks(nested))
        for item in block.get("match_cases", []):
            nested = item.get("graph")
            if isinstance(nested, dict):
                result.extend(_recursive_blocks(nested))
        for section in block.get("python_sections", []):
            nested = section.get("graph")
            if isinstance(nested, dict):
                result.extend(_recursive_blocks(nested))
    return result



class PythonImporterTests(unittest.TestCase):
    def test_common_script_round_trip_executes(self):
        source = '''import math
BASE = 3

def calcul(x: int = BASE):
    total = 0
    for i in range(x):
        if i % 2 == 0:
            total += i
        else:
            total += 1
    return math.sqrt(total)

resultat = calcul(6)
'''
        result, code = generated(source)
        namespace = {}
        exec(compile(code, "<converted>", "exec"), namespace)
        self.assertEqual(namespace["resultat"], 3.0)
        self.assertFalse(any(block.get("key") == "empty" for block in result.graph["blocks"]))
        self.assertIn("def calcul(x: int=BASE):", code)

    def test_function_definition_keeps_module_order(self):
        source = '''DEFAULT = 7

def valeur(x=DEFAULT):
    return x

resultat = valeur()
'''
        _, code = generated(source)
        self.assertLess(code.index("DEFAULT = 7"), code.index("def valeur"))
        namespace = {}
        exec(compile(code, "<ordered>", "exec"), namespace)
        self.assertEqual(namespace["resultat"], 7)

    def test_structures_are_nested_graphs_not_free_code_blocks(self):
        source = '''resultat = []
for i in range(4):
    try:
        if i == 2:
            raise ValueError("x")
        resultat.append(i)
    except ValueError:
        resultat.append(99)
'''
        result, code = generated(source)
        namespace = {}
        exec(compile(code, "<nested>", "exec"), namespace)
        self.assertEqual(namespace["resultat"], [0, 1, 99, 3])
        nodes = _recursive_blocks(result.graph)
        self.assertTrue(any(block.get("key") == "try" for block in nodes))
        self.assertTrue(any(block.get("key") == "for" for block in result.graph["blocks"]))
        self.assertIn("0 bloc Code Python libre", result.report.message())


    def test_converted_project_survives_save_and_reload(self):
        result, _ = generated("value = 2\nif value > 1:\n    value += 3\n")
        project = empty_project()
        project["graphs"]["main"]["graph"] = result.graph
        project["graph"] = result.graph
        project["functions"] = result.functions
        project["classes"] = result.classes
        project["context"]["imports"] = result.imports
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "converted.boa"
            save_project(path, project)
            loaded = load_project(path)
        keys = [block.get("key") for block in loaded["graph"]["blocks"]]
        self.assertIn("assign", keys)
        self.assertIn("if", keys)
        if_block = next(block for block in loaded["graph"]["blocks"] if block.get("key") == "if")
        self.assertTrue(if_block.get("python_has_else") is False)

    def test_main_flow_is_horizontal_and_imports_are_not_blocks(self):
        result, _ = generated("import math\na = 1\nb = 2\nc = a + b\n")
        flow_blocks = [
            block for block in result.graph["blocks"]
            if block.get("key") in {"run", "assign"}
        ]
        self.assertEqual([block["key"] for block in flow_blocks], ["run", "assign", "assign", "assign"])
        self.assertEqual([block["x"] for block in flow_blocks], sorted(block["x"] for block in flow_blocks))
        self.assertEqual([item["statement"] for item in result.imports], ["import math"])
        self.assertFalse(any(
            block.get("key") == "python_node" and "import " in block.get("python_source", "")
            for block in _recursive_blocks(result.graph)
        ))

    def test_class_docstring_imports_decorators_and_order_are_preserved(self):
        source = '''@dataclass
class Exemple:
    """Documentation."""
    import math
    valeur: int = 3

    @property
    def double(self):
        return self.valeur * 2
'''
        result, code = generated(source)
        self.assertEqual(len(result.classes), 1)
        class_def = next(iter(result.classes.values()))
        self.assertEqual(class_def["docstring"], "Documentation.")
        self.assertEqual([item["statement"] for item in class_def["imports"]], ["import math"])
        ordered = sorted(
            [block for block in class_def["graph"]["blocks"] if block.get("class_order", -1) >= 0],
            key=lambda block: block["class_order"],
        )
        self.assertEqual([block["key"] for block in ordered], ["class_attribute", "def_marker"])
        self.assertIn("@dataclass", code)
        self.assertIn("@property", code)
        self.assertIn("class Exemple:", code)

    def test_args_and_kwargs_are_native_definition_ports(self):
        result, code = generated("def appel(a, *args, **kwargs):\n    return a, args, kwargs\n")
        function = next(iter(result.functions.values()))
        ports = [
            block for block in function["graph"]["blocks"]
            if block.get("key") in {"def_input", "def_input_p"}
        ]
        self.assertEqual([block.get("def_param_kind") for block in ports], ["normal", "args", "kwargs"])
        self.assertIn("def appel(a, *args, **kwargs):", code)

    def test_signature_modes_and_return_annotation_are_preserved(self):
        _, code = generated(
            "def signature(a: int, /, b=1, *, c: float=2.0) -> tuple:\n"
            "    return a, b, c\n"
        )
        self.assertIn(
            "def signature(a: int, /, b=1, *, c: float=2.0) -> tuple:",
            code,
        )

    def test_function_import_stays_in_function_scope(self):
        _, code = generated(
            "def racine(value):\n"
            "    import math\n"
            "    return math.sqrt(value)\n"
            "resultat = racine(9)\n"
        )
        lines = code.splitlines()
        self.assertEqual(lines[0], "def racine(value):")
        self.assertIn("    import math", lines)
        namespace = {}
        exec(compile(code, "<scoped-import>", "exec"), namespace)
        self.assertEqual(namespace["resultat"], 3.0)


    def test_loop_else_uses_structured_fallback_without_losing_behavior(self):
        source = "resultat = []\nfor value in range(2):\n    resultat.append(value)\nelse:\n    resultat.append(9)\n"
        result, code = generated(source)
        namespace = {}
        exec(compile(code, "<loop-else>", "exec"), namespace)
        self.assertEqual(namespace["resultat"], [0, 1, 9])
        self.assertTrue(any(
            block.get("key") == "python_node" and "else:" in block.get("python_source", "")
            for block in result.graph.get("blocks", [])
        ))


    def test_property_uses_attribute_access_expression_call_and_primary_return(self):
        source = '''class Mesure:
    valeur: float = 10.0

    @property
    def normalisee(self):
        return round(self.valeur / 100.0, 3)
'''
        result, code = generated(source)
        class_def = next(iter(result.classes.values()))
        self.assertEqual(
            [block.get("key") for block in class_def["graph"]["blocks"] if block.get("class_order", -1) >= 0],
            ["class_attribute", "def_marker"],
        )
        function = next(item for item in result.functions.values() if item["name"] == "normalisee")
        keys = [block.get("key") for block in function["graph"]["blocks"]]
        self.assertIn("attribute_get", keys)
        self.assertNotIn("return", keys)
        primary = next(block for block in function["graph"]["blocks"] if block.get("key") == "function_return")
        self.assertEqual(primary.get("return_values"), ["valeur"])
        rounded = next(block for block in function["graph"]["blocks"] if block.get("key") == "math_round")
        self.assertEqual(rounded.get("module_config", {}).get("mode"), "with_digits")
        self.assertIn("return round((self.valeur / 100.0), 3)", code)

    def test_try_match_with_and_unpacking_are_native(self):
        source = '''def analyser(values):
    first, *middle, last = values
    try:
        with open("missing.txt") as handle:
            text = handle.read()
    except OSError:
        text = "missing"
    finally:
        done = True
    match first:
        case 0:
            return text
        case _ if first > 0:
            return first, middle, last
'''
        result, code = generated(source)
        function = next(iter(result.functions.values()))
        keys = [block.get("key") for block in function["graph"]["blocks"]]
        self.assertIn("multi_assign", keys)
        self.assertIn("try", keys)
        self.assertIn("match", keys)
        try_block = next(block for block in function["graph"]["blocks"] if block.get("key") == "try")
        self.assertTrue(any(block.get("key") == "with" for block in _recursive_blocks(try_block["try_graph"])))
        compile(code, "<native-structures>", "exec")
        self.assertIn("first, *middle, last = values", code)
        self.assertIn("match first:", code)
        self.assertIn("with open('missing.txt') as handle:", code)

    def test_multiple_return_paths_keep_one_protected_primary_return(self):
        result, code = generated(
            "def signe(value):\n"
            "    if value < 0:\n"
            "        return 'negatif'\n"
            "    return 'positif'\n"
        )
        function = next(iter(result.functions.values()))
        returns = [block for block in function["graph"]["blocks"] if block.get("key") in {"return", "function_return"}]
        self.assertEqual(sum(block.get("key") == "function_return" for block in returns), 1)
        self.assertTrue(next(block for block in returns if block.get("key") == "function_return").get("protected"))
        namespace = {}
        exec(compile(code, "<returns>", "exec"), namespace)
        self.assertEqual(namespace["signe"](-1), "negatif")
        self.assertEqual(namespace["signe"](1), "positif")

    def test_imported_definition_ports_are_not_persistent(self):
        result, _ = generated("def f(self, value=1):\n    return value\n")
        function = next(iter(result.functions.values()))
        inputs = [block for block in function["graph"]["blocks"] if block.get("key") in {"def_input", "def_input_p"}]
        outputs = [block for block in function["graph"]["blocks"] if block.get("key") in {"def_output", "def_output_p"}]
        self.assertTrue(inputs)
        self.assertTrue(outputs)
        self.assertTrue(all(block.get("key") == "def_input" for block in inputs))
        self.assertTrue(all(block.get("key") == "def_output" for block in outputs))


    def test_native_structures_survive_project_save_and_reload(self):
        source = """class Config:
    enabled: bool = True

def parse(values):
    first, *rest = values
    try:
        with open('missing.txt') as handle:
            text = handle.read()
    except OSError:
        text = 'fallback'
    match first:
        case 0:
            return text
        case _:
            return first, rest
"""
        result, _ = generated(source)
        project = empty_project()
        project["graphs"]["main"]["graph"] = result.graph
        project["graph"] = result.graph
        project["functions"] = result.functions
        project["classes"] = result.classes
        project["context"]["imports"] = result.imports
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "native.boa"
            save_project(path, project)
            loaded = load_project(path)
        code = generate_python(loaded)
        compile(code, "<reloaded-native>", "exec")
        function = next(item for item in loaded["functions"].values() if item["name"] == "parse")
        keys = {block.get("key") for block in _recursive_blocks(function["graph"])}
        self.assertTrue({"multi_assign", "try", "with", "match"} <= keys)
        class_def = next(iter(loaded["classes"].values()))
        self.assertTrue(any(block.get("key") == "class_attribute" for block in class_def["graph"]["blocks"]))

    def test_attribute_assignment_stays_native_assignment(self):
        source = """class Counter:
    def __init__(self):
        self.value = 0
    def increment(self):
        self.value += 1
        return self.value
"""
        _, code = generated(source)
        self.assertIn("self.value = 0", code)
        self.assertIn("self.value = (self.value + 1)", code)
        namespace = {}
        exec(compile(code, "<attribute-assignment>", "exec"), namespace)
        counter = namespace["Counter"]()
        self.assertEqual(counter.increment(), 1)

    def test_invalid_python_reports_location(self):
        with self.assertRaisesRegex(ValueError, "ligne 1"):
            convert_python_source("if True print('x')", "bad.py")


    def test_imported_function_is_available_from_another_graph(self):
        result = convert_python_source("def double(x):\n    return x * 2\n", "functions.py")
        graph = {
            "blocks": [
                {"id": "run", "key": "run"},
                {"id": "call", "key": "python_node", "python_kind": "call",
                 "python_source": "result = double(5)", "python_inputs": ["double"],
                 "python_outputs": ["result"], "python_sections": [], "python_flow": True},
            ],
            "connections": [{"source": "run", "source_port": "out", "target": "call", "target_port": "start"}],
        }
        code = generate_python({"context": {"imports": [], "variables": []}, "functions": result.functions, "graph": graph})
        namespace = {}
        exec(compile(code, "<other-graph>", "exec"), namespace)
        self.assertEqual(namespace["result"], 10)

    def test_duplicate_function_names_keep_distinct_markers(self):
        source = '''def choix():
    return 1
premier = choix()
def choix():
    return 2
second = choix()
'''
        result, code = generated(source)
        markers = [block for block in result.graph["blocks"] if block.get("key") == "def_marker"]
        self.assertEqual(len(markers), 2)
        self.assertNotEqual(markers[0]["definition_id"], markers[1]["definition_id"])
        namespace = {}
        exec(compile(code, "<duplicate>", "exec"), namespace)
        self.assertEqual((namespace["premier"], namespace["second"]), (1, 2))


    def test_await_and_set_literals_are_native_and_execute(self):
        source = '''import asyncio

async def calcul():
    await asyncio.sleep(0)
    return {1, 2, 3}

resultat = asyncio.run(calcul())
'''
        result, code = generated(source)
        function = next(item for item in result.functions.values() if item["name"] == "calcul")
        keys = [block.get("key") for block in function["graph"]["blocks"]]
        self.assertIn("await", keys)
        self.assertIn("set_literal", keys)
        await_block = next(block for block in function["graph"]["blocks"] if block.get("key") == "await")
        self.assertTrue(await_block.get("await_flow"))
        namespace = {}
        exec(compile(code, "<await-set>", "exec"), namespace)
        self.assertEqual(namespace["resultat"], {1, 2, 3})

    def test_local_function_captures_are_connected_to_the_marker(self):
        source = '''def journaliser(fonction):
    def interne(*args, **kwargs):
        texte = f"appel {fonction.__name__}: {args} {kwargs}"
        return fonction(*args, **kwargs), texte
    return interne
'''
        result, code = generated(source)
        outer = next(item for item in result.functions.values() if item["name"] == "journaliser")
        marker = next(block for block in outer["graph"]["blocks"] if block.get("key") == "def_marker")
        self.assertEqual(marker.get("definition_captures"), ["fonction"])
        self.assertTrue(any(
            item.get("target") == marker["id"] and item.get("target_port") == "capture_1"
            for item in outer["graph"]["connections"]
        ))
        inner = next(item for item in result.functions.values() if item["name"] == "interne")
        self.assertEqual(inner.get("captured_names"), ["fonction"])
        self.assertTrue(any(
            item.get("name") == "fonction" and item.get("scope") == "capturée"
            for item in inner.get("variables", [])
        ))
        captured = next(
            block for block in inner["graph"]["blocks"]
            if block.get("key") == "variable" and block.get("variable_name") == "fonction"
        )
        structured_uses = [
            block for block in inner["graph"]["blocks"]
            if block.get("key") == "python_node" and "fonction" in block.get("python_inputs", [])
        ]
        self.assertEqual(len(structured_uses), 2)
        self.assertTrue(all(any(
            connection.get("source") == captured["id"]
            and connection.get("target") == block["id"]
            and connection.get("target_port") == f"input_{block['python_inputs'].index('fonction')}"
            for connection in inner["graph"]["connections"]
        ) for block in structured_uses))
        namespace = {}
        exec(compile(code, "<capture>", "exec"), namespace)
        wrapped = namespace["journaliser"](lambda value: value * 2)
        self.assertEqual(wrapped(21)[0], 42)

    def test_scope_variables_are_collected_for_panels(self):
        source = '''global_value = 1

def fonction(parametre):
    local_value: float = 2.5
    autre = parametre
    return autre

class Exemple:
    attribut: int = 3
'''
        result, _ = generated(source)
        self.assertEqual([item["name"] for item in result.variables], ["global_value"])
        function = next(item for item in result.functions.values() if item["name"] == "fonction")
        self.assertEqual([item["name"] for item in function["variables"]], ["local_value", "autre"])
        class_def = next(item for item in result.classes.values() if item["name"] == "Exemple")
        self.assertEqual([item["name"] for item in class_def["variables"]], ["attribut"])

if __name__ == "__main__":
    unittest.main()
