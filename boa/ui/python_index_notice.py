from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from boa.python_importer.call_index import block_title, index_change_report


def show_python_index_notice(parent) -> None:
    report = index_change_report()
    if not report:
        return
    language = str(getattr(parent, "preferences", {}).get("language", "fr"))
    if language == "en":
        title = "Python block index updated"
        text = _english_text(report)
    else:
        title = "Index Python mis à jour"
        text = _french_text(report)
    QMessageBox.information(parent, title, text)


def _french_text(report: dict) -> str:
    if report["first_run"]:
        lines = [
            "Le nouvel index Python → blocs Boa est activé.",
            f"{report['rule_count']} règle(s) pour {report['block_count']} bloc(s).",
        ]
    else:
        lines = ["L’index Python → blocs Boa a changé."]
    _append_changes(lines, report, "Ajoutés", "Retirés", "Règles modifiées")
    if report["errors"]:
        lines.append(f"Règles ignorées : {len(report['errors'])}")
    return "\n".join(lines)


def _english_text(report: dict) -> str:
    if report["first_run"]:
        lines = [
            "The new Python → Boa block index is enabled.",
            f"{report['rule_count']} rule(s) for {report['block_count']} block(s).",
        ]
    else:
        lines = ["The Python → Boa block index has changed."]
    _append_changes(lines, report, "Added", "Removed", "Changed rules")
    if report["errors"]:
        lines.append(f"Ignored rules: {len(report['errors'])}")
    return "\n".join(lines)


def _append_changes(lines: list[str], report: dict, added: str, removed: str, changed: str) -> None:
    if report["added"]:
        labels = [block_title(key) for key in report["added"]]
        lines.append(f"{added} : {_compact(labels)}")
    if report["removed"]:
        labels = [block_title(key) for key in report["removed"]]
        lines.append(f"{removed} : {_compact(labels)}")
    if report["changed_rules"]:
        lines.append(f"{changed} : {len(report['changed_rules'])}")


def _compact(values: list[str], limit: int = 8) -> str:
    shown = values[:limit]
    suffix = f" (+{len(values) - limit})" if len(values) > limit else ""
    return ", ".join(shown) + suffix
