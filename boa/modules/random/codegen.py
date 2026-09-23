def expression(block: dict, port: str, input_expr) -> str:
    key = str(block.get("key", ""))
    cfg = dict(block.get("module_config", {}) or {})
    mode = str(cfg.get("mode", ""))
    a = lambda name, default="None": input_expr(name, default)
    if key == "random_number":
        if mode == "integer":
            return f"random.randint({a('minimum', '0')}, {a('maximum', '0')})"
        if mode == "decimal":
            return f"random.uniform({a('minimum', '0.0')}, {a('maximum', '1.0')})"
        return "None"
    values = a("collection", "[]")
    if mode == "choose_item": return f"random.choice({values})"
    if mode == "shuffle": return f"random.sample({values}, k=len({values}))"
    if mode == "sample":
        function = "random.choices" if cfg.get("with_replacement") else "random.sample"
        return f"{function}({values}, k={a('count', '0')})"
    return "None"


BLOCK_HELPERS = {}
HELPERS = {}
