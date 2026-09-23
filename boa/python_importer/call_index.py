from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from boa.core.module_registry import MODULE_SPECS
from boa.core.module_specs import resolved_module_ports
from boa.core.preferences import CONFIG_DIR

STATE_FILE = CONFIG_DIR / "python_call_index.json"


@dataclass(frozen=True, slots=True)
class CallRule:
    rule_id: str
    block_key: str
    kind: str
    names: tuple[str, ...]
    priority: int
    min_args: int
    max_args: int
    arg_ports: tuple[str, ...]
    receiver_port: str
    keyword_ports: dict[str, str]
    config_keywords: dict[str, str]
    dynamic_keywords: dict
    type_argument: dict
    config: dict
    result_port: str


@dataclass(frozen=True, slots=True)
class CallMatch:
    rule: CallRule
    inputs: tuple[tuple[str, ast.AST], ...]
    config: dict


@dataclass(frozen=True, slots=True)
class CallIndex:
    rules: tuple[CallRule, ...]
    errors: tuple[str, ...]
    signature: str

    def match(self, node: ast.Call) -> CallMatch | None:
        for rule in self.rules:
            match = _match_rule(rule, node)
            if match is not None:
                return match
        return None

    @property
    def block_keys(self) -> tuple[str, ...]:
        return tuple(sorted({rule.block_key for rule in self.rules}))


