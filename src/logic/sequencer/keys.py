"""Tasten-Parsing für pynput (inkl. Kombinationen wie alt+z)."""

from pynput.keyboard import Key

KEY_MAP = {
    "space": Key.space,
    "enter": Key.enter,
    "tab": Key.tab,
    "esc": Key.esc,
    "escape": Key.esc,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "shift": Key.shift,
    "ctrl": Key.ctrl,
    "control": Key.ctrl,
    "alt": Key.alt,
    "win": Key.cmd,
    "cmd": Key.cmd,
}


def parse_key(key_str: str):
    if not key_str:
        return None
    k = key_str.strip().lower()
    if k in KEY_MAP:
        return KEY_MAP[k]
    if len(k) == 1:
        return k
    if k.startswith("f") and k[1:].isdigit():
        fn = getattr(Key, k, None)
        if fn:
            return fn
    return None


def parse_combo(key_str: str) -> list:
    """z.B. 'alt+z' oder 'ctrl+shift+a' → Liste von Keys."""
    if not key_str or not str(key_str).strip():
        return []
    parts = [p.strip().lower() for p in str(key_str).split("+") if p.strip()]
    keys = []
    for p in parts:
        k = parse_key(p)
        if k is not None:
            keys.append(k)
    return keys


def combo_label(key_str: str) -> str:
    if not key_str:
        return "?"
    return "+".join(p.strip().upper() if len(p.strip()) == 1 else p.strip().title() for p in key_str.split("+"))
