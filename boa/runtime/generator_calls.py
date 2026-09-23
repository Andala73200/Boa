from __future__ import annotations

from boa.functions.models import function_parameters
from boa.runtime.codegen_utils import safe_call_target, safe_name


class CallMixin:
    def _call_expr(self, block: dict) -> str:
        target = safe_call_target(block.get("call_target", block.get("subtitle", ""))) or "fonction"
        uid = block.get("id", "")
        arguments = [
            self._input_expr(uid, f"arg_{index + 1}", "None")
            for index in range(max(0, min(32, int(block.get("call_arg_count", 0) or 0))))
        ]
        for index in range(max(0, int(block.get("call_vararg_count", 0) or 0))):
            port = f"vararg_{index + 1}"
            if self.incoming.get((uid, port)):
                arguments.append(self._input_expr(uid, port, "None"))
        for index, name in enumerate(block.get("call_kwarg_names", [])):
            port = f"kwarg_{index + 1}"
            if not self.incoming.get((uid, port)):
                continue
            keyword = safe_name(name) or f"kwarg_{index + 1}"
            arguments.append(f"{keyword}={self._input_expr(uid, port, 'None')}")
        return f"{target}({', '.join(arguments)})"

    def _project_call_expr(self, block: dict, function: dict) -> str:
        uid = block.get("id", "")
        arguments: list[str] = []
        for port in function_parameters(function):
            kind = str(port.get("kind", "normal"))
            port_id = str(port.get("id", ""))
            if kind == "args":
                prefix = f"{port_id}__arg_"
                for key in self._connected_input_keys(uid, prefix):
                    arguments.append(self._input_expr(uid, key, "None"))
            elif kind == "kwargs":
                prefix = f"{port_id}__kwarg_"
                for key in self._connected_input_keys(uid, prefix):
                    index = max(0, _suffix_number(key) - 1)
                    names = list(block.get("call_kwarg_names", []))
                    name = safe_name(names[index] if index < len(names) else "") or f"kwarg_{index + 1}"
                    arguments.append(f"{name}={self._input_expr(uid, key, 'None')}")
            else:
                if self.incoming.get((uid, port_id)):
                    value = self._input_expr(uid, port_id, "None")
                    if port.get("call_mode") == "kwonly":
                        arguments.append(f"{safe_name(port.get('name', ''))}={value}")
                    else:
                        arguments.append(value)
                elif not port.get("required", True):
                    continue
                else:
                    arguments.append("None")
        name = safe_name(function.get("name", "")) or "fonction"
        return f"{name}({', '.join(arguments)})"

    def _connected_input_keys(self, uid: str, prefix: str) -> list[str]:
        keys = [port for target, port in self.incoming if target == uid and str(port).startswith(prefix)]
        return sorted(keys, key=_suffix_number)


def _suffix_number(value: str) -> int:
    try:
        return int(str(value).rsplit("_", 1)[1])
    except (ValueError, IndexError):
        return 0
