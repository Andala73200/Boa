HELPERS = {
"json_file": r'''
def __boa_json_read(path, encoding="utf-8"):
    with pathlib.Path(path).open("r", encoding=encoding) as stream: return json.load(stream)

def __boa_json_write(path, data, encoding="utf-8", indent=2, sort_keys=False, ensure_ascii=False, create_parents=True):
    target = pathlib.Path(path)
    if create_parents: target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding=encoding) as stream: json.dump(data, stream, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
    return str(target)
''',
}

