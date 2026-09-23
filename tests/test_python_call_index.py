import unittest

from boa.python_importer import convert_python_source
from boa.python_importer.call_index import get_call_index
from boa.runtime.code_generator import generate_python


SOURCE = '''import math
import random

texte = "  Bonjour Boa  "
nombres = [5, 2, 9, 2]
longueur = len(texte)
minimum = min(nombres)
maximum = max(nombres)
total = sum(nombres)
tries = sorted(nombres, reverse=True)
entier = int("42")
decimal = float("3.5")
chaine = str(123)
liste = list((1, 2, 3))
tuple_valeurs = tuple(nombres)
ensemble = set(nombres)
propre = texte.strip()
majuscule = propre.upper()
est_entier = isinstance(entier, int)
racine = math.sqrt(81)
aleatoire = random.randint(1, 10)
'''


class PythonCallIndexTests(unittest.TestCase):
    def test_index_loads_all_manifests_without_error(self):
        index = get_call_index()
        self.assertFalse(index.errors)
        self.assertGreaterEqual(len(index.rules), 90)
        self.assertIn("math_sqrt", index.block_keys)
        self.assertIn("text_transform", index.block_keys)

    def test_known_calls_become_native_module_blocks(self):
        result = convert_python_source(SOURCE, "indexed.py")
        keys = [block.get("key") for block in result.graph["blocks"]]
        self.assertIn("value_length", keys)
        self.assertIn("statistics_summary", keys)
        self.assertIn("collection_sort", keys)
        self.assertIn("type_convert", keys)
        self.assertIn("type_test", keys)
        self.assertIn("text_transform", keys)
        self.assertIn("math_sqrt", keys)
        self.assertIn("random_number", keys)
        calls = {block.get("call_target") for block in result.graph["blocks"] if block.get("key") == "call"}
        for name in {"len", "min", "max", "sum", "sorted", "int", "float", "str", "list", "tuple", "set", "isinstance", "math.sqrt", "random.randint"}:
            self.assertNotIn(name, calls)

    def test_generated_code_keeps_results(self):
        result = convert_python_source(SOURCE, "indexed.py")
        code = generate_python({
            "context": {"imports": result.imports, "variables": []},
            "functions": result.functions,
            "classes": result.classes,
            "graph": result.graph,
        })
        namespace = {}
        exec(compile(code, "<indexed>", "exec"), namespace)
        self.assertEqual(namespace["longueur"], len("  Bonjour Boa  "))
        self.assertEqual(namespace["minimum"], 2)
        self.assertEqual(namespace["maximum"], 9)
        self.assertEqual(namespace["total"], 18)
        self.assertEqual(namespace["tries"], [9, 5, 2, 2])
        self.assertEqual(namespace["liste"], [1, 2, 3])
        self.assertEqual(namespace["ensemble"], {2, 5, 9})
        self.assertEqual(namespace["propre"], "Bonjour Boa")
        self.assertEqual(namespace["majuscule"], "BONJOUR BOA")
        self.assertTrue(namespace["est_entier"])
        self.assertEqual(namespace["racine"], 9.0)
        self.assertTrue(1 <= namespace["aleatoire"] <= 10)

    def test_second_native_call_batch(self):
        source = '''values = []
a = abs(-2)
b = round(3.14, 1)
values.append(3)
c = {"x": 1}.get("x", 0)
d = list(zip([1], [2]))
e = list(enumerate(values))
f = dict(nom="Boa", version=2)
'''
        result = convert_python_source(source, "native_batch_2.py")
        keys = [block.get("key") for block in result.graph["blocks"]]
        for key in {"math_abs", "math_round", "collection_append", "collection_get", "collection_zip", "collection_enumerate", "collection_dict"}:
            self.assertIn(key, keys)
        calls = {block.get("call_target") for block in result.graph["blocks"] if block.get("key") == "call"}
        for name in {"abs", "round", "values.append", "zip", "enumerate", "dict"}:
            self.assertNotIn(name, calls)
        code = generate_python({
            "context": {"imports": result.imports, "variables": []},
            "functions": result.functions,
            "classes": result.classes,
            "graph": result.graph,
        })
        namespace = {}
        exec(compile(code, "<native_batch_2>", "exec"), namespace)
        self.assertEqual(namespace["values"], [3])
        self.assertEqual(namespace["a"], 2)
        self.assertEqual(namespace["b"], 3.1)
        self.assertEqual(namespace["c"], 1)
        self.assertEqual(namespace["d"], [(1, 2)])
        self.assertEqual(namespace["e"], [(0, 3)])
        self.assertEqual(namespace["f"], {"nom": "Boa", "version": 2})

    def test_round_and_enumerate_keyword_forms(self):
        source = "a = round(3.1415, ndigits=2)\nb = list(enumerate([4, 5], start=7))\n"
        result = convert_python_source(source, "keyword_forms.py")
        calls = [block for block in result.graph["blocks"] if block.get("key") == "call"]
        self.assertFalse(calls)
        code = generate_python({
            "context": {"imports": result.imports, "variables": []},
            "functions": result.functions,
            "classes": result.classes,
            "graph": result.graph,
        })
        namespace = {}
        exec(compile(code, "<keyword_forms>", "exec"), namespace)
        self.assertEqual(namespace["a"], 3.14)
        self.assertEqual(namespace["b"], [(7, 4), (8, 5)])


if __name__ == "__main__":
    unittest.main()
