def expression(block: dict, port: str, input_expr) -> str:
    key = str(block.get("key", ""))
    cfg = dict(block.get("module_config", {}) or {})
    mode = str(cfg.get("mode", ""))
    a = lambda name, default="None": input_expr(name, default)
    empty = "''"
    if key == "text_transform":
        text = a("text", empty)
        return {"lower": f"{text}.lower()", "upper": f"{text}.upper()", "title": f"{text}.title()", "capitalize": f"{text}.capitalize()", "strip": f"{text}.strip()", "normalize_spaces": f"' '.join({text}.split())"}.get(mode, "None")
    if key == "text_split_join":
        if mode == "split": return f"{a('value', empty)}.split({a('separator_value', 'None')})"
        if mode == "join": return f"{a('separator_value', empty)}.join(map(str, {a('value','[]')}))"
        return "None"
    if key == "text_replace": return f"{a('text', empty)}.replace({a('old', empty)}, {a('new', empty)}, {a('count','-1')})"
    if key == "text_search":
        text, query = a("text", empty), a("query", empty)
        if not cfg.get("case_sensitive", True): text, query = f"{text}.casefold()", f"{query}.casefold()"
        return {"contains": f"({query} in {text})", "find": f"{text}.find({query})", "count": f"{text}.count({query})", "starts_with": f"{text}.startswith({query})", "ends_with": f"{text}.endswith({query})"}.get(mode, "None")
    if key == "regex_operation":
        flags = _regex_flags(cfg); text, pattern = a("text", empty), a("pattern", empty)
        if mode == "full_match": return f"(re.fullmatch({pattern}, {text}, flags={flags}) is not None)"
        if mode == "search":
            found = f"re.search({pattern}, {text}, flags={flags})"
            return f"({found} is not None)" if port == "result" else f"(({found}).group(0) if {found} else '')"
        if mode == "find_all": return f"re.findall({pattern}, {text}, flags={flags})"
        if mode == "replace": return f"re.sub({pattern}, {a('replacement', empty)}, {text}, flags={flags})"
        return "None"
    return f"{a('template', empty)}.format_map({a('values','{}')})"


def _regex_flags(cfg: dict) -> str:
    parts = []
    if cfg.get("ignore_case"): parts.append("re.IGNORECASE")
    if cfg.get("multiline"): parts.append("re.MULTILINE")
    return " | ".join(parts) or "0"


BLOCK_HELPERS = {}
HELPERS = {}
