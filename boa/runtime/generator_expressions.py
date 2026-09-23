from __future__ import annotations

import re

from boa.core.module_registry import MODULE_SPECS
from boa.core.module_specs import resolved_module_ports
from boa.functions.models import INPUT_KEYS, function_parameters, function_returns
from boa.runtime.codegen_utils import literal, safe_name, temp_name
from boa.runtime.comment_codegen import block_comment_lines, expression_comment_lines
from boa.runtime.common_codegen import output_var
from boa.runtime.module_codegen import is_module_block, module_expr
from boa.runtime.operator_codegen import is_operator_block, operator_expr
from boa.runtime.python_codegen import python_output_expr


class ExpressionMixin:
    def _value_target_names(self, uid: str, port: str) -> list[str]:
        names: list[str] = []
        for target in self._targets(uid, port):
            block = self.blocks.get(target, {})
            name = safe_name(block.get("variable_name", block.get("subtitle", "")))
            if block.get("key") == "variable" and name:
                names.append(name)
        return names

    def _assigned_variable_names(self) -> set[str]:
        names = {
            safe_name(block.get("variable_name", block.get("subtitle", "")))
            for block in self.blocks.values()
            if block.get("key") == "assign"
        }
        names |= {
            safe_name(block.get("variable_name", block.get("subtitle", "")))
            for block in self.blocks.values()
            if block.get("key") == "variable" and self.incoming.get((block.get("id", ""), "in"))
        }
        names |= {
            safe_name(str(target).lstrip("*"))
            for block in self.blocks.values() if block.get("key") == "multi_assign"
            for target in block.get("assign_targets", [])
        }
        return {name for name in names if name}

    def _input_source_key(self, uid: str, port: str) -> str:
        items = self.incoming.get((uid, port), [])
        return self.blocks.get(items[-1].get("source", ""), {}).get("key", "") if items else ""

    def _expr_waits_for_runtime(self, expression: str) -> bool:
        text = str(expression)
        if "__boa_input_" in text or "__boa_call_" in text:
            return True
        return any(re.search(rf"\b{re.escape(name)}\b", text) for name in self._runtime_names())

    def _mark_runtime(self, names: list[str]) -> None:
        for name in names:
            if name:
                self._runtime_available.add(name)
                self._runtime_emitted.add(name)

    def _runtime_names(self) -> set[str]:
        names = {self._input_var(block.get("id", "")) for block in self.blocks.values() if block.get("key") == "input"}
        names |= {self._call_var(block.get("id", "")) for block in self.blocks.values() if block.get("key") == "call"}
        names |= {
            safe_name(block.get("variable_name", ""))
            for block in self.blocks.values()
            if block.get("key") == "assign"
        }
        for block in self.blocks.values():
            spec = MODULE_SPECS.get(str(block.get("key", "")))
            if spec and spec.flow:
                _, outputs = resolved_module_ports(spec, block.get("module_config", {}))
                names.update(output_var(block.get("id", ""), port.key) for port in outputs if port.value_type != "flow")
            if block.get("key") == "call" and block.get("call_kind") == "project":
                function = self.functions.get(str(block.get("function_id", "")), {})
                names.update(
                    self._function_result_var(block.get("id", ""), port.get("id", ""))
                    for port in function_returns(function)
                )
        return {name for name in names if name}

    def _runtime_deps(self, expression: str) -> set[str]:
        text = str(expression)
        return {name for name in self._runtime_names() if re.search(rf"\b{re.escape(name)}\b", text)}

    def _emit_ready_assignments(self, indent: int) -> None:
        changed = True
        while changed:
            changed = False
            for block in self.blocks.values():
                if block.get("key") != "variable":
                    continue
                name = safe_name(block.get("variable_name", block.get("subtitle", "")))
                if not name or name in self._runtime_emitted:
                    continue
                expression = self._input_expr(block.get("id", ""), "in", "")
                dependencies = self._runtime_deps(expression)
                if dependencies and dependencies <= self._runtime_available:
                    self._emit_input_comments(block.get("id", ""), "in", indent)
                    self._line(f"{name} = {expression}", indent)
                    self._mark_runtime([name])
                    changed = True

    def _targets(self, uid: str, port: str) -> list[str]:
        return [connection.get("target", "") for connection in self.outgoing.get((uid, port), [])]

    def _input_expr(self, uid: str, port: str, default: str = "None") -> str:
        items = self.incoming.get((uid, port), [])
        if len(items) != 1:
            return default
        connection = items[0]
        return self._expr_from_output(connection.get("source", ""), connection.get("source_port", ""))

    def _expr_from_output(self, uid: str, port: str) -> str:
        block = self.blocks.get(uid, {})
        key = str(block.get("key", ""))
        if key == "true":
            return "True"
        if key == "false":
            return "False"
        if key == "none":
            return "None"
        if key == "value":
            return literal(block.get("value_value", ""), block.get("value_type", "any"))
        if key == "variable":
            return safe_name(block.get("variable_name", block.get("subtitle", ""))) or "None"
        if key == "assign":
            target = str(block.get("python_target", "") or "").strip()
            if target and all(part.isidentifier() for part in target.split(".")):
                return target
            return safe_name(block.get("variable_name", block.get("subtitle", ""))) or "None"
        if key == "attribute_get":
            owner = self._input_expr(uid, "object", "None")
            attribute = safe_name(block.get("attribute_name", "")) or "attribut"
            return f"{owner}.{attribute}"
        if key == "await":
            return f"(await {self._input_expr(uid, 'awaitable', 'None')})"
        if key == "set_literal":
            count = max(1, int(block.get("set_item_count", 1) or 1))
            values = [
                self._input_expr(uid, f"element_{index + 1}", "")
                for index in range(count)
                if self.incoming.get((uid, f"element_{index + 1}"))
            ]
            return "{" + ", ".join(values) + "}" if values else "set()"
        if key == "class_attribute":
            return safe_name(block.get("attribute_name", "")) or "None"
        if key == "multi_assign" and port.startswith("result_"):
            try:
                index = int(port.rsplit("_", 1)[1]) - 1
            except (ValueError, IndexError):
                index = -1
            targets = list(block.get("assign_targets", []))
            if 0 <= index < len(targets):
                return safe_name(str(targets[index]).lstrip("*")) or "None"
        if key in {"return", "function_return"} and port.startswith("result_"):
            try:
                index = int(port.rsplit("_", 1)[1])
            except (ValueError, IndexError):
                index = 0
            return self._input_expr(uid, f"value_{index}", "None") if index else "None"
        if key == "with" and port.startswith("alias_"):
            try:
                index = int(port.rsplit("_", 1)[1]) - 1
            except (ValueError, IndexError):
                index = -1
            items = list(block.get("with_items", []))
            if 0 <= index < len(items):
                return safe_name(items[index].get("alias", "")) or "None"
        if key == "input":
            return (self._value_target_names(uid, "value") or [self._input_var(uid)])[0]
        if key == "call" and block.get("call_kind") == "project":
            if not self.incoming.get((uid, "start")):
                function = self.functions.get(str(block.get("function_id", "")), {})
                return self._project_call_expr(block, function)
            return self._function_result_var(uid, port)
        if key == "call":
            if not self.incoming.get((uid, "start")):
                return self._call_expr(block)
            return (self._value_target_names(uid, "result") or [self._call_var(uid)])[0]
        if key in INPUT_KEYS:
            return safe_name(block.get("def_port_name", "")) or "None"
        if is_module_block(key):
            return module_expr(block, port, lambda name, default="None": self._input_expr(uid, name, default))
        if is_operator_block(key):
            return operator_expr(block, lambda name, default="None": self._input_expr(uid, name, default))
        if key in {"and", "or", "xor", "nand", "nor", "xnor", "not"}:
            return self._logic_expr(block, key)
        if key == "for" and port.startswith("temp_"):
            return safe_name(temp_name(block, port)) or "__boa_item"
        if key == "python_node":
            return python_output_expr(block, port)
        return "None"

    def _logic_expr(self, block: dict, key: str) -> str:
        uid = block.get("id", "")
        first = self._input_expr(uid, "a", "False") if key != "not" else self._input_expr(uid, "in", "False")
        second = self._input_expr(uid, "b", "False")
        expressions = {
            "and": f"({first} and {second})",
            "or": f"({first} or {second})",
            "xor": f"(bool({first}) != bool({second}))",
            "not": f"(not {first})",
        }
        base_key = {"nand": "and", "nor": "or", "xnor": "xor"}.get(key, key)
        base = expressions.get(base_key, f"({first} and {second})")
        return f"(not {base})" if key in {"nand", "nor", "xnor"} else base

    def _print_expr(self, block: dict) -> str:
        text = block.get("print_text", block.get("subtitle", ""))
        return f"f{text!r}" if block.get("print_dynamic") else repr(text)

    def _input_var(self, uid: str) -> str:
        return f"__boa_input_{uid or 'tmp'}".replace("-", "_")

    def _call_var(self, uid: str) -> str:
        return f"__boa_call_{uid or 'tmp'}".replace("-", "_")

    def _function_result_var(self, uid: str, port: str) -> str:
        return f"__boa_function_{uid}_{port}".replace("-", "_")

    def _line(self, text: str, indent: int = 0) -> None:
        self.lines.append(("    " * indent) + text if text else "")

    def _emit_comment(self, block: dict, indent: int) -> None:
        for line in block_comment_lines(block):
            self._line(line, indent)

    def _emit_input_comments(self, uid: str, port: str, indent: int) -> None:
        for line in expression_comment_lines(uid, port, self.incoming, self.blocks):
            self._line(line, indent)
