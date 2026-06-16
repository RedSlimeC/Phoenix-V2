import json
from pathlib import Path
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

STATIC_DIR = Path(__file__).parent / "sequencer_static"
PROFILES_DIR = Path(__file__).resolve().parents[2] / "profiles"
PROFILES_DIR.mkdir(exist_ok=True)


class SequencerApi(QObject):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self._window = None

    def set_window(self, window):
        self._window = window
        self.manager.set_window(window)

    @pyqtSlot(str, result=str)
    def set_keybindings(self, reset: str):
        result = self.manager.set_keybindings(reset)
        return json.dumps(result)

    @pyqtSlot(str, result=str)
    def set_sequence_trigger_keys(self, keys_payload: str):
        keys = json.loads(keys_payload)
        result = self.manager.set_sequence_trigger_keys(keys)
        return json.dumps(result)

    @pyqtSlot(str, str, result=str)
    def save_profile_disk(self, name: str, data_json: str):
        try:
            path = PROFILES_DIR / f"{name}.json"
            with open(path, "w", encoding="utf-8") as f:
                f.write(data_json)
            return json.dumps({"ok": True})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    @pyqtSlot(str, result=str)
    def load_profile_disk(self, name: str):
        try:
            path = PROFILES_DIR / f"{name}.json"
            if not path.exists():
                return json.dumps({"ok": False, "error": "file_not_found"})
            with open(path, "r", encoding="utf-8") as f:
                return json.dumps({"ok": True, "data": f.read()})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    @pyqtSlot(result=str)
    def list_profiles(self):
        try:
            names = [f.stem for f in PROFILES_DIR.glob("*.json")]
            return json.dumps({"ok": True, "profiles": names})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    @pyqtSlot(result=str)
    def get_profiles_dir(self):
        return json.dumps({"path": str(PROFILES_DIR.absolute())})

    @pyqtSlot(str, str, result=str)
    def delete_profile_disk(self, id: str, name: str):
        try:
            for f in PROFILES_DIR.glob("*.json"):
                if f.stem == id or f.stem == name:
                    f.unlink()
            return json.dumps({"ok": True})
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)})

    @pyqtSlot(str, float, str, result=str)
    def play_sequence(self, blocks_json: str, from_ms: float = 0.0, options_json: str = "{}"):
        blocks = json.loads(blocks_json)
        options = json.loads(options_json)
        result = self.manager.play(blocks, from_ms, options)
        return json.dumps(result)

    @pyqtSlot(result=str)
    def stop_playback(self):
        result = self.manager.stop()
        return json.dumps(result)

    @pyqtSlot(result=str)
    def reset_playback(self):
        result = self.manager.reset()
        return json.dumps(result)

    @pyqtSlot(result=str)
    def get_playhead_ms(self):
        result = self.manager.get_playhead()
        return json.dumps(result)

    @pyqtSlot(float, result=str)
    def seek_playhead(self, ms: float):
        result = self.manager.seek(ms)
        return json.dumps(result)

    @pyqtSlot()
    def close_app(self):
        if self._window:
            try:
                self._window.hide()
            except Exception:
                pass

    @pyqtSlot(result=str)
    def pick_click_position(self):
        self._hide_main_for_picker()
        try:
            from src.logic.sequencer.input_actions import pick_screen_point
            pt = pick_screen_point("Pick click position · ESC = Cancel")
            return json.dumps({"ok": pt is not None, "point": pt})
        finally:
            self._show_main_after_picker()

    def _hide_main_for_picker(self):
        if self._window:
            try:
                self._window.hide()
            except Exception:
                pass

    def _show_main_after_picker(self):
        if self._window:
            try:
                self._window.show()
            except Exception:
                pass


class SequencerWindow(QMainWindow):
    eval_js_signal = pyqtSignal(str)

    def __init__(self, manager, always_on_top=True):
        super().__init__()
        self.manager = manager
        self.setWindowTitle("Phoenix Sequencer")
        self.setFixedSize(600, 600)
        self.drag_pos = None
        
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        if always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(central_widget)

        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

        self.api = SequencerApi(manager)
        self.api.set_window(self)

        self.channel = QWebChannel()
        self.channel.registerObject("pywebview.api", self.api)
        self.web_view.page().setWebChannel(self.channel)

        html_path = STATIC_DIR / "sequencer.html"
        self.web_view.setUrl(QUrl.fromLocalFile(str(html_path.absolute())))

        self.eval_js_signal.connect(self._evaluate_js)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_pos:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        super().mouseReleaseEvent(event)

    def evaluate_js(self, code):
        """Thread-safe JS evaluation."""
        self.eval_js_signal.emit(code)

    def _evaluate_js(self, code):
        self.web_view.page().runJavaScript(code)


class SequencerWindowManager(QObject):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.window = None

    def open_window(self, always_on_top=True):
        if self.window is None:
            self.window = SequencerWindow(self.manager, always_on_top=always_on_top)
        
        # Ensure manager is enabled when window is open
        self.manager.set_enabled(True)
        
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        return {"ok": True}

    def destroy(self):
        if self.window:
            self.window.close()
            self.window = None
