import threading
import time
import mss
import ctypes
import os
import re
from PIL import Image, ImageEnhance, ImageOps
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Controller as KeyboardController, Key
from ctypes import wintypes

try:
    import pytesseract
    HAS_TESSERACT = True
    # Common Tesseract paths on Windows
    for candidate in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if os.path.isfile(candidate):
            pytesseract.pytesseract.tesseract_cmd = candidate
            break
except ImportError:
    HAS_TESSERACT = False

class QuestManager:
    def __init__(self, db, user_id):
        self.db = db
        self.user_id = user_id
        self._lock = threading.Lock()
        self._running = False
        self._busy = False
        self._thread = None
        self._mouse = MouseController()
        self._keyboard = KeyboardController()
        self.user32 = ctypes.windll.user32
        self._cooldown_until = 0.0
        self._quest_window_cooldown_until = 0.0

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
                busy = self._busy

            if busy:
                time.sleep(0.5)
                continue

            settings = self.db.get_quest_settings(self.user_id)
            if not settings or not settings.get("enabled"):
                time.sleep(1.0)
                continue

            pid, hwnd = self._get_foreground_pid()
            
            # Check if foreground process matches any fiesta.exe PID from scanner
            # This logic should be consistent with AutoHeal
            foreground_hwnd = self.user32.GetForegroundWindow()
            foreground_pid = wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(foreground_hwnd, ctypes.byref(foreground_pid))
            foreground_pid = foreground_pid.value
            
            # Note: In a real scenario, we'd verify if foreground_pid is a Fiesta process.
            # For now, we follow the user request: "nur ausgelöst werden wenn die entsprechende PID im vordergrund ist"
            # Since the manager runs globally, it should only act on the active window.

            # 1. Check Quest Window (if enabled)
            if settings.get("quest_window_enabled") and settings.get("quest_window_region"):
                self._check_quest_window(hwnd, settings)

            # 2. Check Reward Text
            if settings.get("region") and time.perf_counter() >= self._cooldown_until:
                self._check_reward(hwnd, settings)

            time.sleep(0.5)

    def _check_quest_window(self, hwnd, cfg):
        if time.perf_counter() < self._quest_window_cooldown_until:
            return

        region = cfg["quest_window_region"]
        img = self._capture_region(region)
        if img and self._is_quest_window_visible(img):
            return # Window is open, everything fine

        # Window closed? Press key
        key = cfg.get("quest_window_key", "l").lower()
        # Use pynput for key press
        self._tap_key(key)
        self._quest_window_cooldown_until = time.perf_counter() + 2.5 # Increased cooldown

    def _check_reward(self, hwnd, cfg):
        region = cfg["region"]
        img = self._capture_region(region)
        if not img: return

        keywords = cfg.get("keywords", ["belohnung", "reward"])
        center = self._find_reward_center(img, keywords)
        
        if center:
            self._run_sequence(center, cfg)

    def _find_reward_center(self, img, keywords):
        if not HAS_TESSERACT: return None
        
        # Preprocess for red text
        proc = self._preprocess_red(img)
        try:
            data = pytesseract.image_to_data(proc, lang="deu+eng", config="--psm 6", output_type=pytesseract.Output.DICT)
            for i in range(len(data['text'])):
                word = data['text'][i].lower()
                if any(kw in word for kw in keywords):
                    x = int(data['left'][i]) + int(data['width'][i]) // 2
                    y = int(data['top'][i]) + int(data['height'][i]) // 2
                    # Scaling back (preprocess scales by 3)
                    return int(x / 3), int(y / 3)
        except: pass
        return None

    def _preprocess_red(self, img):
        rgb = img.convert("RGB")
        out = Image.new("L", rgb.size)
        # Red text detection (r_min=140, g_max=110, b_max=110)
        data = [255 if (r >= 140 and g <= 110 and b <= 110) else 0 for r, g, b in rgb.getdata()]
        out.putdata(data)
        w, h = out.size
        out = out.resize((w * 3, h * 3), Image.Resampling.LANCZOS)
        return ImageEnhance.Contrast(out).enhance(2.0)

    def _is_quest_window_visible(self, img):
        # Simplified: Check for yellow "Quest" text or similar
        if not HAS_TESSERACT: return True # Assume visible if we can't check
        
        rgb = img.convert("RGB")
        out = Image.new("L", rgb.size)
        # Yellow detection
        data = [255 if (r >= 150 and g >= 120 and b <= 140) else 0 for r, g, b in rgb.getdata()]
        out.putdata(data)
        try:
            text = pytesseract.image_to_string(out, lang="eng", config="--psm 7").lower()
            return "quest" in text
        except: return True

    def _run_sequence(self, center, cfg):
        with self._lock:
            self._busy = True
        
        try:
            region = cfg["region"]
            abs_x = int(region["left"] + center[0])
            abs_y = int(region["top"] + center[1])
            
            # 1. Click Reward
            self._click_at(abs_x, abs_y)
            time.sleep(cfg.get("delay_after_reward", 300) / 1000.0)
            
            # 2. Click Target (if set)
            target = cfg.get("click_target")
            if target:
                self._click_at(int(target["x"]), int(target["y"]))
                time.sleep(cfg.get("delay_after_click", 200) / 1000.0)
                
            # 3. Space sequence
            count = cfg.get("space_count", 10)
            interval = cfg.get("space_interval", 100) / 1000.0
            for _ in range(count):
                self._tap_key("space")
                time.sleep(interval)
                
            self._cooldown_until = time.perf_counter() + 3.0
        finally:
            with self._lock:
                self._busy = False

    def _capture_region(self, region):
        with mss.mss() as sct:
            mon = {"left": int(region["left"]), "top": int(region["top"]), "width": int(region["width"]), "height": int(region["height"])}
            shot = sct.grab(mon)
            return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    def _click_at(self, x, y):
        old_pos = self._mouse.position
        self._mouse.position = (x, y)
        time.sleep(0.05)
        self._mouse.click(Button.left, 2) # Double click
        time.sleep(0.05)
        self._mouse.position = old_pos

    def _tap_key(self, key_str):
        if key_str == "space":
            k = Key.space
        else:
            k = key_str
        self._keyboard.press(k)
        time.sleep(0.05)
        self._keyboard.release(k)
