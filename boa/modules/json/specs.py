from boa.core.module_specs import ModuleBlockSpec
from boa.modules.spec_tools import B, C, I, INFO, P, PATH, S, T, V

RELATIVE = B("relative_to_project", False, "info.path.relative")


SPECS: dict[str, ModuleBlockSpec] = {}


def _add(*specs: ModuleBlockSpec) -> None:
    SPECS.update((spec.key, spec) for spec in specs)


# JSON -----------------------------------------------------------------------
JSON_FIELDS = (I("indent", 2), B("sort_keys"), B("ensure_ascii"))
_add(
    S("json_convert", "Convertir JSON", "Convertit un texte JSON en données ou des données en texte JSON.", "json",
      fields=(C("mode", "text_to_data", "data_to_text"), *JSON_FIELDS),
      variants={
          "text_to_data": V((P("value", "texte JSON", "str"),), (P("result", "données"),)),
          "data_to_text": V((P("value", "données"),), (P("result", "texte JSON", "str"),)),
      }, imports=("json",)),
    S("json_read", "Lire un fichier JSON", "Charge les données d’un fichier JSON.", "json",
      (P("path", "fichier", "str"),), (P("data", "données"),),
      fields=(PATH("file_path"), RELATIVE, C("encoding", "utf8", "utf8_bom", "ascii", "latin1", "cp1252")), flow=True, imports=("json", "pathlib")),
    S("json_write", "Écrire un fichier JSON", "Enregistre des données dans un fichier JSON.", "json",
      (P("path", "fichier", "str"), P("data", "données")), (P("result", "fichier", "str"),),
      fields=(PATH("file_path"), RELATIVE, C("encoding", "utf8", "utf8_bom", "ascii", "latin1", "cp1252"), *JSON_FIELDS, B("create_parents", True)), flow=True, imports=("json", "pathlib")),
    S("json_value", "Accéder ou modifier une valeur JSON", "Lit, remplace ou supprime une valeur à partir de sa clé.", "json",
      fields=(C("mode", "get", "set", "delete"),),
      variants={
          "get": V((P("data", "données"), P("key", "clé")), (P("result", "valeur"),)),
          "set": V((P("data", "données"), P("key", "clé"), P("value", "valeur")), (P("result", "données"),)),
          "delete": V((P("data", "données"), P("key", "clé")), (P("result", "données"),)),
      }, imports=("json",)),
)


