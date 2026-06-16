"""Globale Tastenkürzel (pynput), auch wenn ein anderes Fenster fokussiert ist."""

from __future__ import annotations

from pynput import keyboard

MODIFIER_ALIASES = {
    "ctrl_l": "ctrl",
    "ctrl_r": "ctrl",
    "control_l": "ctrl",
    "control_r": "ctrl",
    "alt_l": "alt",
    "alt_r": "alt",
    "alt_gr": "alt",
    "shift_l": "shift",
    "shift_r": "shift",
    "cmd": "win",
    "cmd_r": "win",
}

MODIFIER_ORDER = ("ctrl", "alt", "shift", "win")


def _key_to_name(key) -> str | None:
    if key is None:
        return None
    if hasattr(key, "char") and key.char:
        return key.char.lower()
    name = getattr(key, "name", None)
    if name:
        return str(name).lower()
    return None


def _normalize_name(name: str | None) -> str | None:
    if not name:
        return None
    n = name.lower()
    return MODIFIER_ALIASES.get(n, n)


def _chord_string(parts: set[str]) -> str:
    mods = [m for m in MODIFIER_ORDER if m in parts]
    rest = sorted(p for p in parts if p not in MODIFIER_ORDER)
    return "+".join(mods + rest)


def _normalize_combo(combo: str) -> str:
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    mods = [m for m in MODIFIER_ORDER if m in parts]
    rest = sorted(p for p in parts if p not in MODIFIER_ORDER)
    return "+".join(mods + rest)


class GlobalHotkeys:
    def __init__(
        self,
        on_reset_timeline,
        on_trigger_key_down=None,
        on_trigger_key_up=None,
    ):
        self._on_reset = on_reset_timeline
        self._on_trigger_key_down = on_trigger_key_down
        self._on_trigger_key_up = on_trigger_key_up
        self._reset_binding = "f3"
        self._trigger_keys: set[str] = set()
        self._pressed: set[str] = set()
        self._fired_triggers: set[str] = set()
        self._listener: keyboard.Listener | None = None

    def set_bindings(
        self,
        reset: str,
    ) -> None:
        self._reset_binding = (reset or "f3").strip().lower()

    def set_trigger_keys(self, keys: list[str]) -> None:
        self._trigger_keys = {_normalize_combo(k) for k in keys if k and k.strip()}

    def get_bindings(self) -> dict:
        return {
            "resetTimeline": self._reset_binding,
        }

    def _on_press(self, key):
        name = _normalize_name(_key_to_name(key))
        if not name:
            return
        self._pressed.add(name)
        chord = _chord_string(self._pressed)

        if name == self._reset_binding:
            self._on_reset()
        elif (
            chord in self._trigger_keys
            and chord not in self._fired_triggers
            and self._on_trigger_key_down
        ):
            self._fired_triggers.add(chord)
            self._on_trigger_key_down(chord)

    def _on_release(self, key):
        name = _normalize_name(_key_to_name(key))
        if not name:
            return
        self._pressed.discard(name)
        for combo in list(self._fired_triggers):
            if name in combo.split("+"):
                self._fired_triggers.discard(combo)
        if name in self._trigger_keys and self._on_trigger_key_up:
            self._on_trigger_key_up(name)

    def start(self) -> None:
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None