@lru_cache(maxsize=1)
def get_call_index() -> CallIndex:
    rules: list[CallRule] = []
    errors: list[str] = []
    seen: set[str] = set()
    payloads: list[dict] = []
    for path in _manifest_paths():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{path.name}: {error}")
            continue
        for raw in data.get("rules", []) if isinstance(data, dict) else []:
            try:
                rule = _parse_rule(raw)
                if rule.rule_id in seen:
                    raise ValueError(f"identifiant dupliqué {rule.rule_id}")
                seen.add(rule.rule_id)
                rules.append(rule)
                payloads.append(raw)
            except (TypeError, ValueError) as error:
                errors.append(f"{path.name}: {error}")
    rules.sort(key=lambda item: (-item.priority, item.rule_id))
    canonical = json.dumps(payloads, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    signature = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return CallIndex(tuple(rules), tuple(errors), signature)


def index_change_report() -> dict | None:
    index = get_call_index()
    current = {
        "signature": index.signature,
        "blocks": list(index.block_keys),
        "rules": {rule.rule_id: _rule_digest(rule) for rule in index.rules},
        "errors": list(index.errors),
    }
    previous = _read_state()
    if previous == current:
        return None
    old_blocks = set(previous.get("blocks", [])) if previous else set()
    new_blocks = set(current["blocks"])
    old_rules = dict(previous.get("rules", {})) if previous else {}
    changed = [key for key, value in current["rules"].items() if key in old_rules and old_rules[key] != value]
    report = {
        "first_run": not bool(previous),
        "rule_count": len(index.rules),
        "block_count": len(new_blocks),
        "added": sorted(new_blocks - old_blocks),
        "removed": sorted(old_blocks - new_blocks),
        "changed_rules": sorted(changed),
        "errors": list(index.errors),
    }
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def block_title(block_key: str) -> str:
    spec = MODULE_SPECS.get(block_key)
    return str(getattr(spec, "title", block_key))


def _manifest_paths() -> list[Path]:
    importer_dir = Path(__file__).resolve().parent
    module_dir = importer_dir.parent / "modules"
    paths = list((importer_dir / "indexes").glob("*.json"))
    paths.extend(module_dir.glob("*/python_index.json"))
    return sorted(path.resolve() for path in paths if path.is_file())


def _parse_rule(raw: dict) -> CallRule:
    if not isinstance(raw, dict):
        raise ValueError("règle JSON invalide")
    block_key = str(raw.get("block", ""))
    if block_key not in MODULE_SPECS:
        raise ValueError(f"bloc inconnu {block_key!r}")
    kind = str(raw.get("kind", "function"))
    if kind not in {"function", "method"}:
        raise ValueError(f"type de règle invalide {kind!r}")
    names = tuple(str(item) for item in raw.get("names", []) if str(item))
    if not names:
        raise ValueError("règle sans nom Python")
    arg_ports = tuple(str(item) for item in raw.get("arg_ports", []))
    min_args = int(raw.get("min_args", len(arg_ports)))
    max_args = int(raw.get("max_args", len(arg_ports)))
    rule = CallRule(
        str(raw.get("id", "")), block_key, kind, names,
        int(raw.get("priority", 100)), min_args, max_args, arg_ports,
        str(raw.get("receiver_port", "")),
        {str(k): str(v) for k, v in dict(raw.get("keyword_ports", {})).items()},
        {str(k): str(v) for k, v in dict(raw.get("config_keywords", {})).items()},
        dict(raw.get("dynamic_keywords", {})),
        dict(raw.get("type_argument", {})), dict(raw.get("config", {})),
        str(raw.get("result_port", "result")),
    )
    if not rule.rule_id:
        raise ValueError("règle sans identifiant")
    _validate_ports(rule)
    return rule


def _validate_ports(rule: CallRule) -> None:
    spec = MODULE_SPECS[rule.block_key]
    config = dict(rule.config)
    if rule.type_argument:
        allowed = list(rule.type_argument.get("allowed", []))
        if allowed:
            config[str(rule.type_argument.get("config", "mode"))] = str(allowed[0])
    inputs, outputs = resolved_module_ports(spec, config)
    input_keys = {port.key for port in inputs}
    output_keys = {port.key for port in outputs}
    requested = set(rule.arg_ports) | set(rule.keyword_ports.values())
    if rule.dynamic_keywords:
        prefix = str(rule.dynamic_keywords.get("port_prefix", "value_"))
        maximum = int(rule.dynamic_keywords.get("max", 0))
        requested.update(f"{prefix}{index}" for index in range(1, maximum + 1))
    if rule.receiver_port:
        requested.add(rule.receiver_port)
    unknown = requested - input_keys
    if unknown:
        raise ValueError(f"ports inconnus pour {rule.block_key}: {', '.join(sorted(unknown))}")
    if rule.result_port not in output_keys:
        raise ValueError(f"sortie inconnue {rule.result_port!r} pour {rule.block_key}")


def _match_rule(rule: CallRule, node: ast.Call) -> CallMatch | None:
    if any(isinstance(arg, ast.Starred) for arg in node.args) or any(item.arg is None for item in node.keywords):
        return None
    receiver = None
    if rule.kind == "function":
        if _target_name(node.func) not in rule.names:
            return None
    else:
        if not isinstance(node.func, ast.Attribute) or node.func.attr not in rule.names:
            return None
        receiver = node.func.value
    if not rule.min_args <= len(node.args) <= rule.max_args:
        return None
    config = dict(rule.config)
    skipped_index = -1
    type_arg = rule.type_argument
    if type_arg:
        skipped_index = int(type_arg.get("index", -1))
        if not 0 <= skipped_index < len(node.args):
            return None
        value = _target_name(node.args[skipped_index])
        allowed = {str(item) for item in type_arg.get("allowed", [])}
        if value not in allowed:
            return None
        config[str(type_arg.get("config", "mode"))] = value
    values = [arg for index, arg in enumerate(node.args) if index != skipped_index]
    if len(values) > len(rule.arg_ports):
        return None
    inputs: list[tuple[str, ast.AST]] = []
    if receiver is not None:
        inputs.append((rule.receiver_port, receiver))
    inputs.extend((rule.arg_ports[index], value) for index, value in enumerate(values))
    dynamic = dict(rule.dynamic_keywords)
    dynamic_items: list[ast.keyword] = []
    for keyword in node.keywords:
        name = str(keyword.arg)
        if name in rule.keyword_ports:
            inputs.append((rule.keyword_ports[name], keyword.value))
        elif name in rule.config_keywords and isinstance(keyword.value, ast.Constant):
            config[rule.config_keywords[name]] = keyword.value.value
        elif dynamic:
            dynamic_items.append(keyword)
        else:
            return None
    if dynamic_items:
        maximum = int(dynamic.get("max", 0))
        if maximum <= 0 or len(dynamic_items) > maximum:
            return None
        prefix = str(dynamic.get("port_prefix", "value_"))
        names = [str(item.arg) for item in dynamic_items]
        config[str(dynamic.get("config", "keys"))] = names
        enabled = [f"{prefix}{index}" for index in range(1, len(dynamic_items) + 1)]
        config["_enabled_inputs"] = enabled
        inputs.extend((enabled[index], item.value) for index, item in enumerate(dynamic_items))
    elif dynamic:
        config[str(dynamic.get("config", "keys"))] = []
        config["_enabled_inputs"] = []
    ports = [port for port, _value in inputs]
    if len(ports) != len(set(ports)):
        return None
    return CallMatch(rule, tuple(inputs), config)


def _target_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _target_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _rule_digest(rule: CallRule) -> str:
    return hashlib.sha256(repr(rule).encode("utf-8")).hexdigest()


def _read_state() -> dict:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}
