from __future__ import annotations

from boa.core.module_registry import MODULE_SPECS
from boa.core.module_specs import resolved_module_ports, unfiltered_module_ports
from boa.functions.models import INPUT_KEYS, OUTPUT_KEYS, function_returns
from boa.runtime.codegen_utils import input_call_expr, only_imports, ports, safe_name
from boa.runtime.common_codegen import flow_call, output_var
from boa.runtime.module_codegen import is_flow_module_block, is_module_block
from boa.runtime.operator_codegen import is_operator_block


class DispatchMixin:
    def _roots(self) -> list[str]:
        runs = [block.get("id") for block in self.blocks.values() if block.get("key") == "run"]
        if runs:
            return [uid for uid in runs if uid]
        starts = [block.get("id") for block in self.blocks.values() if block.get("key") == "start"]
        if starts:
            return [uid for uid in starts if uid]
        roots: list[str] = []
        data_only = {"true", "false", "none", "value", "variable", "decorator", "attribute_get", "class_attribute", "set_literal"}
        for uid, block in self.blocks.items():
            key = str(block.get("key", ""))
            if key == "function_start":
                roots.append(uid)
                continue
            if key == "function_return" or key in INPUT_KEYS or key in OUTPUT_KEYS or key in data_only:
                continue
            if key == "python_node" and not block.get("python_flow", True):
                continue
            if is_operator_block(key) or key in {"and", "or", "xor", "nand", "nor", "xnor", "not"}:
                continue
            if key == "call" and not self.incoming.get((uid, "start")) and self.outgoing.get((uid, "result")):
                continue
            if key == "await" and not block.get("await_flow", False):
                continue
            if is_module_block(key) and not is_flow_module_block(key):
                continue
            flow_inputs = [port for port in ports(block, "input") if port[1] == "flow"]
            if not flow_inputs or not any((uid, port[0]) in self.incoming for port in flow_inputs):
                roots.append(uid)
        return roots

    def _emit_block(
        self,
        uid: str,
        indent: int,
        seen: set[str],
        stop_uid: str = "",
    ) -> None:
        if not uid or uid == stop_uid or uid in seen:
            return
        block = self.blocks.get(uid)
        if not block:
            return
        seen.add(uid)
        key = str(block.get("key", ""))
        if key not in {"if", "while", "for", "function_start"}:
            self._emit_comment(block, indent)

        if key in {"run", "start"}:
            self._follow(uid, "out", indent, seen, stop_uid)
        elif key == "print":
            self._line(f"print({self._print_expr(block)})", indent)
            self._follow(uid, "done", indent, seen, stop_uid)
        elif key == "input":
            self._emit_input(block, indent)
            self._follow(uid, "done", indent, seen, stop_uid)
        elif key == "assign":
            self._emit_assign(block, indent)
            self._follow(uid, "done", indent, seen, stop_uid)
        elif key == "multi_assign":
            self._emit_multi_assign(block, indent)
            self._follow(uid, "done", indent, seen, stop_uid)
        elif key == "return":
            self._emit_return_block(block, indent)
        elif key == "call":
            if block.get("call_kind") == "project":
                self._emit_function_call(block, indent)
            else:
                self._emit_call(block, indent)
            self._follow(uid, "done", indent, seen, stop_uid)
        elif is_flow_module_block(key):
            self._emit_module_flow(block, indent)
            self._follow(uid, "done", indent, seen, stop_uid)
        elif key == "if":
            self._emit_if(block, indent, seen, stop_uid)
        elif key == "while":
            self._emit_while(block, indent)
            self._follow(uid, "end", indent, seen, stop_uid)
        elif key == "for":
            self._emit_for(block, indent)
            self._follow(uid, "end", indent, seen, stop_uid)
        elif key == "try":
            self._emit_try_block(block, indent)
            self._follow(uid, "done", indent, seen, stop_uid)
        elif key == "match":
            self._emit_match_block(block, indent)
            self._follow(uid, "done", indent, seen, stop_uid)
        elif key == "with":
            self._emit_with_block(block, indent)
            self._follow(uid, "done", indent, seen, stop_uid)
        elif key == "await":
            if block.get("await_flow", False):
                self._emit_await_block(block, indent)
                self._follow(uid, "done", indent, seen, stop_uid)
        elif key == "def_marker":
            function = self.functions.get(str(block.get("definition_id", "")))
            if function:
                self._emit_function_definition(function, indent, self._decorators_for(uid))
            else:
                self._line("# Fonction DEF introuvable", indent)
            self._follow(uid, "done", indent, seen, stop_uid)
        elif key == "class_marker":
            class_def = self.classes.get(str(block.get("definition_id", "")))
            if class_def:
                self._emit_class_definition(class_def, indent, self._decorators_for(uid))
            else:
                self._line("# Classe introuvable", indent)
            self._follow(uid, "done", indent, seen, stop_uid)
        elif key == "tp" and block.get("tp_role") == "in":
            self._jump_tp(block, indent, seen, stop_uid)
        elif key == "end":
            return
        elif key == "function_start":
            self._follow(uid, "start", indent, seen, stop_uid)
        elif key == "function_return":
            self._emit_return_block(block, indent)
        elif key == "python_node":
            self._emit_python_node(block, indent)
            self._follow(uid, "done", indent, seen, stop_uid)
        elif key == "empty":
            raw = block.get("raw_code", "pass") or "pass"
            if not only_imports(raw):
                for line in str(raw).splitlines():
                    self._line(line, indent)
        else:
            self._line(f"# Bloc non généré : {block.get('title', key)}", indent)

    def _emit_assign(self, block: dict, indent: int) -> None:
        raw_target = str(block.get("python_target", "") or "").strip()
        name = raw_target if _valid_assignment_target(raw_target) else (safe_name(block.get("variable_name", block.get("subtitle", ""))) or "variable")
        uid = block.get("id", "")
        annotation = str(block.get("python_annotation", "") or "").strip()
        has_value = bool(self.incoming.get((uid, "value")))
        if annotation and not has_value:
            self._line(f"{name}: {annotation}", indent)
        else:
            expression = self._input_expr(uid, "value", "None")
            prefix = f"{name}: {annotation}" if annotation else name
            self._line(f"{prefix} = {expression}", indent)
        self._mark_runtime([name])

    def _emit_python_node(self, block: dict, indent: int) -> None:
        if block.get("python_expression"):
            return
        if block.get("python_kind") == "import" and block.get("python_import_header"):
            return
        sections = list(block.get("python_sections", []))
        if sections:
            self._emit_sections(sections, indent)
            return
        source = str(block.get("python_source", "pass") or "pass")
        for line in source.splitlines():
            self._line(line, indent)

    def _emit_sections(self, sections: list[dict], indent: int) -> None:
        for section in sections:
            for line in str(section.get("header", "") or "if True:").splitlines():
                self._line(line, indent)
            nested = list(section.get("sections", []))
            if nested:
                self._emit_sections(nested, indent + 1)
            else:
                self._emit_inner(section.get("graph", {}) or {}, indent + 1)

    def _emit_module_flow(self, block: dict, indent: int) -> None:
        uid = block.get("id", "")
        output_ports, call = flow_call(block, lambda port, default="None": self._input_expr(uid, port, default))
        variables = [output_var(uid, port) for port in output_ports]
        spec = MODULE_SPECS.get(str(block.get("key", "")))
        _, all_outputs = unfiltered_module_ports(spec, block.get("module_config", {})) if spec else ((), ())
        all_value_ports = [port.key for port in all_outputs if port.value_type != "flow"]
        if not output_ports:
            self._line(call, indent)
        elif len(all_value_ports) > 1 and output_ports != all_value_ports:
            result = output_var(uid, "outputs")
            self._line(f"{result} = {call}", indent)
            for port, variable in zip(output_ports, variables):
                self._line(f"{variable} = {result}[{all_value_ports.index(port)}]", indent)
        elif len(output_ports) == 1:
            self._line(f"{variables[0]} = {call}", indent)
        else:
            self._line(f"{', '.join(variables)} = {call}", indent)
        self._mark_runtime(variables)
        for port, variable in zip(output_ports, variables):
            names = self._value_target_names(uid, port)
            for name in names:
                self._line(f"{name} = {variable}", indent)
            self._mark_runtime(names)
        self._emit_ready_assignments(indent)

    def _emit_input(self, block: dict, indent: int) -> None:
        uid = block.get("id", "")
        names = self._value_target_names(uid, "value")
        expression = input_call_expr(block)
        if len(names) == 1:
            self._line(f"{names[0]} = {expression}", indent)
            self._mark_runtime(names)
            self._emit_ready_assignments(indent)
            return
        variable = self._input_var(uid)
        self._line(f"{variable} = {expression}", indent)
        self._mark_runtime([variable])
        for name in names:
            self._line(f"{name} = {variable}", indent)
        self._mark_runtime(names)
        self._emit_ready_assignments(indent)

    def _emit_call(self, block: dict, indent: int) -> None:
        uid = block.get("id", "")
        expression = self._call_expr(block)
        names = self._value_target_names(uid, "result")
        if len(names) == 1:
            self._line(f"{names[0]} = {expression}", indent)
            self._mark_runtime(names)
            self._emit_ready_assignments(indent)
            return
        if names or self.outgoing.get((uid, "result")):
            variable = self._call_var(uid)
            self._line(f"{variable} = {expression}", indent)
            self._mark_runtime([variable])
            for name in names:
                self._line(f"{name} = {variable}", indent)
            self._mark_runtime(names)
            self._emit_ready_assignments(indent)
            return
        self._line(expression, indent)

    def _emit_function_call(self, block: dict, indent: int) -> None:
        function = self.functions.get(str(block.get("function_id", "")))
        if not function:
            self._line("# Fonction introuvable", indent)
            return
        uid = block.get("id", "")
        call = self._project_call_expr(block, function)
        returns = function_returns(function)
        variables = [self._function_result_var(uid, port.get("id", "")) for port in returns]
        if not variables:
            self._line(call, indent)
            return
        left = ", ".join(variables)
        self._line(f"{left} = {call}", indent)
        self._mark_runtime(variables)
        for port, variable in zip(returns, variables):
            names = self._value_target_names(uid, port.get("id", ""))
            for name in names:
                self._line(f"{name} = {variable}", indent)
            self._mark_runtime(names)
        self._emit_ready_assignments(indent)

    def _emit_function_return(self, block: dict, indent: int) -> None:
        if (self.function_definition or {}).get("python_inline"):
            return
        returns = function_returns(self.function_definition or {})
        values = [self._input_expr(port.get("block_id", ""), "value", "None") for port in returns]
        if not values:
            self._line("return None", indent)
        elif len(values) == 1:
            self._line(f"return {values[0]}", indent)
        else:
            self._line(f"return {', '.join(values)}", indent)


def _valid_assignment_target(value: str) -> bool:
    return bool(value) and all(part.isidentifier() for part in value.split("."))
