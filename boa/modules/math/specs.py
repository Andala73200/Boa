from boa.core.module_specs import (
    ModuleBlockSpec, ModuleChoiceSpec, ModuleFieldSpec, ModulePortSpec, ModuleVariantSpec,
)


MathPortSpec = ModulePortSpec
MathBlockSpec = ModuleBlockSpec


X = MathPortSpec("x", "x", "float")
Y = MathPortSpec("y", "y", "float")
A = MathPortSpec("a", "a", "float")
B = MathPortSpec("b", "b", "float")
N = MathPortSpec("n", "n", "int")
K = MathPortSpec("k", "k", "int")
I = MathPortSpec("i", "i", "int")
VALUES = MathPortSpec("values", "values", "any")
P = MathPortSpec("p", "p", "any")
Q = MathPortSpec("q", "q", "any")
VALUE = MathPortSpec("value", "valeur", "any")
DIGITS = MathPortSpec("digits", "décimales", "int")
RESULT_ANY = MathPortSpec("result", "résultat", "any")
RESULT_INT = MathPortSpec("result", "résultat", "int")


def _one(name: str, title: str, desc: str, inputs, out_type: str, expr: str) -> MathBlockSpec:
    return MathBlockSpec(
        f"math_{name}", title, desc, tuple(inputs),
        (MathPortSpec("result", "", out_type),), {"result": expr}, "math", imports=("math",),
    )


def _const(name: str, title: str, desc: str, out_type: str = "float") -> MathBlockSpec:
    return _one(name, title, desc, (), out_type, f"math.{name}")


