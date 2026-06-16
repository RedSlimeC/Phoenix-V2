import threading
from src.logic.sequencer.playback import PlaybackEngine
from src.logic.sequencer.hotkeys import GlobalHotkeys
from src.logic.scanner import OFFSETS


class SequencerManager:
    def __init__(self, scanner):
        self.scanner = scanner
        self._lock = threading.Lock()
        self._scan_results = []
        self._active_index = 0
        self._enabled = False
        self._window = None

        self.engine = PlaybackEngine(
            death_check=self.is_character_dead,
            stones_check=self.are_stones_empty,
        )
        self._hotkeys = GlobalHotkeys(
            on_reset_timeline=self._hotkey_reset_timeline,
            on_trigger_key_down=self._hotkey_trigger_down,
            on_trigger_key_up=lambda _k: None,
        )
        self._hotkeys.start()

    def set_window(self, window):
        self._window = window

    def set_enabled(self, enabled: bool):
        with self._lock:
            self._enabled = enabled
        if not enabled:
            self.engine.stop()

    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def update_scan_data(self, results, active_index=0):
        with self._lock:
            self._scan_results = list(results or [])
            self._active_index = active_index

    def _get_active_data(self):
        with self._lock:
            if not self._scan_results:
                return None
            idx = min(max(self._active_index, 0), len(self._scan_results) - 1)
            return self._scan_results[idx]

    def _read_live_value(self, field: str):
        data = self._get_active_data()
        if not data:
            return None
        pid = data.get("pid")
        p_base_str = data.get("p_base")
        if not pid or not p_base_str:
            return None
        try:
            p_base = int(p_base_str, 16)
        except (TypeError, ValueError):
            return None
        h = self.scanner.open_process(pid)
        if not h:
            return None
        try:
            if field == "hp":
                return self.scanner.read_i32(h, p_base + OFFSETS["CURRENT_HP"])
            if field == "hp_stone":
                return self.scanner.read_u16(h, p_base + OFFSETS["HP_STONE"])
            if field == "mp_stone":
                return self.scanner.read_u16(h, p_base + OFFSETS["MP_STONE"])
        finally:
            self.scanner.kernel32.CloseHandle(h)
        return None

    def is_character_dead(self) -> bool:
        hp = self._read_live_value("hp")
        if hp is not None:
            return hp <= 0
        data = self._get_active_data()
        if not data:
            return False
        try:
            return int(data.get("hp", 0)) <= 0
        except (TypeError, ValueError):
            return False

    def are_stones_empty(self, stone_type: str) -> bool:
        field = "hp_stone" if stone_type == "hp" else "mp_stone"
        count = self._read_live_value(field)
        if count is not None:
            return count <= 0
        data = self._get_active_data()
        if not data:
            return False
        try:
            return int(data.get(field, 0)) <= 0
        except (TypeError, ValueError):
            return False

    def play(self, blocks, from_ms=0.0, options=None):
        if not self.is_enabled():
            return {"ok": False, "error": "sequencer_disabled"}
        self.engine.play(blocks, from_ms, options or {})
        return {"ok": True}

    def stop(self):
        self.engine.stop()
        return {"ok": True, "positionMs": self.engine.get_position_ms()}

    def reset(self):
        self.engine.reset()
        return {"ok": True, "positionMs": 0.0}

    def get_playhead(self):
        return {
            "positionMs": self.engine.get_position_ms(),
            "playing": self.engine.is_playing(),
        }

    def seek(self, ms: float):
        self.engine.seek(ms)
        return {"positionMs": self.engine.get_position_ms()}

    def set_keybindings(self, reset: str):
        self._hotkeys.set_bindings(reset)
        return {"ok": True}

    def set_sequence_trigger_keys(self, keys):
        if not isinstance(keys, list):
            keys = []
        self._hotkeys.set_trigger_keys(keys)
        return {"ok": True}

    def _broadcast_js(self, code: str):
        if self._window:
            try:
                self._window.evaluate_js(code)
            except Exception:
                pass

    def _hotkey_reset_timeline(self):
        if not self.is_enabled():
            return
        self.reset()
        self._broadcast_js("window.FiestaApp && window.FiestaApp.resetTimeline()")

    def _hotkey_trigger_down(self, key):
        if not self.is_enabled():
            return
        import json
        key_js = json.dumps(str(key))
        self._broadcast_js(
            f"window.FiestaHotkeys && window.FiestaHotkeys.triggerKeyDown({key_js})"
        )

    def stop_hotkeys(self):
        self._hotkeys.stop()
