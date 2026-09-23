from boa.core.module_specs import ModuleBlockSpec
from boa.modules.spec_tools import B, C, I, INFO, P, PATH, S, T, V


SPECS: dict[str, ModuleBlockSpec] = {}


def _add(*specs: ModuleBlockSpec) -> None:
    SPECS.update((spec.key, spec) for spec in specs)


# Text and regular expressions ----------------------------------------------
_add(
    S("text_transform", "Transformer un texte", "Change la casse ou nettoie un texte.", "text",
      (P("text", "texte", "str"),), (P("result", "texte", "str"),), fields=(C("mode", "lower", "upper", "title", "capitalize", "strip", "normalize_spaces"),)),
    S("text_split_join", "Découper ou joindre un texte", "Découpe un texte en liste ou joint une collection en texte.", "text",
      fields=(C("mode", "split", "join"),),
      variants={
          "split": V((P("value", "texte", "str"), P("separator_value", "séparateur", "str")), (P("result", "liste", "list"),)),
          "join": V((P("value", "collection"), P("separator_value", "séparateur", "str")), (P("result", "texte", "str"),)),
      }),
    S("text_replace", "Remplacer dans un texte", "Remplace une partie de texte par une autre.", "text",
      (P("text", "texte", "str"), P("old", "à remplacer", "str"), P("new", "remplacement", "str"), P("count", "maximum", "int")), (P("result", "texte", "str"),)),
    S("text_search", "Rechercher dans un texte", "Teste, localise ou compte un fragment de texte.", "text",
      fields=(C("mode", "contains", "find", "count", "starts_with", "ends_with"), B("case_sensitive", True)),
      variants={
          "contains": V((P("text", "texte", "str"), P("query", "recherche", "str")), (P("result", "présent", "bool"),)),
          "find": V((P("text", "texte", "str"), P("query", "recherche", "str")), (P("result", "position", "int"),)),
          "count": V((P("text", "texte", "str"), P("query", "recherche", "str")), (P("result", "nombre", "int"),)),
          "starts_with": V((P("text", "texte", "str"), P("query", "recherche", "str")), (P("result", "résultat", "bool"),)),
          "ends_with": V((P("text", "texte", "str"), P("query", "recherche", "str")), (P("result", "résultat", "bool"),)),
      }),
    S("regex_operation", "Expression régulière", "Recherche, valide ou remplace avec une expression régulière.", "text",
      fields=(C("mode", "full_match", "search", "find_all", "replace"), B("ignore_case"), B("multiline"), INFO("pattern_help", "info.regex.pattern")),
      variants={
          "full_match": V((P("text", "texte", "str"), P("pattern", "motif", "str")), (P("result", "correspond", "bool"),)),
          "search": V((P("text", "texte", "str"), P("pattern", "motif", "str")), (P("result", "trouvé", "bool"), P("match", "résultat", "str"))),
          "find_all": V((P("text", "texte", "str"), P("pattern", "motif", "str")), (P("result", "résultats", "list"),)),
          "replace": V((P("text", "texte", "str"), P("pattern", "motif", "str"), P("replacement", "remplacement", "str")), (P("result", "texte", "str"),)),
      }, imports=("re",)),
    S("text_format", "Formater un texte", "Remplace les champs d’un modèle par les valeurs d’un dictionnaire.", "text",
      (P("template", "modèle", "str"), P("values", "valeurs", "dict")), (P("result", "texte", "str"),), fields=(INFO("format_help", "info.text.format"),)),
)