MATH_SPECS: dict[str, MathBlockSpec] = {spec.key: spec for spec in [
    MathBlockSpec(
        "math_abs", "Valeur absolue", "Renvoie la valeur absolue Python sans forcer le type.",
        (VALUE,), (RESULT_ANY,), {"result": "abs({value})"}, "math",
    ),
    MathBlockSpec(
        "math_round", "Arrondir", "Arrondit une valeur, avec ou sans nombre de décimales.",
        (VALUE, DIGITS), (RESULT_ANY,), {}, "math",
        fields=(ModuleFieldSpec(
            "mode", "field.mode", "choice",
            (
                ModuleChoiceSpec("without_digits", "option.without_digits"),
                ModuleChoiceSpec("with_digits", "option.with_digits"),
            ),
            "",
        ),),
        variants={
            "without_digits": ModuleVariantSpec(
                (VALUE,), (RESULT_INT,), {"result": "round({value})"},
            ),
            "with_digits": ModuleVariantSpec(
                (VALUE, DIGITS), (RESULT_ANY,), {"result": "round({value}, {digits})"},
            ),
        },
    ),
    _const("pi", "π", "Constante pi."),
    _const("e", "e", "Constante e."),
    _const("tau", "τ", "Constante tau, égale à 2*pi."),
    _const("inf", "∞", "Infini flottant."),
    _const("nan", "NaN", "Valeur flottante non numérique."),
    _one("ceil", "ceil", "Arrondi supérieur entier.", (X,), "int", "math.ceil({x})"),
    _one("floor", "floor", "Arrondi inférieur entier.", (X,), "int", "math.floor({x})"),
    _one("trunc", "trunc(x)", "Partie entière tronquée.", (X,), "int", "math.trunc({x})"),
    _one("fabs", "|x|", "Valeur absolue flottante.", (X,), "float", "math.fabs({x})"),
    _one("copysign", "copy sign", "Copie le signe de y sur x.", (X, Y), "float", "math.copysign({x}, {y})"),
    _one("fmod", "fmod", "Modulo flottant.", (X, Y), "float", "math.fmod({x}, {y})"),
    _one("remainder", "remainder", "Reste flottant IEEE.", (X, Y), "float", "math.remainder({x}, {y})"),
    MathBlockSpec("math_modf", "modf", "Sépare fraction et partie entière.", (X,), (MathPortSpec("frac", "frac", "float"), MathPortSpec("int", "int", "float")), {"frac": "math.modf({x})[0]", "int": "math.modf({x})[1]"}, "math"),
    _one("fma", "x·y+z", "Calcule x*y+z.", (X, Y, MathPortSpec("z", "z", "float")), "float", "math.fma({x}, {y}, {z})"),
    _one("sqrt", "√x", "Racine carrée.", (X,), "float", "math.sqrt({x})"),
    _one("cbrt", "∛x", "Racine cubique.", (X,), "float", "math.cbrt({x})"),
    _one("pow", "xʸ", "Puissance x exposant y.", (X, Y), "float", "math.pow({x}, {y})"),
    _one("exp", "eˣ", "Exponentielle.", (X,), "float", "math.exp({x})"),
    _one("exp2", "2ˣ", "Puissance de 2.", (X,), "float", "math.exp2({x})"),
    _one("expm1", "eˣ−1", "Exponentielle moins 1.", (X,), "float", "math.expm1({x})"),
    _one("log", "ln(x)", "Logarithme naturel.", (X,), "float", "math.log({x})"),
    _one("log_base", "logᵦ(x)", "Logarithme avec base.", (X, MathPortSpec("base", "base", "float")), "float", "math.log({x}, {base})"),
    _one("log1p", "ln(1+x)", "Logarithme naturel de 1+x.", (X,), "float", "math.log1p({x})"),
    _one("log2", "log₂(x)", "Logarithme base 2.", (X,), "float", "math.log2({x})"),
    _one("log10", "log₁₀(x)", "Logarithme base 10.", (X,), "float", "math.log10({x})"),
    _one("sin", "sin(x)", "Sinus.", (X,), "float", "math.sin({x})"),
    _one("cos", "cos(x)", "Cosinus.", (X,), "float", "math.cos({x})"),
    _one("tan", "tan(x)", "Tangente.", (X,), "float", "math.tan({x})"),
    _one("asin", "sin⁻¹(x)", "Arc sinus.", (X,), "float", "math.asin({x})"),
    _one("acos", "cos⁻¹(x)", "Arc cosinus.", (X,), "float", "math.acos({x})"),
    _one("atan", "tan⁻¹(x)", "Arc tangente.", (X,), "float", "math.atan({x})"),
    _one("atan2", "atan2(y,x)", "Arc tangente avec coordonnées y/x.", (Y, X), "float", "math.atan2({y}, {x})"),
    _one("radians", "°→rad", "Convertit des degrés en radians.", (X,), "float", "math.radians({x})"),
    _one("degrees", "rad→°", "Convertit des radians en degrés.", (X,), "float", "math.degrees({x})"),
    _one("sinh", "sinh(x)", "Sinus hyperbolique.", (X,), "float", "math.sinh({x})"),
    _one("cosh", "cosh(x)", "Cosinus hyperbolique.", (X,), "float", "math.cosh({x})"),
    _one("tanh", "tanh(x)", "Tangente hyperbolique.", (X,), "float", "math.tanh({x})"),
    _one("asinh", "sinh⁻¹(x)", "Arc sinus hyperbolique.", (X,), "float", "math.asinh({x})"),
    _one("acosh", "cosh⁻¹(x)", "Arc cosinus hyperbolique.", (X,), "float", "math.acosh({x})"),
    _one("atanh", "tanh⁻¹(x)", "Arc tangente hyperbolique.", (X,), "float", "math.atanh({x})"),
    _one("factorial", "n!", "Factorielle.", (N,), "int", "math.factorial({n})"),
    _one("comb", "C(n,k)", "Combinaison.", (N, K), "int", "math.comb({n}, {k})"),
    _one("perm", "P(n,k)", "Permutation.", (N, K), "int", "math.perm({n}, {k})"),
    _one("gcd", "gcd", "Plus grand diviseur commun.", (MathPortSpec("a", "a", "int"), MathPortSpec("b", "b", "int")), "int", "math.gcd({a}, {b})"),
    _one("lcm", "lcm", "Plus petit multiple commun.", (MathPortSpec("a", "a", "int"), MathPortSpec("b", "b", "int")), "int", "math.lcm({a}, {b})"),
    _one("isqrt", "⌊√n⌋", "Racine carrée entière.", (N,), "int", "math.isqrt({n})"),
    _one("fsum", "Σ", "Somme flottante précise.", (VALUES,), "float", "math.fsum({values})"),
    _one("prod", "Π", "Produit des valeurs.", (VALUES,), "any", "math.prod({values})"),
    _one("sumprod", "Σ a·b", "Somme des produits.", (P, Q), "any", "math.sumprod({p}, {q})"),
    _one("dist", "dist", "Distance entre deux points.", (P, Q), "float", "math.dist({p}, {q})"),
    _one("hypot", "√Σx²", "Norme euclidienne.", (X, Y), "float", "math.hypot({x}, {y})"),
    _one("isfinite", "finite?", "Teste si x est fini.", (X,), "bool", "math.isfinite({x})"),
    _one("isinf", "∞?", "Teste si x est infini.", (X,), "bool", "math.isinf({x})"),
    _one("isnan", "NaN?", "Teste si x est NaN.", (X,), "bool", "math.isnan({x})"),
    _one("isclose", "a≈b", "Teste si deux valeurs sont proches.", (A, B), "bool", "math.isclose({a}, {b})"),
    MathBlockSpec("math_frexp", "m·2ᵉ", "Décompose x en mantisse et exposant.", (X,), (MathPortSpec("m", "m", "float"), MathPortSpec("e", "e", "int")), {"m": "math.frexp({x})[0]", "e": "math.frexp({x})[1]"}, "math"),
    _one("ldexp", "x·2ⁱ", "Calcule x * 2**i.", (X, I), "float", "math.ldexp({x}, {i})"),
    _one("nextafter", "next→", "Prochain flottant de x vers y.", (X, Y), "float", "math.nextafter({x}, {y})"),
    _one("ulp", "ulp", "Unité de précision de x.", (X,), "float", "math.ulp({x})"),
    _one("erf", "erf", "Fonction erreur.", (X,), "float", "math.erf({x})"),
    _one("erfc", "erfc", "Fonction erreur complémentaire.", (X,), "float", "math.erfc({x})"),
    _one("gamma", "Γ(x)", "Fonction gamma.", (X,), "float", "math.gamma({x})"),
    _one("lgamma", "ln|Γ|", "Logarithme de la valeur absolue de gamma.", (X,), "float", "math.lgamma({x})"),
]}

MATH_BLOCK_KEYS = set(MATH_SPECS)

FEATURED_MATH_KEYS = {
    "math_pi", "math_e", "math_sqrt", "math_pow", "math_ceil", "math_floor",
    "math_sin", "math_cos", "math_tan", "math_degrees", "math_radians",
}


SPECS = MATH_SPECS
