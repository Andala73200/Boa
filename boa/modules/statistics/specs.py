from boa.core.module_specs import ModuleBlockSpec
from boa.modules.spec_tools import B, C, I, INFO, P, PATH, S, T, V


SPECS: dict[str, ModuleBlockSpec] = {}


def _add(*specs: ModuleBlockSpec) -> None:
    SPECS.update((spec.key, spec) for spec in specs)


# Statistics -----------------------------------------------------------------
_add(
    S("statistics_summary", "Résumé statistique", "Calcule les principales informations d’une série numérique.", "statistics",
      (P("values", "valeurs"),), (P("count", "nombre", "int"), P("minimum", "minimum", "float"), P("maximum", "maximum", "float"), P("sum", "somme", "float"), P("mean", "moyenne", "float"), P("median", "médiane", "float")), imports=("statistics",)),
    S("statistics_mean", "Calculer une moyenne", "Calcule une moyenne arithmétique, pondérée, géométrique ou harmonique.", "statistics",
      fields=(C("mode", "arithmetic", "weighted", "geometric", "harmonic"),),
      variants={
          "arithmetic": V((P("values", "valeurs"),), (P("result", "moyenne", "float"),)),
          "weighted": V((P("values", "valeurs"), P("weights", "poids")), (P("result", "moyenne", "float"),)),
          "geometric": V((P("values", "valeurs"),), (P("result", "moyenne", "float"),)),
          "harmonic": V((P("values", "valeurs"),), (P("result", "moyenne", "float"),)),
      }, imports=("statistics",)),
    S("statistics_dispersion", "Mesurer la dispersion", "Calcule la variance et l’écart-type d’une série.", "statistics",
      (P("values", "valeurs"),), (P("variance", "variance", "float"), P("stdev", "écart-type", "float")), fields=(C("mode", "sample", "population"),), imports=("statistics",)),
    S("statistics_quantiles", "Calculer des quantiles", "Découpe une série en groupes de même taille.", "statistics",
      (P("values", "valeurs"), P("groups", "groupes", "int")), (P("result", "quantiles", "list"),), fields=(C("method", "exclusive", "inclusive", info="info.statistics.quantiles"),), imports=("statistics",)),
    S("statistics_compare", "Comparer deux séries", "Calcule covariance, corrélation et régression linéaire.", "statistics",
      (P("first", "série A"), P("second", "série B")), (P("covariance", "covariance", "float"), P("correlation", "corrélation", "float"), P("slope", "pente", "float"), P("intercept", "ordonnée", "float")), imports=("statistics",)),
)



