def expression(block: dict, port: str, input_expr) -> str:
    key = str(block.get("key", ""))
    cfg = dict(block.get("module_config", {}) or {})
    mode = str(cfg.get("mode", ""))
    a = lambda name, default="None": input_expr(name, default)
    if key == "statistics_summary":
        values = a("values", "[]")
        return {"count": f"len({values})", "minimum": f"min({values})", "maximum": f"max({values})", "sum": f"sum({values})", "mean": f"statistics.mean({values})", "median": f"statistics.median({values})"}.get(port, "None")
    if key == "statistics_mean":
        values = a("values", "[]"); weights = a("weights", "[]")
        return {"arithmetic": f"statistics.mean({values})", "weighted": f"(sum(v*w for v, w in zip({values}, {weights})) / sum({weights}))", "geometric": f"statistics.geometric_mean({values})", "harmonic": f"statistics.harmonic_mean({values})"}.get(mode, "None")
    if key == "statistics_dispersion":
        values = a("values", "[]"); population = mode == "population"
        return f"statistics.{'pvariance' if population else 'variance'}({values})" if port == "variance" else f"statistics.{'pstdev' if population else 'stdev'}({values})"
    if key == "statistics_quantiles": return f"statistics.quantiles({a('values','[]')}, n={a('groups','4')}, method={str(cfg.get('method') or 'exclusive')!r})"
    first, second = a("first", "[]"), a("second", "[]")
    return {"covariance": f"statistics.covariance({first}, {second})", "correlation": f"statistics.correlation({first}, {second})", "slope": f"statistics.linear_regression({first}, {second}).slope", "intercept": f"statistics.linear_regression({first}, {second}).intercept"}.get(port, "None")


BLOCK_HELPERS = {}
HELPERS = {}
