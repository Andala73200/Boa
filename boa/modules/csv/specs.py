from boa.core.module_specs import ModuleBlockSpec
from boa.modules.spec_tools import B, C, I, INFO, P, PATH, S, T, V

RELATIVE = B("relative_to_project", False, "info.path.relative")


SPECS: dict[str, ModuleBlockSpec] = {}


def _add(*specs: ModuleBlockSpec) -> None:
    SPECS.update((spec.key, spec) for spec in specs)


# CSV ------------------------------------------------------------------------
CSV_FORMAT_FIELDS = (
    C("separator", "semicolon", "comma", "tab", "custom"),
    T("custom_separator", ";", show_if=(("separator", "custom"),)),
    C("encoding", "utf8", "utf8_bom", "ascii", "latin1", "cp1252"),
    B("has_header", True),
)
_add(
    S("csv_read", "Lire un fichier CSV", "Charge un fichier CSV sous forme de tableau.", "csv",
      (P("path", "fichier", "str"),), (P("rows", "tableau", "list"), P("headers", "en-têtes", "list")),
      fields=(PATH("file_path"), RELATIVE, C("separator", "auto", "semicolon", "comma", "tab", "custom"), T("custom_separator", ";", show_if=(("separator", "custom"),)), C("encoding", "utf8", "utf8_bom", "ascii", "latin1", "cp1252"), B("has_header", True), B("auto_types", False, "info.csv.auto_types")), flow=True, imports=("csv", "io", "pathlib")),
    S("csv_write", "Écrire un fichier CSV", "Enregistre un tableau dans un fichier CSV.", "csv",
      (P("path", "fichier", "str"), P("rows", "tableau", "list")), (P("result", "fichier", "str"),),
      fields=(PATH("file_path"), RELATIVE, *CSV_FORMAT_FIELDS, B("excel_compatible", False, "info.csv.excel"), B("create_parents", True)), flow=True, imports=("csv", "pathlib")),
    S("csv_append", "Ajouter à un fichier CSV", "Ajoute des lignes à la fin d’un fichier CSV.", "csv",
      (P("path", "fichier", "str"), P("rows", "lignes", "list")), (P("result", "fichier", "str"),),
      fields=(PATH("file_path"), RELATIVE, *CSV_FORMAT_FIELDS, B("write_header_if_empty", True)), flow=True, imports=("csv", "pathlib")),
    S("csv_convert", "Convertir CSV", "Convertit un texte CSV en tableau ou un tableau en texte CSV.", "csv",
      fields=(C("mode", "text_to_data", "data_to_text"), *CSV_FORMAT_FIELDS, B("auto_types", False, "info.csv.auto_types")),
      variants={
          "text_to_data": V((P("value", "texte CSV", "str"),), (P("result", "tableau", "list"),)),
          "data_to_text": V((P("value", "tableau", "list"),), (P("result", "texte CSV", "str"),)),
      }, imports=("csv", "io")),
)


