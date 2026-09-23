from boa.core.module_specs import ModuleBlockSpec
from boa.modules.spec_tools import B, C, I, INFO, P, PATH, S, T, V


SPECS: dict[str, ModuleBlockSpec] = {}


def _add(*specs: ModuleBlockSpec) -> None:
    SPECS.update((spec.key, spec) for spec in specs)


# Types and conversions ------------------------------------------------------
TYPE_CHOICES = ("int", "float", "str", "bool", "list", "tuple", "set", "dict", "bytes")
_add(
    S("type_convert", "Convertir une valeur", "Convertit une valeur vers le type choisi.", "types",
      (P("value", "valeur"),), fields=(C("mode", *TYPE_CHOICES),),
      variants={item: V((P("value", "valeur"),), (P("result", "résultat", item),)) for item in TYPE_CHOICES}, imports=("ast",)),
    S("type_test", "Tester le type", "Vérifie si une valeur possède le type choisi.", "types",
      (P("value", "valeur"),), fields=(C("mode", *TYPE_CHOICES),),
      variants={item: V((P("value", "valeur"),), (P("result", "résultat", "bool"),)) for item in TYPE_CHOICES}),
    S("type_convertible", "Tester une conversion", "Vérifie si une valeur peut être convertie sans interrompre le programme.", "types",
      (P("value", "valeur"),), fields=(C("mode", *TYPE_CHOICES),),
      variants={item: V((P("value", "valeur"),), (P("result", "possible", "bool"),)) for item in TYPE_CHOICES}, imports=("ast",)),
    S("type_name", "Obtenir le type", "Renvoie le nom du type d’une valeur.", "types", (P("value", "valeur"),), (P("result", "type", "str"),)),
    S("value_length", "Obtenir la longueur", "Renvoie le nombre d’éléments ou de caractères d’une valeur.", "types", (P("value", "valeur"),), (P("result", "longueur", "int"),)),
    S("none_fallback", "Valeur si aucune", "Utilise une valeur de remplacement lorsque la première vaut AUCUNE VALEUR.", "types",
      (P("value", "valeur"), P("fallback", "remplacement")), (P("result", "résultat"),)),
)



