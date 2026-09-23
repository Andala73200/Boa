from boa.core.module_specs import ModuleBlockSpec
from boa.modules.spec_tools import B, C, I, INFO, P, PATH, S, T, V

RELATIVE = B("relative_to_project", False, "info.path.relative")


SPECS: dict[str, ModuleBlockSpec] = {}


def _add(*specs: ModuleBlockSpec) -> None:
    SPECS.update((spec.key, spec) for spec in specs)


# Encoding, identifiers and security ----------------------------------------
_add(
    S("text_bytes", "Texte et octets", "Convertit du texte en octets ou des octets en texte.", "security",
      fields=(C("mode", "text_to_bytes", "bytes_to_text"), C("encoding", "utf8", "ascii", "latin1", "cp1252", "custom"), T("custom_encoding", "utf-8", show_if=(("encoding", "custom"),)), C("errors", "strict", "replace", "ignore", info="info.encoding.errors")),
      variants={
          "text_to_bytes": V((P("value", "texte", "str"),), (P("result", "octets", "bytes"),)),
          "bytes_to_text": V((P("value", "octets", "bytes"),), (P("result", "texte", "str"),)),
      }),
    S("encode_decode", "Encoder ou décoder", "Encode ou décode des données dans un format textuel réversible.", "security",
      fields=(C("mode", "encode", "decode"), C("format", "base64", "base64_url", "base32", "hex", "base85", info="info.encoding.not_encryption"), B("strict_validation", True, show_if=(("mode", "decode"),))),
      variants={
          "encode": V((P("value", "octets", "bytes"),), (P("result", "texte", "str"),)),
          "decode": V((P("value", "texte", "str"),), (P("result", "octets", "bytes"),)),
      }, imports=("base64",)),
    S("digest", "Calculer ou vérifier une empreinte", "Calcule ou vérifie l’empreinte d’une donnée ou d’un fichier.", "security",
      fields=(C("mode", "calculate", "verify"), C("source", "data", "file"), C("algorithm", "sha256", "sha512", "sha3_256", "blake2b", "crc32", "md5", "sha1", info="info.digest.algorithms"), PATH("file_path"), RELATIVE),
      variants={
          "calculate": V((P("value", "donnée / fichier"),), (P("digest", "empreinte", "str"),)),
          "verify": V((P("value", "donnée / fichier"), P("expected", "empreinte attendue", "str")), (P("valid", "valide", "bool"), P("digest", "empreinte", "str"))),
      }, flow=True, imports=("hashlib", "hmac", "pathlib", "zlib")),
    S("hmac_signature", "Créer ou vérifier une signature HMAC", "Authentifie des données avec une clé secrète.", "security",
      fields=(C("mode", "create", "verify"), C("algorithm", "sha256", "sha512", info="info.hmac")),
      variants={
          "create": V((P("value", "donnée"), P("secret", "clé secrète")), (P("signature", "signature", "str"),)),
          "verify": V((P("value", "donnée"), P("secret", "clé secrète"), P("expected", "signature attendue", "str")), (P("valid", "valide", "bool"),)),
      }, imports=("hashlib", "hmac")),
    S("secure_value", "Générer une valeur sécurisée", "Génère un jeton, mot de passe, nombre ou choix avec une source sécurisée.", "security",
      fields=(C("mode", "token_hex", "token_url", "password", "secure_integer", "secure_choice", info="info.secrets"), I("length", 32), B("lowercase", True, show_if=(("mode", "password"),)), B("uppercase", True, show_if=(("mode", "password"),)), B("digits", True, show_if=(("mode", "password"),)), B("symbols", False, show_if=(("mode", "password"),))),
      variants={
          "token_hex": V((), (P("result", "jeton", "str"),)),
          "token_url": V((), (P("result", "jeton", "str"),)),
          "password": V((), (P("result", "mot de passe", "str"),)),
          "secure_integer": V((P("maximum", "maximum", "int"),), (P("result", "nombre", "int"),)),
          "secure_choice": V((P("collection", "collection"),), (P("result", "élément"),)),
      }, imports=("secrets", "string")),
    S("uuid_generate", "Générer un identifiant UUID", "Génère un identifiant aléatoire ou déterministe.", "security",
      fields=(C("mode", "uuid4", "uuid5", info="info.uuid"), C("namespace", "dns", "url", "oid", "x500", "custom", show_if=(("mode", "uuid5"),)), T("custom_namespace", "", show_if=(("namespace", "custom"),))),
      variants={
          "uuid4": V((), (P("result", "UUID", "str"),)),
          "uuid5": V((P("name", "nom", "str"),), (P("result", "UUID", "str"),)),
      }, imports=("uuid",)),
)


