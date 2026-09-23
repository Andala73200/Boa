from boa.i18n import tr


def block_actions() -> list[tuple[str, str, str]]:
    return [
        (tr("action.add_if"), "if", "Ctrl+1"), (tr("action.add_tp"), "tp", "Ctrl+T"),
        (tr("action.add_and"), "and", "Ctrl+Alt+1"),
        (tr("action.add_or"), "or", "Ctrl+Alt+2"),
        (tr("action.add_not"), "not", "Ctrl+Alt+3"),
        (tr("action.add_xor"), "xor", "Ctrl+Alt+4"),
        (tr("action.add_while"), "while", "Ctrl+2"),
        (tr("action.add_for"), "for", "Ctrl+3"),
        (tr("action.add_call"), "call", "Ctrl+9"), (tr("action.add_print"), "print", "Ctrl+5"),
        (tr("action.add_input"), "input", "Ctrl+7"), (tr("action.add_value"), "value", "Ctrl+8"),
        (tr("action.add_empty"), "empty", "Ctrl+6"),
    ]
