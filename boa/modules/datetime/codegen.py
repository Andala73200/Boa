WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def expression(block: dict, port: str, input_expr) -> str:
    key = str(block.get("key", ""))
    cfg = dict(block.get("module_config", {}) or {})
    mode = str(cfg.get("mode", ""))
    a = lambda name, default="None": input_expr(name, default)
    if key == "datetime_now":
        return {
            "current_datetime": "datetime.datetime.now()",
            "current_date": "datetime.date.today()",
            "current_time": "datetime.datetime.now().time()",
            "timestamp": "datetime.datetime.now().timestamp()",
        }.get(mode, "None")
    if key == "datetime_create":
        defaults = {name: str(int(cfg.get(name, value) or value)) for name, value in {
            "year": 1970, "month": 1, "day": 1, "hour": 0, "minute": 0, "second": 0,
        }.items()}
        values = {name: a(name, default) for name, default in defaults.items()}
        if mode == "date": return "datetime.date({year}, {month}, {day})".format(**values)
        if mode == "time": return "datetime.time({hour}, {minute}, {second})".format(**values)
        if mode == "datetime": return "datetime.datetime({year}, {month}, {day}, {hour}, {minute}, {second})".format(**values)
        return "None"
    if key == "datetime_parts":
        return f"getattr({a('value')}, {port!r}, 0)"
    if key == "datetime_shift":
        return f"({a('value')} + datetime.timedelta(days={a('days','0')}, hours={a('hours','0')}, minutes={a('minutes','0')}))"
    if key == "datetime_difference":
        delta = f"({a('end_value')} - {a('start_value')})"
        return {"duration": delta, "days": f"({delta}.total_seconds() / 86400)", "seconds": f"{delta}.total_seconds()"}.get(port, "None")
    if key == "datetime_format":
        value = a("value", "''")
        fmt = repr(str(cfg.get("date_format") or "%d/%m/%Y %H:%M:%S"))
        if mode == "date_to_text": return f"{value}.strftime({fmt})"
        if mode == "text_to_date": return f"datetime.datetime.strptime({value}, {fmt})"
        return "None"
    value = a("value")
    return f"({value}.weekday() + 1)" if port == "number" else f"{WEEKDAYS!r}[{value}.weekday()]"


BLOCK_HELPERS = {}
HELPERS = {}
