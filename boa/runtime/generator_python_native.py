from __future__ import annotations

from boa.functions.models import function_returns
from boa.runtime.codegen_utils import safe_name


class PythonNativeMixin:

    def _emit_await_block(self, block: dict, indent: int) -> None:
        uid = str(block.get("id", ""))
        self._line(f"await {self._input_expr(uid, 'awaitable', 'None')}", indent)

    def _emit_return_block(self, block: dict, indent: int) -> None:
        uid = str(block.get("id", ""))
        if block.get("key") == "function_return" and "return_values" not in block:
            returns = function_returns(self.function_definition or {})
            values = [self._input_expr(port.get("block_id", ""), "value", "None") for port in returns]
            if not values:
                self._line("return None", indent)
            elif len(values) == 1:
                self._line(f"return {values[0]}", indent)
            else:
                self._line(f"return {', '.join(values)}", indent)
            return
        labels = list(block.get("return_values", []))
        values = [self._input_expr(uid, f"value_{index + 1}", "None") for index in range(len(labels))]
        if not values:
            self._line("return", indent)
        elif len(values) == 1:
            self._line(f"return {values[0]}", indent)
        else:
            self._line(f"return {', '.join(values)}", indent)

    def _emit_multi_assign(self, block: dict, indent: int) -> None:
        targets = [str(item).strip() for item in block.get("assign_targets", []) if str(item).strip()]
        if not targets:
            targets = ["valeur"]
        value = self._input_expr(str(block.get("id", "")), "value", "None")
        self._line(f"{', '.join(targets)} = {value}", indent)
        self._mark_runtime([safe_name(item.lstrip("*")) for item in targets])

    def _emit_try_block(self, block: dict, indent: int) -> None:
        self._line("try:", indent)
        self._emit_inner(block.get("try_graph", {}) or {}, indent + 1)
        for handler in block.get("try_handlers", []):
            exception = str(handler.get("type", "")).strip()
            name = safe_name(handler.get("name", ""))
            header = "except"
            if exception:
                header += f" {exception}"
            if name:
                header += f" as {name}"
            self._line(f"{header}:", indent)
            self._emit_inner(handler.get("graph", {}) or {}, indent + 1)
        if block.get("try_else_graph"):
            self._line("else:", indent)
            self._emit_inner(block.get("try_else_graph", {}) or {}, indent + 1)
        if block.get("try_finally_graph"):
            self._line("finally:", indent)
            self._emit_inner(block.get("try_finally_graph", {}) or {}, indent + 1)

    def _emit_match_block(self, block: dict, indent: int) -> None:
        uid = str(block.get("id", ""))
        self._line(f"match {self._input_expr(uid, 'value', 'None')}:", indent)
        cases = list(block.get("match_cases", []))
        if not cases:
            self._line("case _:", indent + 1)
            self._line("pass", indent + 2)
            return
        for item in cases:
            pattern = str(item.get("pattern", "_")).strip() or "_"
            guard = str(item.get("guard", "")).strip()
            header = f"case {pattern}" + (f" if {guard}" if guard else "")
            self._line(f"{header}:", indent + 1)
            self._emit_inner(item.get("graph", {}) or {}, indent + 2)

    def _emit_with_block(self, block: dict, indent: int) -> None:
        uid = str(block.get("id", ""))
        parts = []
        for index, item in enumerate(block.get("with_items", [])):
            expression = self._input_expr(uid, f"context_{index + 1}", "None")
            alias = str(item.get("alias", "")).strip()
            parts.append(expression + (f" as {alias}" if alias else ""))
        prefix = "async " if block.get("with_async") else ""
        self._line(f"{prefix}with {', '.join(parts) if parts else 'None'}:", indent)
        self._emit_inner(block.get("with_graph", {}) or {}, indent + 1)

    def _emit_class_attribute(self, block: dict, indent: int) -> None:
        name = safe_name(block.get("attribute_name", "")) or "attribut"
        annotation = str(block.get("attribute_annotation", "")).strip()
        uid = str(block.get("id", ""))
        has_value = bool(self.incoming.get((uid, "value")))
        if has_value:
            left = f"{name}: {annotation}" if annotation else name
            self._line(f"{left} = {self._input_expr(uid, 'value', 'None')}", indent)
        elif annotation:
            self._line(f"{name}: {annotation}", indent)
        else:
            self._line(f"{name} = None", indent)
