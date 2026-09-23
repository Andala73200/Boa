from __future__ import annotations

from boa.runtime.generator_calls import CallMixin
from boa.runtime.generator_control import ControlFlowMixin
from boa.runtime.generator_definitions import DefinitionMixin
from boa.runtime.generator_dispatch import DispatchMixin
from boa.runtime.generator_expressions import ExpressionMixin
from boa.runtime.generator_imports import ImportMixin
from boa.runtime.generator_python_native import PythonNativeMixin


def generate_python(project: dict) -> str:
    generator = _Generator(
        project.get("graph", {}) or {},
        project.get("context", {}) or {},
        project.get("functions", {}) or {},
        project.get("classes", {}) or {},
    )
    return generator.generate()

class _Generator(
    PythonNativeMixin,
    DefinitionMixin,
    CallMixin,
    DispatchMixin,
    ControlFlowMixin,
    ExpressionMixin,
    ImportMixin,
):
    def __init__(
        self,
        graph: dict,
        context: dict,
        functions: dict | None = None,
        classes: dict | None = None,
        function_definition: dict | None = None,
        class_definition: dict | None = None,
    ) -> None:
        self.graph = graph or {}
        self.context = context or {}
        self.functions = functions or {}
        self.classes = classes or {}
        self.function_definition = function_definition
        self.class_definition = class_definition
        self.lines: list[str] = []
        self._runtime_available: set[str] = set()
        self._runtime_emitted: set[str] = set()
        self._build(self.graph)

    def _build(self, graph: dict) -> None:
        self.blocks = {block.get("id", ""): block for block in graph.get("blocks", []) if block.get("id")}
        self.incoming: dict[tuple[str, str], list[dict]] = {}
        self.outgoing: dict[tuple[str, str], list[dict]] = {}
        for connection in graph.get("connections", []):
            self.incoming.setdefault(
                (connection.get("target", ""), connection.get("target_port", "")), []
            ).append(connection)
            self.outgoing.setdefault(
                (connection.get("source", ""), connection.get("source_port", "")), []
            ).append(connection)

    def generate(self) -> str:
        self._header()
        self._top_level_definitions()
        self._variables()
        self._emit_roots(0)
        if not self.lines or all(line.startswith(("#", "import", "from")) for line in self.lines):
            self._line("pass")
        return "\n".join(self.lines).rstrip() + "\n"

    def fragment(self) -> list[str]:
        self._emit_roots(0, add_empty_message=False)
        return list(self.lines)

    def _emit_roots(self, indent: int, add_empty_message: bool = True) -> None:
        roots = self._roots()
        if not roots and add_empty_message:
            self._line("# Aucun point de départ détecté.", indent)
        emitted: set[str] = set()
        for root in roots:
            self._emit_block(root, indent, emitted)
