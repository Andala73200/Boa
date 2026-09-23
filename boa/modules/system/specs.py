from boa.core.module_specs import ModuleBlockSpec
from boa.modules.spec_tools import B, C, I, INFO, P, PATH, S, T, V

RELATIVE = B("relative_to_project", False, "info.path.relative")


SPECS: dict[str, ModuleBlockSpec] = {}


def _add(*specs: ModuleBlockSpec) -> None:
    SPECS.update((spec.key, spec) for spec in specs)


# System and programs --------------------------------------------------------
_add(
    S("system_info", "Informations système", "Renvoie les informations principales sur le système et Python.", "system",
      (), (P("system", "système", "str"), P("release", "version", "str"), P("machine", "machine", "str"), P("python", "Python", "str")), imports=("platform",)),
    S("environment_variable", "Variable d’environnement", "Lit, définit ou supprime une variable d’environnement.", "system",
      fields=(C("mode", "read", "write", "delete"),),
      variants={
          "read": V((P("name", "nom", "str"),), (P("value", "valeur", "str"), P("exists", "existe", "bool"))),
          "write": V((P("name", "nom", "str"), P("value", "valeur", "str")), (P("success", "réussi", "bool"),)),
          "delete": V((P("name", "nom", "str"),), (P("success", "réussi", "bool"),)),
      }, flow=True, imports=("os",)),
    S("run_program", "Lancer un programme", "Exécute un programme et récupère son résultat.", "system",
      (P("program", "programme", "str"), P("arguments", "arguments", "list"), P("input_text", "entrée", "str")),
      (P("stdout", "sortie", "str"), P("stderr", "erreur", "str"), P("return_code", "code retour", "int"), P("success", "réussi", "bool")),
      fields=(PATH("program_path"), I("timeout", 0, "info.system.timeout"), B("hide_window", True)), flow=True, imports=("subprocess", "sys")),
    S("open_external", "Ouvrir avec le système", "Ouvre un fichier, un dossier ou une adresse web avec l’application associée.", "system",
      (P("target", "cible", "str"),), (P("success", "réussi", "bool"),),
      fields=(C("mode", "file", "folder", "url"), PATH("target_path"), RELATIVE), flow=True, imports=("os", "subprocess", "sys", "webbrowser")),
)


