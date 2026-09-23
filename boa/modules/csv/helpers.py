HELPERS = {
"csv_memory": r'''
def __boa_csv_from_text(text, delimiter=";", has_header=True, auto_types=False):
    sample = str(text); actual = delimiter or csv.Sniffer().sniff(sample[:4096]).delimiter
    rows = list(csv.reader(io.StringIO(sample), delimiter=actual)); headers = rows.pop(0) if has_header and rows else []
    if auto_types: rows = [[__boa_scalar(value) for value in row] for row in rows]
    if has_header: rows = [dict(zip(headers, row)) for row in rows]
    return rows, headers

def __boa_csv_to_text(rows, delimiter=";", has_header=True):
    output = io.StringIO(); rows = list(rows or [])
    if rows and isinstance(rows[0], dict):
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter=delimiter); writer.writeheader() if has_header else None; writer.writerows(rows)
    else:
        csv.writer(output, delimiter=delimiter).writerows(rows)
    return output.getvalue()
''',
"csv_file": r'''
def __boa_csv_read(path, delimiter="", encoding="utf-8", has_header=True, auto_types=False):
    text = pathlib.Path(path).read_text(encoding=encoding); return __boa_csv_from_text(text, delimiter, has_header, auto_types)

def __boa_csv_write(path, rows, delimiter=";", encoding="utf-8", has_header=True, append=False, create_parents=True):
    target = pathlib.Path(path)
    if create_parents: target.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows or []); exists = target.exists() and target.stat().st_size > 0
    with target.open("a" if append else "w", newline="", encoding=encoding) as stream:
        if rows and isinstance(rows[0], dict):
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter=delimiter); writer.writeheader() if has_header and not exists else None; writer.writerows(rows)
        else: csv.writer(stream, delimiter=delimiter).writerows(rows)
    return str(target)
''',
}

