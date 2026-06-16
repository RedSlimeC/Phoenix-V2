import ctypes
from ctypes import wintypes
import time
from pynput.keyboard import Controller, Key

class AutoHealManager:
    def __init__(self, db, user_id):
        self.db = db
        self.user_id = user_id
        self.user32 = ctypes.windll.user32
        self.keyboard = Controller()
        self.last_execution = {} # (pid, condition_index) -> last_time
        self.settings = None
        self.last_settings_fetch = 0
        
    def reload_settings(self):
        self.settings = self.db.get_auto_heal_settings(self.user_id)
        self.last_settings_fetch = time.time()

    def check_and_heal(self, results, is_feature_on):
        if not is_feature_on:
            return

        # Refresh settings every 5 seconds or if not loaded
        if self.settings is None or time.time() - self.last_settings_fetch > 5:
            self.reload_settings()
        
        settings = self.settings
        if not settings:
            return

        interval_ms = settings.get("interval", 500)
        interval_sec = interval_ms / 1000.0
        conditions = settings.get("conditions", [])
        
        # Get foreground window PID
        foreground_hwnd = self.user32.GetForegroundWindow()
        foreground_pid = wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(foreground_hwnd, ctypes.byref(foreground_pid))
        foreground_pid = foreground_pid.value

        for data in results:
            pid = data["pid"]
            
            # Check if this fiesta.exe is in foreground
            if pid != foreground_pid:
                continue

            # Check conditions
            try:
                hp = int(data.get("hp", 0))
                hp_max = int(data.get("hp_max", 1))
                mp = int(data.get("mp", 0))
                mp_max = int(data.get("mp_max", 1))
            except (ValueError, TypeError):
                continue

            for i, cond in enumerate(conditions):
                stat_val = 0
                max_val = 1
                
                if cond["stat"] == "LP":
                    stat_val = hp
                    max_val = hp_max
                else:
                    stat_val = mp
                    max_val = mp_max

                if max_val <= 0: max_val = 1
                
                current_val = stat_val
                threshold = cond["value"]
                
                if cond["comparison"] == "Prozent":
                    current_val = (stat_val / max_val) * 100
                
                # Check operator
                op = cond["operator"]
                triggered = False
                if op == "<": triggered = current_val < threshold
                elif op == "<=": triggered = current_val <= threshold
                elif op == ">": triggered = current_val > threshold
                elif op == ">=": triggered = current_val >= threshold
                elif op == "==": triggered = current_val == threshold
                
                if triggered:
                    now = time.time()
                    last_time = self.last_execution.get((pid, i), 0)
                    if now - last_time >= interval_sec:
                        print(f"[AutoHeal] Triggered: {cond['stat']}={current_val:.1f} {op} {threshold} -> Key: {cond['key']}")
                        self.send_key(foreground_hwnd, cond["key"])
                        self.last_execution[(pid, i)] = now

    def send_key(self, hwnd, key):
        # Using pynput for more reliable input simulation
        key = key.lower()
        
        special_keys = {
            "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4, "f5": Key.f5,
            "f6": Key.f6, "f7": Key.f7, "f8": Key.f8, "f9": Key.f9, "f10": Key.f10,
            "f11": Key.f11, "f12": Key.f12,
            "space": Key.space, "enter": Key.enter, "esc": Key.esc, "tab": Key.tab
        }
        
        target_key = special_keys.get(key, key)
        
        try:
            self.keyboard.press(target_key)
            time.sleep(0.05)
            self.keyboard.release(target_key)
        except Exception as e:
            print(f"[AutoHeal] Error sending key {key}: {e}")
