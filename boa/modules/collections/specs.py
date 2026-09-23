from boa.core.module_specs import ModuleBlockSpec
from boa.modules.spec_tools import B, C, I, INFO, P, PATH, S, T, V


SPECS: dict[str, ModuleBlockSpec] = {}


def _add(*specs: ModuleBlockSpec) -> None:
    SPECS.update((spec.key, spec) for spec in specs)


DICT_VALUE_PORTS = tuple(P(f"value_{index}", f"valeur {index}") for index in range(1, 17))


# Collections ----------------------------------------------------------------
_add(
    S("collection_append", "Ajouter à une liste", "Ajoute une valeur à une liste existante.", "collections",
      (P("collection", "liste", "list"), P("value", "valeur")), (P("result", "résultat"),), flow=True),
    S("collection_get", "Lire une clé", "Lit une clé de dictionnaire avec une valeur par défaut facultative.", "collections",
      fields=(C("mode", "without_default", "with_default"),),
      variants={
          "without_default": V((P("collection", "dictionnaire", "dict"), P("key", "clé")), (P("result", "valeur"),)),
          "with_default": V((P("collection", "dictionnaire", "dict"), P("key", "clé"), P("default", "défaut")), (P("result", "valeur"),)),
      }),
    S("collection_enumerate", "Énumérer", "Associe chaque élément à son index.", "collections",
      fields=(C("mode", "without_start", "with_start"),),
      variants={
          "without_start": V((P("collection", "collection"),), (P("result", "énumération"),)),
          "with_start": V((P("collection", "collection"), P("start_index", "début", "int")), (P("result", "énumération"),)),
      }),
    S("collection_zip", "Associer (ZIP)", "Associe les éléments de deux collections.", "collections",
      (P("first", "collection A"), P("second", "collection B")), (P("result", "association"),)),
    S("collection_dict", "Créer un dictionnaire", "Crée un dictionnaire à partir d’arguments nommés.", "collections",
      DICT_VALUE_PORTS, (P("result", "dictionnaire", "dict"),), selectable_inputs=True),
    S("collection_create", "Créer une collection", "Crée une liste, un tuple, un ensemble ou un dictionnaire.", "collections",
      (P("values", "valeurs"),), fields=(C("mode", "list", "tuple", "set", "dict"),),
      variants={item: V((P("values", "valeurs"),), (P("result", "collection", item),)) for item in ("list", "tuple", "set", "dict")}),
    S("collection_access", "Accéder à une collection", "Récupère un élément, une clé ou une portion de collection.", "collections",
      fields=(C("mode", "index", "key", "slice"),),
      variants={
          "index": V((P("collection", "collection"), P("index", "index", "int")), (P("result", "élément"),)),
          "key": V((P("collection", "dictionnaire", "dict"), P("key", "clé")), (P("result", "valeur"),)),
          "slice": V((P("collection", "collection"), P("start_index", "début", "int"), P("end_index", "fin", "int"), P("step", "pas", "int")), (P("result", "portion"),)),
      }),
    S("collection_modify", "Modifier une collection", "Ajoute, insère, remplace ou retire un élément sans modifier l’original.", "collections",
      fields=(C("mode", "add", "insert", "replace", "remove"),),
      variants={
          "add": V((P("collection", "collection"), P("value", "valeur")), (P("result", "collection"),)),
          "insert": V((P("collection", "liste", "list"), P("index", "index", "int"), P("value", "valeur")), (P("result", "liste", "list"),)),
          "replace": V((P("collection", "collection"), P("index", "index / clé"), P("value", "valeur")), (P("result", "collection"),)),
          "remove": V((P("collection", "collection"), P("value", "valeur")), (P("result", "collection"),)),
      }),
    S("collection_sort", "Trier une collection", "Crée une liste triée à partir d’une collection.", "collections",
      (P("collection", "collection"),), (P("result", "liste triée", "list"),), fields=(B("reverse"),)),
    S("collection_search", "Rechercher dans une collection", "Teste, localise ou compte une valeur dans une collection.", "collections",
      fields=(C("mode", "contains", "index", "count"),),
      variants={
          "contains": V((P("collection", "collection"), P("value", "valeur")), (P("result", "présent", "bool"),)),
          "index": V((P("collection", "collection"), P("value", "valeur")), (P("result", "index", "int"),)),
          "count": V((P("collection", "collection"), P("value", "valeur")), (P("result", "nombre", "int"),)),
      }),
    S("collection_combine", "Combiner des collections", "Concatène, associe ou compare deux collections.", "collections",
      (P("first", "collection A"), P("second", "collection B")), fields=(C("mode", "concatenate", "zip", "merge", "union", "intersection", "difference"),),
      variants={
          "concatenate": V((P("first", "collection A"), P("second", "collection B")), (P("result", "collection"),)),
          "zip": V((P("first", "collection A"), P("second", "collection B")), (P("result", "paires", "list"),)),
          "merge": V((P("first", "dictionnaire A", "dict"), P("second", "dictionnaire B", "dict")), (P("result", "dictionnaire", "dict"),)),
          "union": V((P("first", "ensemble A"), P("second", "ensemble B")), (P("result", "union", "set"),)),
          "intersection": V((P("first", "ensemble A"), P("second", "ensemble B")), (P("result", "intersection", "set"),)),
          "difference": V((P("first", "ensemble A"), P("second", "ensemble B")), (P("result", "différence", "set"),)),
      }),
)



