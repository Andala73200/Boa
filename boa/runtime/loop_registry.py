LOOP_KEYS = {"while", "for"}


def next_loop_number(project: dict, key: str) -> int:
    numbers = [item["number"] for item in collect_loop_instances(project) if item["key"] == key]
    return max(numbers, default=0) + 1


def collect_loop_instances(project_or_graph: dict) -> list[dict]:
    result: list[dict] = []
    if isinstance(project_or_graph.get("graphs"), dict):
        for item in project_or_graph.get("graphs", {}).values(): _collect_from_graph(item.get("graph", {}), [], result)
        for item in project_or_graph.get("functions", {}).values(): _collect_from_graph(item.get("graph", {}), [], result)
    else:
        _collect_from_graph(project_or_graph.get("graph", project_or_graph) or {}, [], result)
    return result


def _collect_from_graph(graph: dict, path: list[str], result: list[dict]) -> None:
    for block in graph.get("blocks", []) or []:
        key = block.get("key", "")
        uid = block.get("id", "")
        next_path = path + [uid]
        if key in LOOP_KEYS and uid:
            number = int(block.get("loop_instance_number", 0) or 0)
            result.append({"key": key, "number": number, "path": next_path, "label": f"{key}#{number}", "depth": len(path)})
        _collect_from_graph(block.get("inner_graph", {}) or {}, next_path, result)


def graph_has_uid(graph: dict, uid: str) -> bool:
    return bool(find_block_data(graph, [uid]))


def find_block_data(graph: dict, path: list[str]) -> dict | None:
    if not path:
        return None
    current = graph or {}
    found = None
    for uid in path:
        found = next((b for b in current.get("blocks", []) or [] if b.get("id") == uid), None)
        if found is None:
            return None
        current = found.get("inner_graph", {}) or {}
    return found
