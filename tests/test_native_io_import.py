import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from boa.python_importer import convert_python_source
from boa.runtime.code_generator import generate_python


def _convert(source: str):
    result = convert_python_source(source, "native_io.py")
    code = generate_python({
        "context": {"imports": result.imports, "variables": []},
        "functions": result.functions,
        "classes": result.classes,
        "graph": result.graph,
    })
    return result, code


class NativeIoImportTests(unittest.TestCase):
    def test_float_input_and_print_use_native_blocks(self):
        source = '''nombre = float(input("Entre un nombre : "))
if nombre < 50:
    print("Le nombre est plus petit que 50.")
elif nombre > 50:
    print("Le nombre est plus grand que 50.")
else:
    print("Le nombre est égal à 50.")
'''
        result, code = _convert(source)
        inputs = [b for b in result.graph["blocks"] if b.get("key") == "input"]
        prints = [b for b in result.graph["blocks"] if b.get("key") == "print"]
        calls = [b.get("call_target") for b in result.graph["blocks"] if b.get("key") == "call"]
        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0].get("input_type"), "float")
        self.assertEqual(inputs[0].get("input_prompt"), "Entre un nombre : ")
        self.assertEqual(len(prints), 3)
        self.assertNotIn("input", calls)
        self.assertNotIn("float", calls)
        self.assertNotIn("print", calls)
        with patch("builtins.input", return_value="42"), redirect_stdout(io.StringIO()) as output:
            exec(compile(code, "<native_io>", "exec"), {})
        self.assertEqual(output.getvalue(), "Le nombre est plus petit que 50.\n")

    def test_int_input_is_one_native_input_block(self):
        result, code = _convert('age = int(input("Âge : "))\n')
        inputs = [b for b in result.graph["blocks"] if b.get("key") == "input"]
        self.assertEqual(len(inputs), 1)
        self.assertEqual(inputs[0].get("input_type"), "int")
        self.assertIn("int(input(", code)

    def test_print_with_values_uses_dynamic_native_print(self):
        result, code = _convert('valeur = 3\nprint("Résultat :", valeur)\n')
        block = next(b for b in result.graph["blocks"] if b.get("key") == "print")
        self.assertTrue(block.get("print_dynamic"))
        self.assertEqual(block.get("print_text"), "Résultat : {valeur}")
        self.assertIn("print(f'Résultat : {valeur}')", code)


if __name__ == "__main__":
    unittest.main()
