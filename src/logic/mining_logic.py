import threading
import time
import mss
import ctypes
from PIL import Image
from pynput.mouse import Button, Controller as MouseController
from ctypes import wintypes

class MiningManager:
    def __init__(self, db, user_id):
        self.db = db
        self.user_id = user_id
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._mouse = MouseController()
        self._sessions = {} # pid -> { "last_click": float, "is_mining": bool }
        self.user32 = ctypes.windll.user32

    def start(self):
        with self._lock:
            if self._running: return
            self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        with self._lock:
            self._running = False

    def _get_foreground_pid(self):
        foreground_hwnd = self.user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(foreground_hwnd, ctypes.byref(pid))
        return pid.value, foreground_hwnd

    def _loop(self):
        while True:
            with self._lock:
                if not self._running: break

            settings = self.db.get_mining_settings(self.user_id)
            if settings and settings.get("enabled"):
                pid, hwnd = self._get_foreground_pid()
                # Check if foreground process is Fiesta.exe (simplified for now)
                # In main_view we have results, but logic runs in thread. 
                # We'll assume the user is in the game if they enable it.
                
                region = settings.get("region")
                if region:
                    try:
                        self._process_mining(pid, hwnd, settings)
                    except Exception as e:
                        print(f"[Mining] Error: {e}")

            time.sleep(0.03) # ~33 FPS

    def _process_mining(self, pid, hwnd, cfg):
        region = cfg["region"]
        delay_ms = cfg.get("delay_ms", 0)
        tolerance = 75
        
        if pid not in self._sessions:
            self._sessions[pid] = {"last_click": 0, "is_mining": False}
        session = self._sessions[pid]

        # Grab region
        with mss.mss() as sct:
            mon = {
                "left": int(region["left"]),
                "top": int(region["top"]),
                "width": int(region["width"]),
                "height": int(region["height"]),
            }
            shot = sct.grab(mon)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            
        pixels = img.load()
        width, height = img.size
        mid_y = height // 2
        
        rail_pixels = []
        yellow_pixels = []
        green_pixels = []
        
        r_threshold = 160 + (tolerance - 50)
        g_threshold = 140 + (tolerance - 50)
        b_threshold = 120 - (tolerance - 50)
        
        for x in range(width):
            r, g, b = pixels[x, mid_y]
            if r < 100 and g < 100 and b < 100: rail_pixels.append(x)
            if r > r_threshold and g > g_threshold and b < b_threshold:
                if abs(r - g) < 40: yellow_pixels.append(x)
            if g > 160 and r < 160 and b < 160: green_pixels.append(x)
        
        if not green_pixels:
            session["is_mining"] = False
            return

        if session["is_mining"] and (time.perf_counter() - session["last_click"] < 1.5):
            return

        if not yellow_pixels: return

        actual_rail_width = (max(rail_pixels) - min(rail_pixels)) if rail_pixels else width
        if actual_rail_width < 10: actual_rail_width = width

        target_x = sum(yellow_pixels) / len(yellow_pixels)
        current_x = max(green_pixels)
        
        if current_x > target_x + 2: return

        dist = target_x - current_x
        wait_ms = (dist * 1000.0) / actual_rail_width
        wait_ms += delay_ms
        
        if wait_ms < 0: wait_ms = 0
        if wait_ms > 1100: return

        session["is_mining"] = True
        session["last_click"] = time.perf_counter()
        
        def do_click(w_ms, tx, ty):
            if w_ms > 0: time.sleep(w_ms / 1000.0)
            abs_x = int(region["left"] + tx)
            abs_y = int(region["top"] + ty)
            
            try:
                class POINT(ctypes.Structure):
                    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
                pt = POINT()
                self.user32.GetCursorPos(ctypes.byref(pt))
                old_x, old_y = pt.x, pt.y

                self.user32.SetCursorPos(abs_x, abs_y)
                time.sleep(0.01)
                self.user32.mouse_event(0x0002, 0, 0, 0, 0) # LEFTDOWN
                time.sleep(0.04)
                self.user32.mouse_event(0x0004, 0, 0, 0, 0) # LEFTUP
                time.sleep(0.01)
                self.user32.SetCursorPos(old_x, old_y)
            except:
                old_pos = self._mouse.position
                self._mouse.position = (abs_x, abs_y)
                time.sleep(0.02)
                self._mouse.press(Button.left)
                time.sleep(0.04)
                self._mouse.release(Button.left)
                self._mouse.position = old_pos

        threading.Thread(target=do_click, args=(wait_ms, target_x, mid_y), daemon=True).start()
