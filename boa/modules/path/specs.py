from boa.core.module_specs import ModuleBlockSpec
from boa.modules.spec_tools import B, C, I, INFO, P, PATH, S, T, V


SPECS: dict[str, ModuleBlockSpec] = {}


def _add(*specs: ModuleBlockSpec) -> None:
    SPECS.update((spec.key, spec) for spec in specs)


# Files and paths ------------------------------------------------------------
RELATIVE = B("relative_to_project", False, "info.path.relative")
_add(
    S("path_build", "Construire un chemin", "Assemble proprement plusieurs parties de chemin.", "path",
      (P("base", "base", "str"), P("part", "partie", "str")), (P("result", "chemin", "str"),), fields=(PATH("base_path", "folder"), RELATIVE), imports=("pathlib",)),
    S("path_info", "Informations sur un chemin", "Décompose un chemin et renvoie ses principales propriétés.", "path",
      (P("path", "chemin", "str"),),
      (P("name", "nom", "str"), P("stem", "nom sans extension", "str"), P("suffix", "extension", "str"), P("parent", "dossier parent", "str"), P("absolute", "chemin absolu", "str")), fields=(PATH("target_path", "any"), RELATIVE), imports=("pathlib",)),
    S("path_test", "Tester un chemin", "Teste l’existence et la nature d’un chemin.", "path",
      (P("path", "chemin", "str"),), (P("exists", "existe", "bool"), P("is_file", "fichier", "bool"), P("is_dir", "dossier", "bool")), fields=(PATH("target_path", "any"), RELATIVE), imports=("pathlib",)),
    S("path_list", "Lister un dossier", "Liste le contenu d’un dossier avec filtre facultatif.", "path",
      (P("folder", "dossier", "str"),), (P("items", "éléments", "list"), P("count", "nombre", "int")),
      fields=(PATH("folder_path", "folder"), RELATIVE, T("pattern", "*"), B("recursive")), flow=True, imports=("pathlib",)),
    S("path_create_folder", "Créer un dossier", "Crée un dossier et ses parents si nécessaire.", "path",
      (P("folder", "dossier", "str"),), (P("result", "dossier créé", "str"),),
      fields=(PATH("folder_path", "folder"), RELATIVE, B("exist_ok", True)), flow=True, imports=("pathlib",)),
    S("path_copy", "Copier un fichier ou dossier", "Copie un fichier ou un dossier vers une destination.", "path",
      (P("source", "source", "str"), P("destination", "destination", "str")), (P("result", "destination", "str"),),
      fields=(C("mode", "file", "folder"), PATH("source_path"), PATH("destination_path", "folder"), RELATIVE, C("existing", "refuse", "replace")), flow=True, imports=("pathlib", "shutil")),
    S("path_move", "Déplacer ou renommer", "Déplace ou renomme un fichier ou un dossier.", "path",
      (P("source", "source", "str"), P("destination", "destination", "str")), (P("result", "destination", "str"),),
      fields=(PATH("source_path"), PATH("destination_path"), RELATIVE, C("existing", "refuse", "replace")), flow=True, imports=("pathlib", "shutil")),
    S("path_delete", "Supprimer un fichier ou dossier", "Supprime un fichier, un dossier vide ou une arborescence.", "path",
      (P("path", "chemin", "str"),), (P("deleted", "supprimé", "bool"),),
      fields=(C("mode", "file", "empty_folder", "folder_tree", info="info.path.delete"), PATH("target_path"), RELATIVE, B("ignore_missing")), flow=True, imports=("pathlib", "shutil")),
    S("file_text", "Lire ou écrire un fichier texte", "Lit, écrit ou complète un fichier texte.", "path",
      fields=(C("mode", "read", "write", "append"), PATH("file_path"), RELATIVE, C("encoding", "utf8", "utf8_bom", "ascii", "latin1", "cp1252"), B("create_parents", True)),
      variants={
          "read": V((P("path", "fichier", "str"),), (P("text", "texte", "str"),)),
          "write": V((P("path", "fichier", "str"), P("text", "texte", "str")), (P("result", "fichier", "str"),)),
          "append": V((P("path", "fichier", "str"), P("text", "texte", "str")), (P("result", "fichier", "str"),)),
      }, flow=True, imports=("pathlib",)),
)



