from boa.core.module_specs import (
    ModuleBlockSpec,
    ModuleChoiceSpec,
    ModuleFieldSpec,
    ModulePortSpec,
    ModuleVariantSpec,
)


def P(key: str, label: str, value_type: str = "any") -> ModulePortSpec:
    return ModulePortSpec(key, label, value_type)


def V(inputs=(), outputs=()) -> ModuleVariantSpec:
    return ModuleVariantSpec(tuple(inputs), tuple(outputs), {})


def C(key: str, *choices: str, default: str = "", info: str = "", show_if=()) -> ModuleFieldSpec:
    return ModuleFieldSpec(
        key, f"field.{key}", "choice",
        tuple(ModuleChoiceSpec(item, f"option.{item}") for item in choices),
        default, info, tuple(show_if),
    )


def B(key: str, default: bool = False, info: str = "", show_if=()) -> ModuleFieldSpec:
    return ModuleFieldSpec(key, f"field.{key}", "bool", (), default, info, tuple(show_if))


def T(key: str, default: str = "", info: str = "", show_if=()) -> ModuleFieldSpec:
    return ModuleFieldSpec(key, f"field.{key}", "text", (), default, info, tuple(show_if))


def I(
    key: str,
    default: int = 0,
    info: str = "",
    show_if=(),
    minimum: int = 0,
    maximum: int = 1_000_000_000,
) -> ModuleFieldSpec:
    return ModuleFieldSpec(
        key, f"field.{key}", "int", (), default, info, tuple(show_if),
        minimum=minimum, maximum=maximum,
    )


def PATH(key: str, kind: str = "file", info: str = "", show_if=()) -> ModuleFieldSpec:
    return ModuleFieldSpec(key, f"field.{key}", "path", (), "", info, tuple(show_if), kind)


def INFO(key: str, info: str) -> ModuleFieldSpec:
    return ModuleFieldSpec(key, f"field.{key}", "info", (), "", info)


def S(
    key: str,
    title: str,
    description: str,
    module: str,
    inputs=(),
    outputs=(),
    *,
    fields=(),
    variants=None,
    variant_field: str = "mode",
    flow: bool = False,
    imports=(),
    selectable_inputs: bool = False,
) -> ModuleBlockSpec:
    return ModuleBlockSpec(
        key, title, description, tuple(inputs), tuple(outputs), {}, module,
        tuple(fields), variants or {}, variant_field, flow, False,
        tuple(imports), selectable_inputs,
    )


def collect(*specs: ModuleBlockSpec) -> dict[str, ModuleBlockSpec]:
    return {spec.key: spec for spec in specs}
