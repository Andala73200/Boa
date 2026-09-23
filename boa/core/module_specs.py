from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ModulePortSpec:
    key: str
    label: str
    value_type: str


@dataclass(frozen=True, slots=True)
class ModuleChoiceSpec:
    key: str
    label_key: str


@dataclass(frozen=True, slots=True)
class ModuleFieldSpec:
    key: str
    label_key: str
    kind: str = "choice"
    choices: tuple[ModuleChoiceSpec, ...] = ()
    default: object = ""
    info_key: str = ""
    show_if: tuple[tuple[str, object], ...] = ()
    path_kind: str = "file"
    minimum: int = 0
    maximum: int = 1_000_000_000


@dataclass(frozen=True, slots=True)
class ModuleVariantSpec:
    inputs: tuple[ModulePortSpec, ...] = ()
    outputs: tuple[ModulePortSpec, ...] = ()
    expressions: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModuleBlockSpec:
    key: str
    title: str
    description: str
    inputs: tuple[ModulePortSpec, ...]
    outputs: tuple[ModulePortSpec, ...]
    expressions: dict[str, str]
    module: str = ""
    fields: tuple[ModuleFieldSpec, ...] = ()
    variants: dict[str, ModuleVariantSpec] = field(default_factory=dict)
    variant_field: str = "mode"
    flow: bool = False
    hidden: bool = False
    imports: tuple[str, ...] = ()
    selectable_inputs: bool = False


FLOW_INPUT = ModulePortSpec("start", "start", "flow")
FLOW_OUTPUT = ModulePortSpec("done", "done", "flow")


def unfiltered_module_ports(spec: ModuleBlockSpec, config: dict | None = None) -> tuple[tuple[ModulePortSpec, ...], tuple[ModulePortSpec, ...]]:
    values = config or {}
    selected = str(values.get(spec.variant_field, ""))
    variant = spec.variants.get(selected)
    inputs = variant.inputs if variant else spec.inputs
    outputs = variant.outputs if variant else spec.outputs
    if spec.flow:
        inputs = (FLOW_INPUT, *inputs)
        outputs = (FLOW_OUTPUT, *outputs)
    return tuple(inputs), tuple(outputs)


def resolved_module_ports(spec: ModuleBlockSpec, config: dict | None = None) -> tuple[tuple[ModulePortSpec, ...], tuple[ModulePortSpec, ...]]:
    values = config or {}
    inputs, outputs = unfiltered_module_ports(spec, values)
    enabled_inputs = values.get("_enabled_inputs")
    if spec.selectable_inputs and isinstance(enabled_inputs, (list, tuple, set)):
        selected_inputs = {str(key) for key in enabled_inputs}
        inputs = tuple(port for port in inputs if port.value_type == "flow" or port.key in selected_inputs)
    value_outputs = tuple(port for port in outputs if port.value_type != "flow")
    enabled_outputs = values.get("_enabled_outputs")
    if len(value_outputs) > 1 and isinstance(enabled_outputs, (list, tuple, set)):
        selected_outputs = {str(key) for key in enabled_outputs}
        outputs = tuple(port for port in outputs if port.value_type == "flow" or port.key in selected_outputs)
    return inputs, outputs


def module_has_selectable_outputs(spec: ModuleBlockSpec) -> bool:
    candidates = [spec.outputs, *(variant.outputs for variant in spec.variants.values())]
    return any(sum(port.value_type != "flow" for port in outputs) > 1 for outputs in candidates)


def possible_module_ports(spec: ModuleBlockSpec) -> tuple[tuple[ModulePortSpec, ...], tuple[ModulePortSpec, ...]]:
    inputs: dict[str, ModulePortSpec] = {port.key: port for port in spec.inputs if port.value_type != "flow"}
    outputs: dict[str, ModulePortSpec] = {port.key: port for port in spec.outputs if port.value_type != "flow"}
    for variant in spec.variants.values():
        inputs.update((port.key, port) for port in variant.inputs if port.value_type != "flow")
        outputs.update((port.key, port) for port in variant.outputs if port.value_type != "flow")
    return tuple(inputs.values()), tuple(outputs.values())


def resolved_module_expressions(spec: ModuleBlockSpec, config: dict | None = None) -> dict[str, str]:
    selected = str((config or {}).get(spec.variant_field, ""))
    variant = spec.variants.get(selected)
    return variant.expressions if variant and variant.expressions else spec.expressions
