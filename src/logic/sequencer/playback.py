"""Sequenz-Wiedergabe mit Loop-Modi und erweiterten Blöcken."""

from __future__ import annotations

import time
import ctypes
from typing import Callable

from src.logic.sequencer.input_actions import block_events, perform_mouse_block, release_combo
from pynput.keyboard import Controller as KeyboardController
from pynput.mouse import Controller as MouseController

# Windows-spezifische High-Resolution Timer Unterstützung
_winmm = None
if __import__("sys").platform == "win32":
    try:
        _winmm = ctypes.WinDLL("winmm")
    except Exception:
        pass


def _set_precision_timer(enable: bool):
    """Setzt die Windows-Timer-Auflösung auf 1ms für genaueres sleep()."""
    if _winmm:
        try:
            if enable:
                _winmm.timeBeginPeriod(1)
            else:
                _winmm.timeEndPeriod(1)
        except Exception:
            pass


class PlaybackEngine:
    def __init__(self, death_check: Callable[[], bool] | None = None, stones_check: Callable[[str], bool] | None = None):
        self._lock = __import__("threading").Lock()
        self._playing = False
        self._position_ms = 0.0
        self._start_wall = 0.0
        self._pause_at_ms = 0.0
        self._thread = None
        self._keyboard = KeyboardController()
        self._mouse = MouseController()
        self._death_check = death_check
        self._stones_check = stones_check
        self._held_keys = set()

    def is_playing(self) -> bool:
        with self._lock:
            return self._playing

    def get_position_ms(self) -> float:
        with self._lock:
            if self._playing:
                return self._pause_at_ms + (time.perf_counter() - self._start_wall) * 1000
            return self._position_ms

    def seek(self, ms: float):
        with self._lock:
            self._position_ms = max(0.0, ms)
            if self._playing:
                self._pause_at_ms = self._position_ms
                self._start_wall = time.perf_counter()

    def reset(self):
        self.stop()
        with self._lock:
            self._position_ms = 0.0
            self._pause_at_ms = 0.0

    def stop(self):
        with self._lock:
            self._playing = False
        if self._thread:
            self._thread.join(timeout=3.0)
        with self._lock:
            self._position_ms = self._pause_at_ms
            # Alle noch gehaltenen Tasten loslassen
            if self._held_keys:
                release_combo(list(self._held_keys), self._keyboard)
                self._held_keys.clear()

    def play(self, blocks: list[dict], from_ms: float = 0.0, options: dict | None = None):
        self.stop()
        options = options or {}
        with self._lock:
            self._pause_at_ms = from_ms
            self._position_ms = from_ms
            self._playing = True
            self._start_wall = time.perf_counter()

        # Timer-Präzision für die Dauer der Wiedergabe erhöhen
        _set_precision_timer(True)

        self._thread = __import__("threading").Thread(
            target=self._run_looped,
            args=(blocks, from_ms, options),
            daemon=True,
        )
        self._thread.start()

    def _should_stop_loop(self, options: dict, run_index: int, loop_start: float) -> bool:
        mode = options.get("mode", "once")
        stop_cond = options.get("stopCondition", "none")

        if mode == "once":
            return run_index >= 1
        if mode == "count":
            return run_index >= int(options.get("count", 1))
        if mode == "minutes":
            elapsed = (time.perf_counter() - loop_start) / 60.0
            return elapsed >= float(options.get("minutes", 1))
        
        # Check stop conditions (either from mode or from stopCondition)
        if mode == "untilDeath" or stop_cond == "untilDeath":
            if self._death_check and self._death_check():
                return True
        if mode == "hpStonesEmpty" or stop_cond == "hpStonesEmpty":
            if self._stones_check and self._stones_check("hp"):
                return True
        if mode == "mpStonesEmpty" or stop_cond == "mpStonesEmpty":
            if self._stones_check and self._stones_check("mp"):
                return True
        
        if mode == "loop":
            return False
            
        return run_index >= 1

    def _run_looped(self, blocks: list[dict], from_ms: float, options: dict):
        run_index = 0
        loop_start = time.perf_counter()
        current_from = from_ms

        while True:
            with self._lock:
                if not self._playing:
                    _set_precision_timer(False)
                    return

            self._run_once(blocks, current_from, options)
            run_index += 1
            current_from = 0.0

            with self._lock:
                if not self._playing:
                    _set_precision_timer(False)
                    return

            if self._should_stop_loop(options, run_index, loop_start):
                # Teleport-Taste drücken falls konfiguriert
                tp_key = options.get("teleportKey")
                if tp_key:
                    try:
                        self._keyboard.press(tp_key)
                        time.sleep(0.1)
                        self._keyboard.release(tp_key)
                    except Exception:
                        pass
                break

            with self._lock:
                self._pause_at_ms = 0.0
                self._position_ms = 0.0
                self._start_wall = time.perf_counter()

        with self._lock:
            self._playing = False
            self._position_ms = 0.0
            self._pause_at_ms = 0.0
        
        _set_precision_timer(False)

    def _run_once(self, blocks: list[dict], from_ms: float, options: dict | None = None):
        options = options or {}
        events: list[tuple[float, str, object]] = []
        for b in blocks:
            events.extend(block_events(b, from_ms))

        events.sort(key=lambda e: e[0])

        end_time = max(
            (float(b.get("startMs", 0)) + float(b.get("durationMs", 0)) for b in blocks),
            default=from_ms,
        )

        for t_ms, action, payload in events:
            if not self._wait_until(t_ms):
                with self._lock:
                    self._release_held(list(self._held_keys))
                return

            with self._lock:
                if not self._playing:
                    self._release_held(list(self._held_keys))
                    return

            # Check stones/death inside the event loop for immediate stop
            if self._death_check and self._death_check():
                with self._lock: self._playing = False
                return
            
            mode = options.get("mode")
            stop_cond = options.get("stopCondition", "none")
            if (mode == "hpStonesEmpty" or stop_cond == "hpStonesEmpty") and self._stones_check and self._stones_check("hp"):
                with self._lock: self._playing = False
                return
            if (mode == "mpStonesEmpty" or stop_cond == "mpStonesEmpty") and self._stones_check and self._stones_check("mp"):
                with self._lock: self._playing = False
                return

            try:
                if action == "keydown":
                    for k in payload:
                        self._keyboard.press(k)
                    with self._lock:
                        for k in payload:
                            self._held_keys.add(k)
                elif action == "keyup":
                    release_combo(payload, self._keyboard)
                    with self._lock:
                        for k in payload:
                            if k in self._held_keys:
                                self._held_keys.remove(k)
                elif action == "mouse":
                    perform_mouse_block(payload, self._mouse)
            except Exception:
                pass

        while True:
            with self._lock:
                if not self._playing:
                    break
                now_ms = self._pause_at_ms + (time.perf_counter() - self._start_wall) * 1000
            if now_ms >= end_time:
                break
            if self._death_check and self._death_check():
                with self._lock:
                    self._playing = False
                break
            time.sleep(0.02)

        with self._lock:
            self._release_held(list(self._held_keys))
        with self._lock:
            self._position_ms = end_time
            self._pause_at_ms = end_time

    def _wait_until(self, t_ms: float) -> bool:
        while True:
            with self._lock:
                if not self._playing:
                    return False
                now_ms = self._pause_at_ms + (time.perf_counter() - self._start_wall) * 1000
            
            wait_ms = t_ms - now_ms
            if wait_ms <= 0:
                return True
            
            # Strategie für präzises Warten:
            if wait_ms > 15:
                # Mehr als ein Standard-Tick: Normaler sleep (der durch timeBeginPeriod nun 1ms genau ist)
                time.sleep(min(0.01, wait_ms / 1000.0))
            elif wait_ms > 1:
                # Nah dran: Minimaler sleep
                time.sleep(0.001)
            else:
                # Extrem nah dran (<1ms): "Busy wait" für maximale Präzision
                pass

    def _release_held(self, held_keys: list):
        release_combo(held_keys, self._keyboard)
        self._held_keys.clear()
