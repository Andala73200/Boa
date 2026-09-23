HELPERS = {
"scalar": r'''
def __boa_to_bool(value):
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "oui", "vrai"}
    return bool(value)

def __boa_convert(value, target):
    if target is bool:
        return __boa_to_bool(value)
    if target is bytes and isinstance(value, str):
        return value.encode("utf-8")
    if target in {list, tuple, set, dict} and isinstance(value, str):
        value = ast.literal_eval(value)
    return target(value)

def __boa_can_convert(value, target):
    try:
        __boa_convert(value, target)
        return True
    except (TypeError, ValueError, OverflowError):
        return False

def __boa_scalar(value):
    text = str(value).strip()
    if not text:
        return ""
    try:
        return int(text)
    except ValueError:
        try:
            return float(text.replace(",", "."))
        except ValueError:
            if text.casefold() in {"true", "false", "vrai", "faux"}:
                return text.casefold() in {"true", "vrai"}
            return value
''',
}

