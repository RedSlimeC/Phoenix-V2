"""Maus, Tastatur-Kombos und Bildschirm-Positionsauswahl."""

from __future__ import annotations

from typing import Any

import time

from src.logic.sequencer.keys import parse_combo, parse_key
from pynput.keyboard import Controller as KeyboardController
from pynput.mouse import Button, Controller as MouseController


def pick_screen_point(hint: str = "Klicke Zielposition · ESC = Abbrechen") -> dict | None:
    import tkinter as tk

    result: dict | None = None

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.25)
    root.configure(cursor="crosshair", bg="#000022")

    lbl = tk.Label(
        root,
        text=hint,
        font=("Segoe UI", 16),
        fg="#e8b923",
        bg="#111118",
        padx=20,
        pady=10,
    )
    lbl.place(relx=0.5, y=40, anchor="n")

    def on_click(e):
        nonlocal result
        result = {"x": int(e.x_root), "y": int(e.y_root)}
        root.quit()

    def on_esc(_e=None):
        root.quit()

    root.bind("<ButtonRelease-1>", on_click)
    root.bind("<Escape>", on_esc)
    root.mainloop()
    try:
        root.destroy()
    except Exception:
        pass
    return result


def is_mouse_block(block: dict) -> bool:
    """Nur echter Maus-Typ – keyboard-Blöcke haben oft mouseButton aus dem Standard-Template."""
    t = block.get("type")
    if t == "mouse":
        return True
    if t == "keyboard":
        return False
    return block.get("clickX") is not None and block.get("clickY") is not None


def perform_mouse_block(block: dict, mouse: MouseController):
    x = block.get("clickX")
    y = block.get("clickY")
    if x is None or y is None:
        return
    btn = Button.left if block.get("mouseButton", "left") == "left" else Button.right
    count = 2 if block.get("doubleClick") else 1
    
    # Position mouse and wait slightly to ensure focus/detection
    mouse.position = (int(x), int(y))
    time.sleep(0.05) 
    
    mouse.click(btn, count)


def press_combo(key_str: str, keyboard: KeyboardController) -> list:
    keys = parse_combo(key_str)
    for k in keys:
        keyboard.press(k)
    return keys


def release_combo(keys: list, keyboard: KeyboardController):
    for k in reversed(keys):
        try:
            keyboard.release(k)
        except Exception:
            pass


def tap_key_once(key_str: str, hold_ms: float = 0.05, keyboard: KeyboardController | None = None) -> None:
    kb = keyboard or KeyboardController()
    keys = press_combo(key_str, kb)
    time.sleep(max(0.03, hold_ms))
    release_combo(keys, kb)


def tap_space_once(hold_ms: float = 0.05, keyboard: KeyboardController | None = None) -> None:
    kb = keyboard or KeyboardController()
    keys = press_combo("space", kb)
    time.sleep(max(0.03, hold_ms))
    release_combo(keys, kb)


def tap_space_repeated(count: int, interval_ms: int = 100, keyboard: KeyboardController | None = None) -> None:
    interval = max(0.05, int(interval_ms) / 1000.0)
    for _ in range(max(0, int(count))):
        tap_space_once(0.05, keyboard)
        time.sleep(interval)


def mouse_click_at(
    mouse: MouseController,
    x: int,
    y: int,
    *,
    double: bool = False,
    button: Button = Button.left,
) -> None:
    mouse.position = (int(x), int(y))
    time.sleep(0.1) # Etwas mehr Zeit für die Positionierung
    
    def _single_click():
        mouse.press(button)
        time.sleep(0.05) # Kurzes Halten der Taste
        mouse.release(button)

    if double:
        _single_click()
        time.sleep(0.15) # Etwas längeres Intervall für Doppelklick
        _single_click()
    else:
        _single_click()


def block_events(block: dict, from_ms: float) -> list[tuple[float, str, Any]]:
    """Erzeugt zeitgesteuerte Events: (ms, action, payload)."""
    start = float(block.get("startMs", 0))
    dur = float(block.get("durationMs", 100))
    end = start + dur
    if end <= from_ms:
        return []

    events: list[tuple[float, str, Any]] = []

    if is_mouse_block(block):
        t = max(start, from_ms)
        events.append((t, "mouse", block))
        return events

    keys = parse_combo(block.get("key", ""))
    if not keys:
        return []

    if start >= from_ms:
        events.append((start, "keydown", keys))
    else:
        events.append((from_ms, "keydown", keys))
    events.append((end, "keyup", keys))
    return events
