from dataclasses import dataclass, field
from typing import Any

from boa.core.module_registry import MODULE_CATEGORIES, MODULE_SPECS
from boa.core.operator_specs import OPERATOR_SPECS


@dataclass(slots=True)
class ImportEntry:
    module: str
    statement: str
    origin: str = "manuel"


@dataclass(slots=True)
class VariableEntry:
    name: str
    var_type: str = "any"
    initial_value: str = ""
    is_constant: bool = False
    scope: str = "global"


@dataclass(slots=True)
class BlockDefinition:
    key: str
    title: str
    category: str
    description: str


@dataclass(slots=True)
class BlockData:
    block_type: str
    title: str
    subtitle: str = ""
    code: str = ""
    x: float = 0.0
    y: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)


BLOCK_DEFINITIONS: list[BlockDefinition] = [
    BlockDefinition("empty", "Code Python libre", "Base", "Exécute du code Python écrit librement."),
    BlockDefinition("print", "print", "Sorties", "Afficher une valeur dans la console."),
    BlockDefinition("input", "input", "Valeurs", "Demander une saisie utilisateur."),
    BlockDefinition("value", "value", "Valeurs", "Valeur littérale typée."),
    BlockDefinition("call", "call", "Fonctions", "Appel de fonction ou méthode importée."),
    BlockDefinition("decorator", "Décorateur @", "Définition", "Décorateur aimanté à une DEF ou une Classe."),
    BlockDefinition("return", "RETOUR", "Définition", "Retourne une valeur depuis une fonction."),
    BlockDefinition("assign", "AFFECTER", "Valeurs", "Affecte une valeur à une variable dans le flux."),
    BlockDefinition("attribute_get", "ACCÈS ATTRIBUT", "Valeurs", "Lit un attribut d’un objet."),
    BlockDefinition("class_attribute", "ATTRIBUT", "Définition", "Déclare un attribut dans une classe."),
    BlockDefinition("multi_assign", "AFFECTATION MULTIPLE", "Valeurs", "Répartit une valeur dans plusieurs variables."),
    BlockDefinition("try", "GESTION D’EXCEPTION", "Conditions", "Gère try, except, else et finally."),
    BlockDefinition("match", "CORRESPONDANCE", "Conditions", "Sélectionne une branche avec match/case."),
    BlockDefinition("with", "CONTEXTE (WITH)", "Base", "Exécute un graphe dans un contexte."),
    BlockDefinition("await", "ATTENDRE (AWAIT)", "Base", "Attend une opération asynchrone."),
    BlockDefinition("set_literal", "ENSEMBLE", "Valeurs", "Crée un ensemble Python."),
    BlockDefinition("if", "if", "Conditions", "Condition booléenne avec sorties vrai/faux."),
    BlockDefinition("true", "TRUE", "Logique", "Constante booléenne vraie."),
    BlockDefinition("false", "FALSE", "Logique", "Constante booléenne fausse."),
    BlockDefinition("none", "AUCUNE VALEUR", "Logique", "Constante représentant l’absence de valeur."),
    BlockDefinition("tp", "TP", "Base", "Téléporte un flow entre deux blocs TP liés."),
    BlockDefinition("and", "AND", "Logique", "Sortie vraie si les deux entrées sont vraies."),
    BlockDefinition("or", "OR", "Logique", "Sortie vraie si au moins une entrée est vraie."),
    BlockDefinition("not", "NOT", "Logique", "Inverse une entrée booléenne."),
    BlockDefinition("xor", "XOR", "Logique", "Sortie vraie si une seule entrée est vraie."),
    BlockDefinition("nand", "NAND", "Logique", "Inverse du AND."),
    BlockDefinition("nor", "NOR", "Logique", "Inverse du OR."),
    BlockDefinition("xnor", "XNOR", "Logique", "Inverse du XOR."),
    BlockDefinition("while", "while", "Boucles", "Boucle tant que la condition est vraie."),
    BlockDefinition("for", "for", "Boucles", "Boucle sur une séquence."),
    BlockDefinition("def_input_p", "Entrée (P)", "Définition", "Entrée permanente, toujours visible sur le bloc Appel."),
    BlockDefinition("def_input", "Entrée", "Définition", "Entrée masquable sur le bloc Appel."),
    BlockDefinition("def_output_p", "Sortie (P)", "Définition", "Sortie permanente, toujours visible sur le bloc Appel."),
    BlockDefinition("def_output", "Sortie", "Définition", "Sortie masquable sur le bloc Appel."),
]

BLOCK_DEFINITIONS.extend(
    BlockDefinition(spec.key, spec.title, "Opérateurs", spec.description)
    for spec in OPERATOR_SPECS.values()
)

BLOCK_DEFINITIONS.extend(
    BlockDefinition(spec.key, spec.title, MODULE_CATEGORIES.get(spec.module, "Modules"), spec.description)
    for spec in MODULE_SPECS.values() if not getattr(spec, "hidden", False)
)
