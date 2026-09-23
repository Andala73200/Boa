from boa.modules.security.helpers import HELPERS


def expression(block: dict, port: str, input_expr) -> str:
    key = str(block.get("key", ""))
    cfg = dict(block.get("module_config", {}) or {})
    mode = str(cfg.get("mode", ""))
    a = lambda name, default="None": input_expr(name, default)
    empty = "''"; empty_bytes = "b''"
    if key == "text_bytes":
        encoding = repr(_encoding(cfg)); errors = repr(str(cfg.get("errors") or "strict"))
        if mode == "text_to_bytes": return f"{a('value', empty)}.encode({encoding}, errors={errors})"
        if mode == "bytes_to_text": return f"bytes({a('value', empty_bytes)}).decode({encoding}, errors={errors})"
        return "None"
    if key == "encode_decode": return _codec_expr(cfg, mode, a("value"))
    if key == "hmac_signature":
        digest = str(cfg.get("algorithm") or "sha256")
        value = f"__boa_bytes({a('value')})"; secret = f"__boa_bytes({a('secret')})"
        signature = f"hmac.new({secret}, {value}, hashlib.{digest}).hexdigest()"
        if mode == "create": return signature
        if mode == "verify": return f"hmac.compare_digest({signature}, str({a('expected', empty)}))"
        return "None"
    if key == "secure_value": return _secure_expr(cfg, mode, a)
    if mode == "uuid4": return "str(uuid.uuid4())"
    if mode == "uuid5": return f"str(uuid.uuid5({_uuid_namespace(cfg)}, str({a('name', empty)})))"
    return "None"


def flow(block: dict, input_expr) -> str:
    cfg = dict(block.get("module_config", {}) or {})
    a = lambda name, default="None": input_expr(name, default)
    path = repr(str(cfg.get("file_path") or "")); empty = "''"
    return f"__boa_digest({str(cfg.get('mode') or '')!r}, {str(cfg.get('source') or 'data')!r}, {str(cfg.get('algorithm') or 'sha256')!r}, {a('value', path)}, {a('expected', empty)})"


def _encoding(cfg: dict) -> str:
    value = str(cfg.get("encoding") or "utf8")
    return {"utf8": "utf-8", "ascii": "ascii", "latin1": "latin-1", "cp1252": "cp1252", "custom": str(cfg.get("custom_encoding") or "utf-8")}.get(value, "utf-8")


def _codec_expr(cfg: dict, mode: str, value: str) -> str:
    fmt = str(cfg.get("format") or "")
    encoders = {"base64": "base64.b64encode", "base64_url": "base64.urlsafe_b64encode", "base32": "base64.b32encode", "hex": "base64.b16encode", "base85": "base64.b85encode"}
    decoders = {"base64": "base64.b64decode", "base64_url": "base64.urlsafe_b64decode", "base32": "base64.b32decode", "hex": "base64.b16decode", "base85": "base64.b85decode"}
    if mode == "encode" and fmt in encoders: return f"{encoders[fmt]}(bytes({value})).decode('ascii')"
    if mode == "decode" and fmt in decoders: return f"{decoders[fmt]}(str({value}).encode('ascii'))"
    return "None"


def _secure_expr(cfg: dict, mode: str, a) -> str:
    length = max(1, int(cfg.get("length", 32) or 32))
    if mode == "token_hex": return f"secrets.token_hex({length})"
    if mode == "token_url": return f"secrets.token_urlsafe({length})"
    if mode == "secure_integer": return f"secrets.randbelow({a('maximum','1')})"
    if mode == "secure_choice": return f"secrets.choice({a('collection','[]')})"
    if mode == "password":
        pools = []
        if cfg.get("lowercase", True): pools.append("string.ascii_lowercase")
        if cfg.get("uppercase", True): pools.append("string.ascii_uppercase")
        if cfg.get("digits", True): pools.append("string.digits")
        if cfg.get("symbols"): pools.append("string.punctuation")
        pool = " + ".join(pools) or "string.ascii_letters + string.digits"
        return f"''.join(secrets.choice({pool}) for _ in range({length}))"
    return "None"


def _uuid_namespace(cfg: dict) -> str:
    value = str(cfg.get("namespace") or "dns")
    custom = f"uuid.UUID({str(cfg.get('custom_namespace') or '')!r})"
    return {"dns": "uuid.NAMESPACE_DNS", "url": "uuid.NAMESPACE_URL", "oid": "uuid.NAMESPACE_OID", "x500": "uuid.NAMESPACE_X500", "custom": custom}.get(value, "uuid.NAMESPACE_DNS")


BLOCK_HELPERS = {"hmac_signature": {"bytes"}, "digest": {"digest", "bytes"}}
