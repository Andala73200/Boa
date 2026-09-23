from boa.core.module_specs import ModuleBlockSpec
from boa.modules.spec_tools import B, C, I, INFO, P, PATH, S, T, V


SPECS: dict[str, ModuleBlockSpec] = {}


def _add(*specs: ModuleBlockSpec) -> None:
    SPECS.update((spec.key, spec) for spec in specs)


# Random ---------------------------------------------------------------------
_add(
    S(
        "random_number", "Nombre aléatoire", "Génère un nombre entier ou décimal entre deux limites.", "random",
        fields=(C("mode", "integer", "decimal"),),
        variants={
            "integer": V((P("minimum", "minimum", "int"), P("maximum", "maximum", "int")), (P("result", "résultat", "int"),)),
            "decimal": V((P("minimum", "minimum", "float"), P("maximum", "maximum", "float")), (P("result", "résultat", "float"),)),
        },
    ),
    S(
        "random_collection", "Collection aléatoire", "Choisit, mélange ou tire des éléments d’une collection.", "random",
        fields=(
            C("mode", "choose_item", "shuffle", "sample"),
            B("with_replacement", False, "info.random.replacement", (("mode", "sample"),)),
        ),
        variants={
            "choose_item": V((P("collection", "collection"),), (P("result", "élément"),)),
            "shuffle": V((P("collection", "liste", "list"),), (P("result", "liste", "list"),)),
            "sample": V((P("collection", "collection"), P("count", "nombre", "int")), (P("result", "liste", "list"),)),
        },
    ),
)



