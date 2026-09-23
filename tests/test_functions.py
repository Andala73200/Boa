import tempfile
import unittest
from pathlib import Path

from boa.core.project_storage import empty_project, load_project, normalize_project, save_project
from boa.functions.models import function_parameters, function_returns, new_function, normalize_function, visible_ports
from boa.runtime.code_generator import generate_python
from boa.functions.sync import synchronize_calls


def port_block(uid, key, port_id, name, value_type="any", required=False, default=""):
    return {"id": uid, "key": key, "def_port_id": port_id, "def_port_name": name, "def_port_type": value_type, "def_required": required, "def_default": default}


class FunctionTests(unittest.TestCase):
    def test_new_function_has_protected_start_and_return(self):
        function = new_function("calcul")
        blocks = {block["key"]: block for block in function["graph"]["blocks"]}
        self.assertTrue(blocks["function_start"]["protected"])
        self.assertTrue(blocks["function_return"]["protected"])
        self.assertEqual(function["graph"]["connections"], [])

    def test_persistent_and_hideable_ports_are_detected_from_blocks(self):
        function = new_function("calcul")
        function["graph"]["blocks"] += [
            port_block("a", "def_input_p", "pa", "valeur", "int", True),
            port_block("b", "def_input", "pb", "coefficient", "float", False, "2.5"),
            port_block("c", "def_output", "pc", "resultat", "float"),
        ]
        inputs = function_parameters(function); outputs = function_returns(function)
        self.assertEqual([port["name"] for port in visible_ports(inputs, [])], ["valeur"])
        self.assertEqual([port["name"] for port in visible_ports(inputs, ["pb"])], ["valeur", "coefficient"])
        self.assertEqual(visible_ports(outputs, []), [])
        self.assertEqual([port["name"] for port in visible_ports(outputs, ["pc"])], ["resultat"])

    def test_port_identifier_survives_renaming(self):
        function = new_function("calcul"); block = port_block("a", "def_input", "stable", "ancien")
        function["graph"]["blocks"].append(block); block["def_port_name"] = "nouveau"
        self.assertEqual(function_parameters(function)[0]["id"], "stable")

    def test_previous_function_format_is_migrated(self):
        legacy = {
            "id": "legacy", "name": "ancienne", "parameters": [{"id": "p", "name": "valeur", "type": "int", "required": True, "always_visible": True}],
            "returns": [{"id": "r", "name": "resultat", "type": "int", "always_visible": True}],
            "graph": {"blocks": [{"id": "old_in", "key": "function_input"}, {"id": "old_out", "key": "function_output"}], "connections": [{"source": "old_in", "source_port": "start", "target": "old_out", "target_port": "end"}, {"source": "old_in", "source_port": "p", "target": "old_out", "target_port": "r"}]},
        }
        migrated = normalize_function(legacy); keys = {block["key"] for block in migrated["graph"]["blocks"]}
        self.assertNotIn("function_input", keys); self.assertNotIn("function_output", keys)
        self.assertEqual(function_parameters(migrated)[0]["id"], "p"); self.assertEqual(function_returns(migrated)[0]["id"], "r")
        self.assertTrue(any(item["source"] == "function_start" for item in migrated["graph"]["connections"]))

    def test_function_generates_and_runs_through_call_block(self):
        function = new_function("identite"); parameter = port_block("pin", "def_input_p", "p", "valeur", "int", True); result = port_block("pout", "def_output_p", "r", "resultat", "int")
        function["graph"]["blocks"] += [parameter, result]
        function["graph"]["connections"] += [
            {"source": "function_start", "source_port": "start", "target": "function_return", "target_port": "return"},
            {"source": "pin", "source_port": "value", "target": "pout", "target_port": "value"},
        ]
        graph = {
            "blocks": [{"id": "run", "key": "run"}, {"id": "value", "key": "value", "value_type": "int", "value_value": "7"}, {"id": "call", "key": "call", "call_kind": "project", "function_id": function["id"]}, {"id": "target", "key": "variable", "variable_name": "resultat", "variable_type": "int"}],
            "connections": [{"source": "run", "source_port": "out", "target": "call", "target_port": "start"}, {"source": "value", "source_port": "value", "target": "call", "target_port": "p"}, {"source": "call", "source_port": "r", "target": "target", "target_port": "in"}],
        }
        code = generate_python({"context": {}, "functions": {function["id"]: function}, "graph": graph})
        namespace = {}; exec(compile(code, "<boa-function>", "exec"), namespace)
        self.assertEqual(namespace["resultat"], 7); self.assertIn("def identite(valeur: int):", code)

    def test_function_can_call_another_project_function(self):
        identity = new_function("identite"); identity["id"] = "identity"
        identity["graph"]["blocks"] += [
            port_block("identity_in", "def_input_p", "input", "valeur", "int", True),
            port_block("identity_out", "def_output_p", "output", "resultat", "int"),
        ]
        identity["graph"]["connections"] += [
            {"source": "function_start", "source_port": "start", "target": "function_return", "target_port": "return"},
            {"source": "identity_in", "source_port": "value", "target": "identity_out", "target_port": "value"},
        ]
        wrapper = new_function("wrapper"); wrapper["id"] = "wrapper"
        wrapper["graph"]["blocks"] += [
            port_block("wrapper_in", "def_input_p", "input", "entree", "int", True),
            port_block("wrapper_out", "def_output_p", "output", "sortie", "int"),
            {"id": "inner_call", "key": "call", "call_kind": "project", "function_id": "identity"},
        ]
        wrapper["graph"]["connections"] += [
            {"source": "function_start", "source_port": "start", "target": "inner_call", "target_port": "start"},
            {"source": "inner_call", "source_port": "done", "target": "function_return", "target_port": "return"},
            {"source": "wrapper_in", "source_port": "value", "target": "inner_call", "target_port": "input"},
            {"source": "inner_call", "source_port": "output", "target": "wrapper_out", "target_port": "value"},
        ]
        graph = {
            "blocks": [
                {"id": "run", "key": "run"},
                {"id": "value", "key": "value", "value_type": "int", "value_value": "9"},
                {"id": "call", "key": "call", "call_kind": "project", "function_id": "wrapper"},
            ],
            "connections": [
                {"source": "run", "source_port": "out", "target": "call", "target_port": "start"},
                {"source": "value", "source_port": "value", "target": "call", "target_port": "input"},
            ],
        }
        code = generate_python({"context": {}, "functions": {"identity": identity, "wrapper": wrapper}, "graph": graph})
        namespace = {}; exec(compile(code, "<nested-functions>", "exec"), namespace)
        self.assertEqual(namespace["__boa_function_call_output"], 9)

    def test_function_comments_are_generated_at_their_expected_place(self):
        function = new_function("documentee")
        function["graph"]["blocks"][0]["comment"] = "Commentaire global"
        function["graph"]["blocks"][1]["comment"] = "Commentaire du retour"
        output = port_block("out", "def_output_p", "result", "resultat")
        output["comment"] = "Valeur renvoyée"
        function["graph"]["blocks"].append(output)
        function["graph"]["connections"].append({"source": "function_start", "source_port": "start", "target": "function_return", "target_port": "return"})
        code = generate_python({"context": {}, "functions": {function["id"]: function}, "graph": {"blocks": [], "connections": []}})
        self.assertLess(code.index("# Commentaire global"), code.index("def documentee"))
        self.assertIn("# resultat : Valeur renvoyée", code)
        self.assertLess(code.index("# Commentaire du retour"), code.index("return None"))

    def test_functions_are_saved_and_added_to_tree(self):
        project = empty_project(); function = new_function("test"); project["functions"] = {function["id"]: function}
        project = normalize_project(project)
        folder = next(item for item in project["tree"]["children"] if item["id"] == "functions_root")
        self.assertEqual(folder["children"][0]["name"], "test")
        with tempfile.TemporaryDirectory() as folder_path:
            path = Path(folder_path) / "project.boa"; saved = save_project(path, project); loaded = load_project(path)
            self.assertGreaterEqual(saved["version"], 6)
        self.assertEqual(loaded["functions"][function["id"]]["name"], "test")

    def test_deleted_ports_are_removed_from_closed_graphs(self):
        function = new_function("calcul"); function["graph"]["blocks"].append(port_block("pin", "def_input", "optional", "option", required=False))
        graph = {"blocks": [{"id": "call", "key": "call", "call_kind": "project", "function_id": function["id"], "function_inputs": ["optional"]}, {"id": "value", "key": "value"}], "connections": [{"source": "value", "source_port": "value", "target": "call", "target_port": "optional"}]}
        function["graph"]["blocks"] = [block for block in function["graph"]["blocks"] if block.get("def_port_id") != "optional"]
        self.assertTrue(synchronize_calls(graph, {function["id"]: function}))
        self.assertEqual(graph["connections"], [])


if __name__ == "__main__": unittest.main()
