from __future__ import annotations

import ast
from uuid import uuid4

from boa.python_importer.analysis import name_usage
from boa.python_importer.call_index import get_call_index
from boa.python_importer.models import ConversionReport
from boa.python_importer.native_calls import input_spec


_BINOPS = {
    ast.Add: "op_add", ast.Sub: "op_sub", ast.Mult: "op_mul", ast.Div: "op_div",
    ast.FloorDiv: "op_floordiv", ast.Mod: "op_mod", ast.Pow: "op_pow",
}
_CMPOPS = {
    ast.Eq: "op_eq", ast.NotEq: "op_ne", ast.Gt: "op_gt", ast.Lt: "op_lt",
    ast.GtE: "op_ge", ast.LtE: "op_le",
}


class ExpressionBuilder:
    def __init__(self, source: str, report: ConversionReport) -> None:
        self.source = source
        self.report = report
        self._counter = 0

    def build(
        self,
        graph: dict,
        node: ast.AST | None,
        definitions: dict[str, tuple[str, str]],
        x: float,
        y: float,
    ) -> tuple[str, str]:
        if node is None:
            return self._constant(graph, None, x, y)
        if isinstance(node, ast.Name):
            return definitions.get(node.id) or self._variable(graph, node.id, x, y)
        if isinstance(node, ast.Constant):
            return self._constant(graph, node.value, x, y)
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
            return self._binary(graph, _BINOPS[type(node.op)], node.left, node.right, definitions, x, y)
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in _CMPOPS:
            return self._binary(graph, _CMPOPS[type(node.ops[0])], node.left, node.comparators[0], definitions, x, y)
        if isinstance(node, ast.BoolOp) and node.values:
            key = "and" if isinstance(node.op, ast.And) else "or"
            result = self.build(graph, node.values[0], definitions, x - 180, y)
            for index, value in enumerate(node.values[1:], start=1):
                right = self.build(graph, value, definitions, x - 180, y + index * 90)
                uid = self._uid("logic")
                graph["blocks"].append({"id": uid, "key": key, "x": x + index * 100, "y": y + index * 60})
                self._connect(graph, result, (uid, "a"))
                self._connect(graph, right, (uid, "b"))
                result = (uid, "out")
                self._native()
            return result
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            source = self.build(graph, node.operand, definitions, x - 150, y)
            uid = self._uid("not")
            graph["blocks"].append({"id": uid, "key": "not", "x": x, "y": y})
            self._connect(graph, source, (uid, "in"))
            self._native()
            return uid, "out"
        if isinstance(node, ast.Await):
            return self._await(graph, node, definitions, x, y)
        if isinstance(node, ast.Set):
            return self._set_literal(graph, node, definitions, x, y)
        if isinstance(node, ast.Attribute):
            return self._attribute(graph, node, definitions, x, y)
        if isinstance(node, ast.Call):
            native_input = input_spec(node)
            if native_input:
                return self._input(graph, native_input, x, y)
            indexed = get_call_index().match(node)
            if indexed:
                return self._indexed_call(graph, indexed, definitions, x, y)
        if isinstance(node, ast.Call) and _simple_call_target(node.func) and not any(isinstance(arg, ast.Starred) for arg in node.args) and not any(item.arg is None for item in node.keywords):
            return self._call(graph, node, definitions, x, y)
        return self._structured_expression(graph, node, definitions, x, y)

    def _binary(self, graph: dict, key: str, left: ast.AST, right: ast.AST, definitions: dict, x: float, y: float) -> tuple[str, str]:
        a = self.build(graph, left, definitions, x - 180, y - 45)
        b = self.build(graph, right, definitions, x - 180, y + 45)
        uid = self._uid("op")
        graph["blocks"].append({"id": uid, "key": key, "x": x, "y": y})
        self._connect(graph, a, (uid, "a"))
        self._connect(graph, b, (uid, "b"))
        self._native()
        return uid, "result"


    def _input(self, graph: dict, spec: dict, x: float, y: float) -> tuple[str, str]:
        uid = self._uid("input")
        graph["blocks"].append({"id": uid, "key": "input", **spec, "x": x, "y": y})
        self._native()
        return uid, "value"


    def _indexed_call(self, graph: dict, match, definitions: dict, x: float, y: float) -> tuple[str, str]:
        uid = self._uid("native_call")
        graph["blocks"].append({
            "id": uid,
            "key": match.rule.block_key,
            "module_config": dict(match.config),
            "x": x,
            "y": y,
        })
        for index, (port, value) in enumerate(match.inputs):
            source = self.build(graph, value, definitions, x - 220, y + index * 76)
            self._connect(graph, source, (uid, port))
        self._native()
        return uid, match.rule.result_port

    def _call(self, graph: dict, node: ast.Call, definitions: dict, x: float, y: float) -> tuple[str, str]:
        uid = self._uid("call")
        keyword_names = [str(item.arg) for item in node.keywords if item.arg]
        block = {
            "id": uid, "key": "call", "call_kind": "python", "call_target": ast.unparse(node.func),
            "call_arg_count": len(node.args), "call_result_type": "any", "call_vararg_count": 0,
            "call_kwarg_names": [*keyword_names, f"kwarg_{len(keyword_names) + 1}"] if keyword_names else [],
            "call_arg_labels": [], "call_flow": False, "x": x, "y": y,
        }
        graph["blocks"].append(block)
        for index, arg in enumerate(node.args):
            source = self.build(graph, arg, definitions, x - 220, y + index * 80)
            self._connect(graph, source, (uid, f"arg_{index + 1}"))
        for index, keyword in enumerate(node.keywords):
            source = self.build(graph, keyword.value, definitions, x - 220, y + (len(node.args) + index) * 80)
            self._connect(graph, source, (uid, f"kwarg_{index + 1}"))
        self._native()
        return uid, "result"


    def _await(self, graph: dict, node: ast.Await, definitions: dict, x: float, y: float) -> tuple[str, str]:
        source = self.build(graph, node.value, definitions, x - 200, y)
        uid = self._uid("await")
        graph["blocks"].append({
            "id": uid, "key": "await", "await_flow": False, "x": x, "y": y,
        })
        self._connect(graph, source, (uid, "awaitable"))
        self._native()
        return uid, "result"

    def _set_literal(self, graph: dict, node: ast.Set, definitions: dict, x: float, y: float) -> tuple[str, str]:
        uid = self._uid("set")
        count = max(1, len(node.elts) + 1)
        graph["blocks"].append({
            "id": uid, "key": "set_literal", "set_item_count": count, "x": x, "y": y,
        })
        for index, item in enumerate(node.elts):
            source = self.build(graph, item, definitions, x - 200, y + index * 58)
            self._connect(graph, source, (uid, f"element_{index + 1}"))
        self._native()
        return uid, "result"

    def _attribute(self, graph: dict, node: ast.Attribute, definitions: dict, x: float, y: float) -> tuple[str, str]:
        source = self.build(graph, node.value, definitions, x - 180, y)
        uid = self._uid("attribute")
        graph["blocks"].append({
            "id": uid,
            "key": "attribute_get",
            "attribute_name": node.attr,
            "x": x,
            "y": y,
        })
        self._connect(graph, source, (uid, "object"))
        self._native()
        return uid, "value"

    def _variable(self, graph: dict, name: str, x: float, y: float) -> tuple[str, str]:
        uid = self._uid("var")
        graph["blocks"].append({"id": uid, "key": "variable", "variable_name": name, "variable_type": "any", "variable_constant": False, "x": x, "y": y})
        self._native()
        return uid, "out"

    def _constant(self, graph: dict, value, x: float, y: float) -> tuple[str, str]:
        uid = self._uid("value")
        if value is True:
            block = {"id": uid, "key": "true", "x": x, "y": y}
            port = "out"
        elif value is False:
            block = {"id": uid, "key": "false", "x": x, "y": y}
            port = "out"
        elif value is None:
            block = {"id": uid, "key": "none", "x": x, "y": y}
            port = "out"
        else:
            value_type = type(value).__name__ if type(value).__name__ in {"bool", "int", "float", "str", "list", "dict", "tuple", "set"} else "any"
            block = {"id": uid, "key": "value", "value_type": value_type, "value_value": repr(value) if value_type != "str" else str(value), "x": x, "y": y}
            port = "value"
        graph["blocks"].append(block)
        self._native()
        return uid, port

    def _structured_expression(
        self,
        graph: dict,
        node: ast.AST,
        definitions: dict[str, tuple[str, str]],
        x: float,
        y: float,
    ) -> tuple[str, str]:
        uid = self._uid("expr")
        expression = ast.unparse(node)
        inputs = name_usage(node).reads
        graph["blocks"].append({
            "id": uid, "key": "python_node", "python_kind": "expression",
            "python_title": "Expression Python structurée", "python_source": expression,
            "python_inputs": inputs, "python_outputs": [expression], "python_sections": [],
            "python_flow": False, "python_expression": True, "x": x, "y": y,
        })
        for index, name in enumerate(inputs):
            source = definitions.get(name) or self._variable(graph, name, x - 220, y + index * 70)
            self._connect(graph, source, (uid, f"input_{index}"))
        self.report.blocks += 1
        self.report.structured_blocks += 1
        return uid, "output_0"

    def _connect(self, graph: dict, source: tuple[str, str], target: tuple[str, str]) -> None:
        graph["connections"].append({"source": source[0], "source_port": source[1], "target": target[0], "target_port": target[1]})

    def _uid(self, prefix: str) -> str:
        self._counter += 1
        return f"{prefix}_{self._counter}_{uuid4().hex[:5]}"

    def _native(self) -> None:
        self.report.blocks += 1
        self.report.native_blocks += 1


def _simple_call_target(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return True
    return isinstance(node, ast.Attribute) and _simple_call_target(node.value)
