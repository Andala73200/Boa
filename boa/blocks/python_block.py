from __future__ import annotations

from PySide6.QtGui import QColor

from boa.blocks.base_block import BlockItem, PortDefinition


PYTHON_COLORS = {
    "import": QColor("#5e35b1"),
    "assignment": QColor("#1565c0"),
    "call": QColor("#00897b"),
    "return": QColor("#6a1b9a"),
    "condition": QColor("#c62828"),
    "loop": QColor("#2e7d32"),
    "exception": QColor("#ad6f00"),
    "context": QColor("#00695c"),
    "class": QColor("#455a64"),
    "statement": QColor("#37474f"),
}


def python_ports(inputs: list[str], outputs: list[str], flow: bool = True) -> list[PortDefinition]:
    ports: list[PortDefinition] = []
    input_y = 54 if flow else 30
    output_y = 54 if flow else 30
    if flow:
        ports.extend([
            PortDefinition("start", "start", "input", "flow", "left", 24),
            PortDefinition("done", "done", "output", "flow", "right", 24),
        ])
    for index, name in enumerate(inputs):
        ports.append(PortDefinition(f"input_{index}", name, "input", "any", "left", input_y + index * 24))
    for index, name in enumerate(outputs):
        ports.append(PortDefinition(f"output_{index}", name, "output", "any", "right", output_y + index * 24))
    return ports


def create_python_block(
    kind: str = "statement",
    title: str = "Instruction Python",
    source: str = "pass",
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    sections: list[dict] | None = None,
    flow: bool = True,
) -> BlockItem:
    input_names = list(inputs or [])
    output_names = list(outputs or [])
    rows = max(len(input_names), len(output_names), 1)
    height = max(70, (54 if flow else 32) + rows * 24)
    subtitle = _compact_source(source)
    block = BlockItem(
        title,
        subtitle,
        PYTHON_COLORS.get(kind, PYTHON_COLORS["statement"]),
        python_ports(input_names, output_names, flow),
        240,
        height,
    )
    block.block_key = "python_node"
    block.python_kind = kind
    block.python_title = title
    block.python_source = source
    block.python_inputs = input_names
    block.python_outputs = output_names
    block.python_sections = list(sections or [])
    block.python_flow = bool(flow)
    block.python_import_only = kind == "import"
    block.python_function_id = ""
    block.python_import_header = False
    block.python_expression = not flow and kind == "expression"
    return block


def python_block_from_data(data: dict) -> BlockItem:
    block = create_python_block(
        str(data.get("python_kind", "statement")),
        str(data.get("python_title", data.get("title", "Instruction Python"))),
        str(data.get("python_source", "pass")),
        list(data.get("python_inputs", [])),
        list(data.get("python_outputs", [])),
        list(data.get("python_sections", [])),
        bool(data.get("python_flow", True)),
    )
    block.python_function_id = str(data.get("python_function_id", ""))
    block.python_import_header = bool(data.get("python_import_header", False))
    block.python_expression = bool(data.get("python_expression", block.python_expression))
    return block


def python_block_to_data(block: BlockItem) -> dict:
    return {
        "python_kind": str(getattr(block, "python_kind", "statement")),
        "python_title": str(getattr(block, "python_title", block.title)),
        "python_source": str(getattr(block, "python_source", "pass")),
        "python_inputs": list(getattr(block, "python_inputs", [])),
        "python_outputs": list(getattr(block, "python_outputs", [])),
        "python_sections": list(getattr(block, "python_sections", [])),
        "python_flow": bool(getattr(block, "python_flow", True)),
        "python_function_id": str(getattr(block, "python_function_id", "")),
        "python_import_header": bool(getattr(block, "python_import_header", False)),
        "python_expression": bool(getattr(block, "python_expression", False)),
    }


def _compact_source(source: str) -> str:
    text = " ".join(str(source).strip().split())
    return text if len(text) <= 70 else text[:67] + "..."


def apply_python_block_data(block: BlockItem, data: dict) -> None:
    replacement = python_block_from_data(data)
    function_id = str(data.get("python_function_id", getattr(block, "python_function_id", "")))
    import_header = bool(data.get("python_import_header", getattr(block, "python_import_header", False)))
    expression = bool(data.get("python_expression", getattr(block, "python_expression", False)))
    block.prepareGeometryChange()
    block.title = replacement.title
    block.subtitle = replacement.subtitle
    block.color = replacement.color
    block.ports = replacement.ports
    block.WIDTH = replacement.WIDTH
    block.HEIGHT = replacement.HEIGHT
    block.python_kind = replacement.python_kind
    block.python_title = replacement.python_title
    block.python_source = replacement.python_source
    block.python_inputs = replacement.python_inputs
    block.python_outputs = replacement.python_outputs
    block.python_sections = replacement.python_sections
    block.python_flow = replacement.python_flow
    block.python_import_only = replacement.python_import_only
    block.python_function_id = function_id
    block.python_import_header = import_header
    block.python_expression = expression
    block.refresh_tooltip()
    block.update()
    block._update_connections()
