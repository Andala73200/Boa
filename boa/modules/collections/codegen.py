from boa.modules.collections.helpers import HELPERS


def expression(block: dict, port: str, input_expr) -> str:
    key = str(block.get("key", ""))
    cfg = dict(block.get("module_config", {}) or {})
    mode = str(cfg.get("mode", ""))
    a = lambda name, default="None": input_expr(name, default)
    if key == "collection_get":
        collection, item_key = a("collection", "{}"), a("key")
        return f"{collection}.get({item_key}, {a('default')})" if mode == "with_default" else f"{collection}.get({item_key})"
    if key == "collection_enumerate":
        collection = a("collection", "[]")
        return f"enumerate({collection}, {a('start_index', '0')})" if mode == "with_start" else f"enumerate({collection})"
    if key == "collection_zip":
        return f"zip({a('first', '[]')}, {a('second', '[]')})"
    if key == "collection_dict":
        keys = [str(item) for item in cfg.get("keys", [])][:16]
        pairs = [f"{key_name!r}: {a(f'value_{index}')}" for index, key_name in enumerate(keys, start=1)]
        return "{" + ", ".join(pairs) + "}"
    if key == "collection_create":
        fallbacks = {"list": "[]", "tuple": "[]", "set": "[]", "dict": "{}"}
        return f"{mode}({a('values', fallbacks[mode])})" if mode in fallbacks else "None"
    if key == "collection_access":
        collection = a("collection", "{}" if mode == "key" else "[]")
        if mode in {"index", "key"}: return f"{collection}[{a('index', '0') if mode == 'index' else a('key', 'None')}]"
        if mode == "slice": return f"{collection}[{a('start_index','None')}:{a('end_index','None')}:{a('step','None')}]"
        return "None"
    if key == "collection_modify":
        collection = a("collection", "[]")
        if mode == "add": return f"(list({collection}) + [{a('value')}])"
        if mode == "insert": return f"(list({collection})[:{a('index','0')}] + [{a('value')}] + list({collection})[{a('index','0')}:])"
        if mode == "replace": return f"__boa_collection_replace({collection}, {a('index')}, {a('value')})"
        if mode == "remove": return f"__boa_collection_remove({collection}, {a('value')})"
        return "None"
    if key == "collection_sort": return f"sorted({a('collection','[]')}, reverse={bool(cfg.get('reverse'))})"
    if key == "collection_search":
        collection, value = a("collection", "[]"), a("value")
        return {"contains": f"({value} in {collection})", "index": f"list({collection}).index({value})", "count": f"list({collection}).count({value})"}.get(mode, "None")
    first, second = a("first", "[]"), a("second", "[]")
    return {"concatenate": f"(list({first}) + list({second}))", "zip": f"list(zip({first}, {second}))", "merge": f"({{**dict({first}), **dict({second})}})", "union": f"(set({first}) | set({second}))", "intersection": f"(set({first}) & set({second}))", "difference": f"(set({first}) - set({second}))"}.get(mode, "None")


BLOCK_HELPERS = {"collection_modify": {"collection"}}

def flow(block: dict, input_expr) -> str:
    key = str(block.get("key", ""))
    if key == "collection_append":
        return f"{input_expr('collection', '[]')}.append({input_expr('value', 'None')})"
    return "None"

