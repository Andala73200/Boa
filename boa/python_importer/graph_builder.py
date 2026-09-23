from __future__ import annotations
import ast
from dataclasses import dataclass
from uuid import uuid4
from boa.core.module_registry import MODULE_SPECS
from boa.python_importer.analysis import leading_comment, name_usage, node_source
from boa.python_importer.expression_builder import ExpressionBuilder
from boa.python_importer.models import ConversionReport
from boa.python_importer.native_calls import print_spec
from boa.python_importer.structured import node_identity, sections_for
@dataclass(slots=True)
class FlowTail: uid: str; port: str
class GraphBuilder:
    X_GAP, BRANCH_GAP = 310, 210
    def __init__(self, source: str, comments: dict[int, str], report: ConversionReport, engine) -> None:
        self.source = source; self.comments = comments
        self.report = report; self.engine = engine
        self.expressions = ExpressionBuilder(source, report); self._counter = 0
    def module_graph(self, nodes: list[ast.stmt]) -> dict:
        graph = {"blocks": [{"id": "run", "key": "run", "x": 0, "y": 0}], "connections": []}
        self._sequence(graph, nodes, [FlowTail("run", "out")], {}, 280, 0, "", "")
        return graph
    def function_body(self, graph: dict, nodes: list[ast.stmt], initial_defs: dict, function_id: str) -> None:
        tails, x = self._sequence(graph, nodes, [FlowTail("function_start", "start")], dict(initial_defs), -80, 0, function_id, "")
        explicit = [block for block in graph["blocks"] if block.get("key") == "return"]
        if not tails and explicit:
            self._promote_return(graph, explicit[0])
        else:
            anchor = self._block(graph, "function_return")
            anchor.update({"return_values": [], "x": max(float(anchor.get("x", 420)), x + 120), "y": 0})
            for tail in tails:
                self._flow(graph, tail, FlowTail("function_return", "start"))
        self._link_returns_to_outputs(graph)
    def inner_graph(self, nodes: list[ast.stmt], function_id: str = "", class_id: str = "") -> dict:
        graph = {"blocks": [{"id": "start", "key": "start", "x": 0, "y": 0}], "connections": []}
        self._sequence(graph, nodes, [FlowTail("start", "out")], {}, 260, 0, function_id, class_id)
        return graph
    def class_graph(self, nodes: list[ast.stmt], class_id: str) -> dict:
        graph = {"blocks": [], "connections": [], "class_columns": 1}
        definitions: dict[str, tuple[str, str]] = {}
        column = 0
        for node in nodes:
            if isinstance(node, (ast.Import, ast.ImportFrom)) or _is_docstring(node):
                continue
            x = column * 320 + 44
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function = self.engine.register_function(node, owner_class_id=class_id)
                marker = self._marker(graph, "def_marker", function["id"], function["name"], node.decorator_list, x, 92, column, [])
                definitions[node.name] = (marker["id"], "definition")
            elif isinstance(node, ast.ClassDef):
                nested = self.engine.register_class(node, owner_class_id=class_id)
                marker = self._marker(graph, "class_marker", nested["id"], nested["name"], node.decorator_list, x, 92, column, [])
                definitions[node.name] = (marker["id"], "definition")
            else:
                block = self._class_member(node, graph, definitions, x, 92, column)
                if block:
                    for index, name in enumerate(name_usage(node).writes):
                        definitions[name] = (block["id"], "attribute" if block.get("key") == "class_attribute" else f"result_{index + 1}")
            column += 1
        graph["class_columns"] = max(1, column + 1)
        return graph
    def statement_block(self, node: ast.stmt) -> dict:
        graph = {"blocks": [], "connections": []}
        self._sequence(graph, [node], [], {}, 0, 0, "", "")
        return graph["blocks"][-1] if graph["blocks"] else {"key": "python_node"}
    def _sequence(self, graph, nodes, tails, definitions, x, y, function_id, class_id):
        current = list(tails)
        for node in nodes:
            if isinstance(node, (ast.Import, ast.ImportFrom)) or _is_docstring(node):
                continue
            current, x = self._statement(graph, node, current, definitions, x, y, function_id, class_id)
        return current, x
    def _statement(self, graph, node, tails, definitions, x, y, function_id, class_id):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function = self.engine.register_function(node, function_id, class_id, set(definitions))
            captures = [name for name in function.get("captured_names", []) if name in definitions]
            marker = self._marker(graph, "def_marker", function["id"], function["name"], node.decorator_list, x, y, -1, captures)
            self._connect_tails(graph, tails, marker["id"], "start")
            for index, name in enumerate(captures):
                self._data(graph, definitions[name], (marker["id"], f"capture_{index + 1}"))
            return [FlowTail(marker["id"], "done")], x + self.X_GAP
        if isinstance(node, ast.ClassDef):
            class_def = self.engine.register_class(node, class_id)
            marker = self._marker(graph, "class_marker", class_def["id"], class_def["name"], node.decorator_list, x, y, -1, [])
            self._connect_tails(graph, tails, marker["id"], "start")
            return [FlowTail(marker["id"], "done")], x + self.X_GAP
        if isinstance(node, ast.If):
            return self._if(graph, node, tails, definitions, x, y, function_id, class_id)
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            if node.orelse or (not isinstance(node, ast.While) and not _target_names(node.target)):
                return self._fallback(graph, node, tails, x, y, function_id, class_id)
            return self._loop(graph, node, tails, definitions, x, y, function_id, class_id)
        if isinstance(node, ast.Try):
            return self._try(graph, node, tails, x, y, function_id, class_id)
        if isinstance(node, ast.Match):
            return self._match(graph, node, tails, definitions, x, y, function_id, class_id)
        if isinstance(node, (ast.With, ast.AsyncWith)):
            return self._with(graph, node, tails, definitions, x, y, function_id, class_id)
        if isinstance(node, ast.Return):
            self._return(graph, node, tails, definitions, x, y)
            return [], x + self.X_GAP
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            result = self._assignment(graph, node, tails, definitions, x, y)
            if result:
                return result, x + self.X_GAP
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Await):
            awaited = self.expressions.build(graph, node.value, definitions, x, y)
            block = self._block(graph, awaited[0])
            if block.get("key") == "await":
                block["await_flow"] = True
                self._connect_tails(graph, tails, awaited[0], "start")
                return [FlowTail(awaited[0], "done")], x + self.X_GAP
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            spec = print_spec(node.value)
            if spec:
                uid = self._uid("print"); graph["blocks"].append({"id": uid, "key": "print", **spec, "x": x, "y": y})
                self._connect_tails(graph, tails, uid, "start"); self._native()
                return [FlowTail(uid, "done")], x + self.X_GAP
            call = self.expressions.build(graph, node.value, definitions, x, y)
            block = self._block(graph, call[0])
            key = str(block.get("key", ""))
            if key in {"call", "input"} or _is_flow_module(key):
                if key == "call": block["call_flow"] = True
                self._connect_tails(graph, tails, call[0], "start")
                return [FlowTail(call[0], "done")], x + self.X_GAP
        return self._fallback(graph, node, tails, x, y, function_id, class_id)
    def _assignment(self, graph, node, tails, definitions, x, y):
        target = node.target if isinstance(node, (ast.AnnAssign, ast.AugAssign)) else (node.targets[0] if len(node.targets) == 1 else None)
        if isinstance(target, ast.Attribute):
            value_node = node.value
            if isinstance(node, ast.AugAssign):
                value_node = ast.BinOp(left=target, op=node.op, right=node.value)
            uid = self._uid("assign")
            target_text = ast.unparse(target)
            graph["blocks"].append({"id": uid, "key": "assign", "variable_name": target_text, "python_target": target_text, "variable_type": "any", "python_annotation": ast.unparse(node.annotation) if isinstance(node, ast.AnnAssign) else "", "x": x, "y": y})
            self._connect_tails(graph, tails, uid, "start")
            if value_node is not None: self._data(graph, self.expressions.build(graph, value_node, definitions, x - 190, y + 90), (uid, "value"))
            self._native(); return [FlowTail(uid, "done")]
        if isinstance(target, (ast.Tuple, ast.List)) and isinstance(node, ast.Assign):
            targets = [ast.unparse(item) for item in target.elts]
            uid = self._uid("multi_assign")
            graph["blocks"].append({"id": uid, "key": "multi_assign", "assign_targets": targets, "x": x, "y": y})
            self._connect_tails(graph, tails, uid, "start")
            self._data(graph, self.expressions.build(graph, node.value, definitions, x - 190, y + 90), (uid, "value"))
            for index, item in enumerate(target.elts):
                for name in _target_names(item):
                    definitions[name] = (uid, f"result_{index + 1}")
            self._native()
            return [FlowTail(uid, "done")]
        if not isinstance(target, ast.Name):
            return None
        value_node = node.value
        annotation = ast.unparse(node.annotation) if isinstance(node, ast.AnnAssign) else ""
        if isinstance(node, ast.AugAssign):
            value_node = ast.BinOp(left=ast.Name(id=target.id, ctx=ast.Load()), op=node.op, right=node.value)
        value = self.expressions.build(graph, value_node, definitions, x - 190, y + 90) if value_node is not None else None
        flow_tails = list(tails)
        if value:
            value_key = str(self._block(graph, value[0]).get("key", ""))
            if value_key == "input" or _is_flow_module(value_key):
                self._connect_tails(graph, flow_tails, value[0], "start")
                flow_tails = [FlowTail(value[0], "done")]
        uid = self._uid("assign")
        graph["blocks"].append({"id": uid, "key": "assign", "variable_name": target.id, "variable_type": "any", "python_annotation": annotation, "x": x, "y": y})
        self._connect_tails(graph, flow_tails, uid, "start")
        if value is not None:
            self._data(graph, value, (uid, "value"))
        definitions[target.id] = (uid, "result")
        self._native()
        return [FlowTail(uid, "done")]
    def _return(self, graph, node, tails, definitions, x, y):
        values = list(node.value.elts) if isinstance(node.value, (ast.Tuple, ast.List)) else ([] if node.value is None else [node.value])
        labels = [_return_label(item, index, len(values)) for index, item in enumerate(values)]
        uid = self._uid("return")
        graph["blocks"].append({"id": uid, "key": "return", "return_values": labels, "x": x, "y": y})
        self._connect_tails(graph, tails, uid, "start")
        for index, value in enumerate(values):
            source = self.expressions.build(graph, value, definitions, x - 180, y + 80 + index * 70)
            self._data(graph, source, (uid, f"value_{index + 1}"))
        self._native()
    def _if(self, graph, node, tails, definitions, x, y, function_id, class_id):
        uid = self._uid("if")
        graph["blocks"].append({"id": uid, "key": "if", "python_has_else": bool(node.orelse), "x": x, "y": y})
        self._connect_tails(graph, tails, uid, "start")
        self._data(graph, self.expressions.build(graph, node.test, definitions, x - 180, y + 100), (uid, "condition"))
        true_tails, true_x = self._sequence(graph, node.body, [FlowTail(uid, "true")], dict(definitions), x + self.X_GAP, y - self.BRANCH_GAP, function_id, class_id)
        false_tails, false_x = self._sequence(graph, node.orelse, [FlowTail(uid, "false")], dict(definitions), x + self.X_GAP, y + self.BRANCH_GAP, function_id, class_id) if node.orelse else ([FlowTail(uid, "false")], x + self.X_GAP)
        self._native()
        return [*true_tails, *false_tails], max(true_x, false_x)
    def _loop(self, graph, node, tails, definitions, x, y, function_id, class_id):
        uid = self._uid("loop")
        if isinstance(node, ast.While):
            block = {"id": uid, "key": "while", "inner_graph": self.inner_graph(node.body, function_id, class_id), "x": x, "y": y}
            value, input_port = self.expressions.build(graph, node.test, definitions, x - 190, y + 100), "condition"
        else:
            names = _target_names(node.target)
            block = {"id": uid, "key": "for", "inner_graph": self.inner_graph(node.body, function_id, class_id), "for_temp_outputs": names, "python_async": isinstance(node, ast.AsyncFor), "x": x, "y": y}
            value, input_port = self.expressions.build(graph, node.iter, definitions, x - 190, y + 100), "iterable"
        graph["blocks"].append(block)
        self._connect_tails(graph, tails, uid, "start")
        self._data(graph, value, (uid, input_port))
        self._native()
        return [FlowTail(uid, "end")], x + self.X_GAP
    def _try(self, graph, node, tails, x, y, function_id, class_id):
        uid = self._uid("try")
        handlers = [{"type": ast.unparse(item.type) if item.type else "", "name": item.name or "", "graph": self.inner_graph(item.body, function_id, class_id)} for item in node.handlers]
        block = {"id": uid, "key": "try", "try_graph": self.inner_graph(node.body, function_id, class_id), "try_handlers": handlers, "try_else_graph": self.inner_graph(node.orelse, function_id, class_id) if node.orelse else {}, "try_finally_graph": self.inner_graph(node.finalbody, function_id, class_id) if node.finalbody else {}, "x": x, "y": y}
        graph["blocks"].append(block); self._connect_tails(graph, tails, uid, "start"); self._native()
        return [FlowTail(uid, "done")], x + self.X_GAP
    def _match(self, graph, node, tails, definitions, x, y, function_id, class_id):
        uid = self._uid("match")
        cases = [{"pattern": ast.unparse(item.pattern), "guard": ast.unparse(item.guard) if item.guard else "", "graph": self.inner_graph(item.body, function_id, class_id)} for item in node.cases]
        graph["blocks"].append({"id": uid, "key": "match", "match_cases": cases, "x": x, "y": y})
        self._connect_tails(graph, tails, uid, "start")
        self._data(graph, self.expressions.build(graph, node.subject, definitions, x - 190, y + 90), (uid, "value"))
        self._native(); return [FlowTail(uid, "done")], x + self.X_GAP
    def _with(self, graph, node, tails, definitions, x, y, function_id, class_id):
        uid = self._uid("with")
        items = []
        for index, item in enumerate(node.items):
            items.append({"alias": ast.unparse(item.optional_vars) if item.optional_vars else ""})
            source = self.expressions.build(graph, item.context_expr, definitions, x - 200, y + 70 + index * 80)
            self._data(graph, source, (uid, f"context_{index + 1}"))
        graph["blocks"].append({"id": uid, "key": "with", "with_items": items, "with_graph": self.inner_graph(node.body, function_id, class_id), "with_async": isinstance(node, ast.AsyncWith), "x": x, "y": y})
        self._connect_tails(graph, tails, uid, "start"); self._native()
        return [FlowTail(uid, "done")], x + self.X_GAP
    def _class_member(self, node, graph, definitions, x, y, order):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            target = node.target if isinstance(node, ast.AnnAssign) else (node.targets[0] if len(node.targets) == 1 else None)
            if isinstance(target, ast.Name):
                uid = self._uid("attribute")
                annotation = ast.unparse(node.annotation) if isinstance(node, ast.AnnAssign) else ""
                value = node.value
                block = {"id": uid, "key": "class_attribute", "attribute_name": target.id, "attribute_annotation": annotation, "attribute_has_default": value is not None, "class_order": order, "x": x, "y": y}
                graph["blocks"].append(block)
                if value is not None:
                    self._data(graph, self.expressions.build(graph, value, definitions, x - 170, y + 75), (uid, "value"))
                self._native(); return block
        block = self._structured(node, x, y, "", ""); block["class_order"] = order; graph["blocks"].append(block); return block
    def _fallback(self, graph, node, tails, x, y, function_id, class_id):
        block = self._structured(node, x, y, function_id, class_id); graph["blocks"].append(block)
        self._connect_tails(graph, tails, block["id"], "start")
        return [FlowTail(block["id"], "done")], x + self.X_GAP
    def _structured(self, node, x, y, function_id, class_id):
        kind, title = node_identity(node)
        usage = name_usage(node)
        block = {"id": self._uid("structured"), "key": "python_node", "python_kind": kind, "python_title": title, "python_source": node_source(self.source, node), "python_inputs": usage.reads, "python_outputs": usage.writes, "python_sections": sections_for(node, lambda body: self.inner_graph(body, function_id, class_id)), "python_flow": True, "x": x, "y": y}
        comment = leading_comment(node, self.comments, self.source)
        if comment: block["comment"] = comment
        self.report.blocks += 1; self.report.structured_blocks += 1
        return block
    def _marker(self, graph, key, definition_id, name, decorators, x, y, order, captures):
        uid = self._uid("definition")
        block = {
            "id": uid, "key": key, "definition_id": definition_id,
            "definition_name": name, "definition_captures": list(captures or []),
            "x": x, "y": y,
        }
        if order >= 0: block["class_order"] = order
        graph["blocks"].append(block)
        for index, decorator in enumerate(decorators):
            graph["blocks"].append({"id": self._uid("decorator"), "key": "decorator", "decorator_expression": ast.unparse(decorator), "decorator_target": uid, "decorator_order": index, "decorator_attached": True, "x": x, "y": y - 28 * (len(decorators) - index)})
            self._native()
        self._native(); return block
    def _promote_return(self, graph, candidate):
        anchor = self._block(graph, "function_return")
        anchor.update({key: value for key, value in candidate.items() if key not in {"id", "key"}})
        old = candidate["id"]
        for connection in graph["connections"]:
            if connection.get("source") == old: connection["source"] = "function_return"
            if connection.get("target") == old: connection["target"] = "function_return"
        graph["blocks"] = [block for block in graph["blocks"] if block.get("id") != old]
    def _link_returns_to_outputs(self, graph):
        outputs = sorted((block for block in graph["blocks"] if block.get("key") in {"def_output", "def_output_p"}), key=lambda item: int(item.get("def_order", 0)))
        returns = [block for block in graph["blocks"] if block.get("key") in {"return", "function_return"}]
        for block in returns:
            for index, output in enumerate(outputs):
                if index < len(block.get("return_values", [])):
                    self._data(graph, (block["id"], f"result_{index + 1}"), (output["id"], "value"))
    @staticmethod
    def _block(graph, uid): return next((item for item in graph["blocks"] if item.get("id") == uid), {})
    def _connect_tails(self, graph, tails, uid, port):
        for tail in tails: self._flow(graph, tail, FlowTail(uid, port))
    @staticmethod
    def _flow(graph, source, target): graph["connections"].append({"source": source.uid, "source_port": source.port, "target": target.uid, "target_port": target.port})
    @staticmethod
    def _data(graph, source, target): graph["connections"].append({"source": source[0], "source_port": source[1], "target": target[0], "target_port": target[1]})
    def _uid(self, prefix): self._counter += 1; return f"{prefix}_{self._counter}_{uuid4().hex[:5]}"
    def _native(self): self.report.blocks += 1; self.report.native_blocks += 1
def _is_flow_module(key): return bool((spec := MODULE_SPECS.get(str(key))) and spec.flow)
def _is_docstring(node): return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
def _target_names(node):
    if isinstance(node, ast.Name): return [node.id]
    if isinstance(node, ast.Starred): return _target_names(node.value)
    if isinstance(node, (ast.Tuple, ast.List)): return [name for item in node.elts for name in _target_names(item)]
    return []
def _return_label(node, index, count):
    if isinstance(node, ast.Name): return node.id
    if isinstance(node, ast.Attribute): return node.attr
    return "valeur" if count == 1 else f"valeur_{index + 1}"
