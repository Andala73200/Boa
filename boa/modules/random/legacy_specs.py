from boa.core.module_specs import ModuleBlockSpec, ModulePortSpec


def _port(key: str, label: str, value_type: str) -> ModulePortSpec:
    return ModulePortSpec(key, label, value_type)


def _random(
    name: str,
    title: str,
    description: str,
    inputs: tuple[ModulePortSpec, ...],
    output: ModulePortSpec,
    expression: str,
) -> ModuleBlockSpec:
    return ModuleBlockSpec(
        f"random_{name}", title, description, inputs, (output,),
        {output.key: expression}, "random", hidden=True, imports=("random",),
    )


RANDOM_SPECS: dict[str, ModuleBlockSpec] = {spec.key: spec for spec in [
    _random(
        "uniform", "Nombre décimal aléatoire", "Nombre décimal compris entre deux limites.",
        (_port("minimum", "minimum", "float"), _port("maximum", "maximum", "float")),
        _port("result", "résultat", "float"), "random.uniform({minimum}, {maximum})",
    ),
    _random(
        "randint", "Entier aléatoire", "Nombre entier compris entre deux limites incluses.",
        (_port("minimum", "minimum", "int"), _port("maximum", "maximum", "int")),
        _port("result", "résultat", "int"), "random.randint({minimum}, {maximum})",
    ),
    _random(
        "choice", "Choisir un élément", "Choisit au hasard un élément d'une collection.",
        (_port("values", "collection", "any"),),
        _port("element", "élément", "any"), "random.choice({values})",
    ),
    _random(
        "shuffle", "Mélanger une liste", "Crée une nouvelle liste mélangée sans modifier l'originale.",
        (_port("values", "liste", "any"),),
        _port("result", "liste", "list"), "random.sample({values}, k=len({values}))",
    ),
    _random(
        "sample", "Tirer plusieurs éléments", "Tire plusieurs éléments différents d'une collection.",
        (_port("values", "collection", "any"), _port("count", "nombre", "int")),
        _port("result", "liste", "list"), "random.sample({values}, k={count})",
    ),
]}

RANDOM_BLOCK_KEYS = set(RANDOM_SPECS)


LEGACY_SPECS = RANDOM_SPECS
