from __future__ import annotations

from collections import deque

from boa.runtime.codegen_utils import safe_name
from boa.runtime.module_codegen import is_flow_module_block


class ControlFlowMixin:
    def _emit_if(self, block: dict, indent: int, seen: set[str], outer_stop: str = "") -> None:
        uid = block.get("id", "")
        self._emit_input_comments(uid, "condition", indent)
        self._emit_comment(block, indent)
        self._line(f"if {self._input_expr(uid, 'condition', 'True')}:", indent)
        true_targets = self._targets(uid, "true")
        false_targets = self._targets(uid, "false")
        imported_has_else = block.get("python_has_else")

        if imported_has_else is False:
            continuation = false_targets[0] if false_targets else ""
            wrote = self._branch_targets(true_targets, indent + 1, set(seen), continuation or outer_stop)
            if not wrote:
                self._line("pass", indent + 1)
            if continuation and continuation != outer_stop:
                self._emit_block(continuation, indent, seen, outer_stop)
            return

        merge = self._common_merge(true_targets, false_targets, outer_stop)
        wrote_true = self._branch_targets(true_targets, indent + 1, set(seen), merge or outer_stop)
        if not wrote_true:
            self._line("pass", indent + 1)
        if false_targets:
            self._line("else:", indent)
            wrote_false = self._branch_targets(false_targets, indent + 1, set(seen), merge or outer_stop)
            if not wrote_false:
                self._line("pass", indent + 1)
        if merge and merge != outer_stop:
            self._emit_block(merge, indent, seen, outer_stop)

    def _branch_targets(self, targets: list[str], indent: int, seen: set[str], stop_uid: str) -> bool:
        wrote = False
        before = len(self.lines)
        for target in targets:
            if target == stop_uid:
                continue
            self._emit_block(target, indent, seen, stop_uid)
        wrote = len(self.lines) > before
        return wrote

    def _common_merge(self, left: list[str], right: list[str], outer_stop: str = "") -> str:
        if not left or not right:
            return ""
        left_dist = self._flow_distances(left, outer_stop)
        right_dist = self._flow_distances(right, outer_stop)
        common = set(left_dist) & set(right_dist)
        if outer_stop in common:
            common.remove(outer_stop)
        if not common:
            return ""
        return min(common, key=lambda uid: (max(left_dist[uid], right_dist[uid]), left_dist[uid] + right_dist[uid]))

    def _flow_distances(self, starts: list[str], stop_uid: str = "") -> dict[str, int]:
        distances: dict[str, int] = {}
        queue = deque((uid, 0) for uid in starts if uid)
        while queue:
            uid, distance = queue.popleft()
            if uid in distances and distances[uid] <= distance:
                continue
            distances[uid] = distance
            if uid == stop_uid:
                continue
            for target in self._flow_successors(uid):
                queue.append((target, distance + 1))
        return distances

    def _flow_successors(self, uid: str) -> list[str]:
        block = self.blocks.get(uid, {})
        key = str(block.get("key", ""))
        flow_ports = {
            "run": ("out",), "start": ("out",), "print": ("done",), "input": ("done",),
            "assign": ("done",), "multi_assign": ("done",), "call": ("done",), "if": ("true", "false"),
            "while": ("end",), "for": ("end",), "try": ("done",), "match": ("done",), "with": ("done",), "await": ("done",), "def_marker": ("done",),
            "class_marker": ("done",), "function_start": ("start",), "python_node": ("done",),
        }.get(key, ())
        if is_flow_module_block(key):
            flow_ports = ("done",)
        result: list[str] = []
        for port in flow_ports:
            result.extend(self._targets(uid, port))
        return result

    def _emit_while(self, block: dict, indent: int) -> None:
        uid = block.get("id", "")
        self._emit_input_comments(uid, "condition", indent)
        self._emit_comment(block, indent)
        self._line(f"while {self._input_expr(uid, 'condition', 'True')}:", indent)
        self._emit_inner(block.get("inner_graph", {}), indent + 1)

    def _emit_for(self, block: dict, indent: int) -> None:
        names = [safe_name(name) for name in block.get("for_temp_outputs", []) if safe_name(name)]
        target = names[0] if len(names) == 1 else (f"({', '.join(names)})" if names else "__boa_item")
        uid = block.get("id", "")
        self._emit_input_comments(uid, "iterable", indent)
        self._emit_comment(block, indent)
        prefix = "async " if block.get("python_async") else ""
        self._line(f"{prefix}for {target} in {self._input_expr(uid, 'iterable', 'range(0)') }:", indent)
        self._emit_inner(block.get("inner_graph", {}), indent + 1)

    def _emit_inner(self, graph: dict, indent: int) -> None:
        child = self.__class__(
            graph or {},
            self.context,
            self.functions,
            self.classes,
            self.function_definition,
            self.class_definition,
        )
        body = [line for line in child.fragment() if line.strip()]
        if not body:
            self._line("pass", indent)
            return
        for line in body:
            self._line(line, indent)

    def _follow(self, uid: str, port: str, indent: int, seen: set[str], stop_uid: str = "") -> None:
        for target in self._targets(uid, port):
            self._emit_block(target, indent, seen, stop_uid)

    def _jump_tp(self, block: dict, indent: int, seen: set[str], stop_uid: str = "") -> None:
        number = block.get("tp_number")
        for other in self.blocks.values():
            if other.get("key") == "tp" and other.get("tp_role") == "out" and other.get("tp_number") == number:
                self._emit_comment(other, indent)
                self._follow(other.get("id", ""), "tp", indent, seen, stop_uid)
                return
        self._line(f"# TP#{number} sans sortie liée", indent)

    def _decorators_for(self, target_uid: str) -> list[str]:
        blocks = [
            block
            for block in self.blocks.values()
            if block.get("key") == "decorator"
            and block.get("decorator_attached")
            and str(block.get("decorator_target", "")) == str(target_uid)
        ]
        blocks.sort(key=lambda block: int(block.get("decorator_order", 0)))
        return [f"@{str(block.get('decorator_expression', '')).lstrip('@').strip()}" for block in blocks]
