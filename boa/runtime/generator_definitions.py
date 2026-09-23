from __future__ import annotations

from boa.functions.models import INPUT_KEYS, OUTPUT_KEYS, function_parameters
from boa.runtime.codegen_utils import literal, only_imports, safe_name
from boa.runtime.module_codegen import is_flow_module_block
from boa.runtime.python_codegen import function_header


class DefinitionMixin:
    def _top_level_definitions(self) -> None:
        if self.function_definition or self.class_definition:
            return
        function_markers = {
            str(block.get("definition_id", ""))
            for block in self.graph.get("blocks", [])
            if block.get("key") == "def_marker"
        }
        class_markers = {
            str(block.get("definition_id", ""))
            for block in self.graph.get("blocks", [])
            if block.get("key") == "class_marker"
        }
        functions = [
            item
            for item in self.functions.values()
            if not item.get("owner_function_id")
            and not item.get("owner_class_id")
            and (not item.get("python_inline") or str(item.get("id", "")) not in function_markers)
        ]
        classes = [
            item
            for item in self.classes.values()
            if not item.get("owner_class_id")
            and (not item.get("python_inline") or str(item.get("id", "")) not in class_markers)
        ]
        ordered = [
            *(('function', item) for item in functions),
            *(('class', item) for item in classes),
        ]
        ordered.sort(key=lambda pair: (int(pair[1].get("python_lineno", 10**9)), str(pair[1].get("name", ""))))
        for kind, item in ordered:
            if kind == "function":
                self._emit_function_definition(item)
            else:
                self._emit_class_definition(item)

    def _emit_function_definition(
        self,
        function: dict,
        indent: int = 0,
        decorators: list[str] | None = None,
    ) -> None:
        name = safe_name(function.get("name", ""))
        if not name:
            return
        start = next(
            (block for block in function.get("graph", {}).get("blocks", []) if block.get("key") == "function_start"),
            {},
        )
        comment = str(function.get("comment") or start.get("comment", "")).strip()
        for line in comment.splitlines():
            self._line(f"# {line}", indent)

        legacy_decorators, legacy_header = function_header(function, name)
        for decorator in decorators if decorators is not None else legacy_decorators:
            text = str(decorator).strip()
            if text:
                self._line(text if text.startswith("@") else f"@{text}", indent)

        header = legacy_header or self._function_signature(function, name)
        self._line(header, indent)
        body_indent = indent + 1
        body_written = False

        docstring = str(function.get("docstring", "") or "")
        if docstring:
            self._line(repr(docstring), body_indent)
            body_written = True
        for statement in self._scope_imports(function, function.get("graph", {}) or {}):
            self._line(statement, body_indent)
            body_written = True

        for block in function.get("graph", {}).get("blocks", []):
            if block.get("key") not in INPUT_KEYS | OUTPUT_KEYS:
                continue
            comments = str(block.get("comment", "") or "").strip().splitlines()
            port_name = safe_name(block.get("def_port_name", ""))
            if comments and port_name:
                self._line(f"# {port_name} : {comments[0]}", body_indent)
                for line in comments[1:]:
                    self._line(f"# {line}", body_indent)
                body_written = True

        child = self.__class__(
            function.get("graph", {}),
            self.context,
            self.functions,
            self.classes,
            function_definition=function,
        )
        fragment = [line for line in child.fragment() if line.strip()]
        for line in fragment:
            self._line(line, body_indent)
            body_written = True
        if not body_written:
            self._line("pass", body_indent)
        self._line("")

    def _function_signature(self, function: dict, name: str) -> str:
        def format_port(port: dict, prefix: str = "") -> str:
            parameter = safe_name(port.get("name", ""))
            if not parameter:
                return ""
            value_type = str(port.get("type", "any"))
            exact_annotation = str(port.get("annotation", "") or "").strip()
            annotation_name = exact_annotation or (value_type if value_type and value_type != "any" else "")
            annotation = f": {annotation_name}" if annotation_name else ""
            item = f"{prefix}{parameter}{annotation}"
            if not prefix and not port.get("required", True):
                default = str(port.get("default", "") or "None")
                item += f"={default}"
            return item

        ports = function_parameters(function)
        posonly = [port for port in ports if port.get("kind") == "normal" and port.get("call_mode") == "posonly"]
        normal = [port for port in ports if port.get("kind") == "normal" and port.get("call_mode") == "normal"]
        kwonly = [port for port in ports if port.get("kind") == "normal" and port.get("call_mode") == "kwonly"]
        args_port = next((port for port in ports if port.get("kind") == "args"), None)
        kwargs_port = next((port for port in ports if port.get("kind") == "kwargs"), None)
        signature = [item for item in (format_port(port) for port in posonly) if item]
        if posonly:
            signature.append("/")
        signature.extend(item for item in (format_port(port) for port in normal) if item)
        if args_port:
            signature.append(format_port(args_port, "*"))
        elif kwonly:
            signature.append("*")
        signature.extend(item for item in (format_port(port) for port in kwonly) if item)
        if kwargs_port:
            signature.append(format_port(kwargs_port, "**"))
        prefix = "async " if function.get("is_async") else ""
        return_annotation = str(function.get("return_annotation", "") or "").strip()
        suffix = f" -> {return_annotation}" if return_annotation else ""
        return f"{prefix}def {name}({', '.join(signature)}){suffix}:"

    def _emit_class_definition(
        self,
        class_def: dict,
        indent: int = 0,
        decorators: list[str] | None = None,
    ) -> None:
        name = safe_name(class_def.get("name", ""))
        if not name:
            return
        for decorator in decorators or []:
            text = str(decorator).strip()
            if text:
                self._line(text if text.startswith("@") else f"@{text}", indent)
        bases = [str(item).strip() for item in class_def.get("bases", []) if str(item).strip()]
        keywords = [str(item).strip() for item in class_def.get("keywords", []) if str(item).strip()]
        suffix = f"({', '.join([*bases, *keywords])})" if bases or keywords else ""
        self._line(f"class {name}{suffix}:", indent)
        body_indent = indent + 1
        body_written = False

        docstring = str(class_def.get("docstring", "") or "")
        if docstring:
            self._line(repr(docstring), body_indent)
            body_written = True
        for statement in self._scope_imports(class_def, class_def.get("graph", {}) or {}):
            self._line(statement, body_indent)
            body_written = True

        graph = class_def.get("graph", {}) or {}
        blocks = sorted(
            (block for block in graph.get("blocks", []) if block.get("key") != "decorator"),
            key=lambda block: (int(block.get("class_order", 10**6)), float(block.get("x", 0))),
        )
        class_child = self.__class__(
            graph,
            self.context,
            self.functions,
            self.classes,
            class_definition=class_def,
        )
        for block in blocks:
            if class_child._emit_class_member(block, body_indent):
                body_written = True
        if class_child.lines:
            self.lines.extend(class_child.lines)
        if not body_written:
            self._line("pass", body_indent)
        self._line("")

    def _emit_class_member(self, block: dict, indent: int) -> bool:
        key = str(block.get("key", ""))
        if key == "assign":
            self._emit_assign(block, indent)
            return True
        if key == "class_attribute":
            self._emit_class_attribute(block, indent)
            return True
        if key == "def_marker":
            function = self.functions.get(str(block.get("definition_id", "")))
            if function:
                self._emit_function_definition(function, indent, self._decorators_for(block.get("id", "")))
                return True
        if key == "class_marker":
            class_def = self.classes.get(str(block.get("definition_id", "")))
            if class_def:
                self._emit_class_definition(class_def, indent, self._decorators_for(block.get("id", "")))
                return True
        if key == "python_node":
            self._emit_python_node(block, indent)
            return True
        if key == "empty":
            raw = str(block.get("raw_code", "") or "")
            if raw and not only_imports(raw):
                for line in raw.splitlines():
                    self._line(line, indent)
                return True
        return False

    def _variables(self) -> None:
        if self.function_definition or self.class_definition:
            return
        assigned = self._assigned_variable_names()
        for item in self.context.get("variables", []):
            name = safe_name(item.get("name", ""))
            if not name or name in assigned:
                continue
            self._line(f"{name} = {literal(item.get('initial', ''), item.get('type', 'any'))}")
        done: set[str] = set()
        for block in self.blocks.values():
            if block.get("key") != "variable" or not self.incoming.get((block.get("id", ""), "in")):
                continue
            name = safe_name(block.get("variable_name", block.get("subtitle", "")))
            source_key = self._input_source_key(block.get("id", ""), "in")
            if not name or name in done or source_key in {"input", "call"} or is_flow_module_block(source_key):
                continue
            expression = self._input_expr(block.get("id", ""), "in")
            if expression and not self._expr_waits_for_runtime(expression):
                self._emit_input_comments(block.get("id", ""), "in", 0)
                self._line(f"{name} = {expression}")
                done.add(name)
        if self.lines and self.lines[-1] != "":
            self._line("")
