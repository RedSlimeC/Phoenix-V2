import ctypes
import struct
from ctypes import wintypes
from PyQt6.QtCore import QObject, pyqtSignal, QThread

# --- Constants & Offsets ---
PROCESS_NAME = "Fiesta.exe"
SCAN_STEP = 0x10000  # Schrittgröße für die Suche nach Adressen mit passendem Suffix

OFFSETS = {
    "CHAR_NAME":  0x1B6C,  # Letzte 16 Bit der CharName-Adresse
    "CURRENT_HP": 0x1B92,  # Letzte 16 Bit der CurrentHP-Adresse
    "MAX_HP":     0x1C7A,  # Letzte 16 Bit der MaxHP-Adresse
    "CURRENT_MP": 0x1B96,  # Letzte 16 Bit der CurrentMP-Adresse
    "MAX_MP":     0x1C7E,  # Letzte 16 Bit der MaxMP-Adresse
    "HP_STONE":   0x1B8E,  # Letzte 16 Bit der HPStone-Adresse
    "MP_STONE":   0x1B90,  # Letzte 16 Bit der MPStone-Adresse
    "STATUS":     0xCF58,  # Letzte 16 Bit der Status-Adresse
    "ZOOM":       0x68E8   # Letzte 16 Bit der Zoom-Adresse
}

# --- Windows API Structures ---
class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p),
        ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wintypes.DWORD),
        ("RegionSize", ctypes.c_size_t),
        ("State", wintypes.DWORD),
        ("Protect", wintypes.DWORD),
        ("Type", wintypes.DWORD),
    ]

class MemoryScanner:
    def __init__(self):
        self.kernel32 = ctypes.windll.kernel32
        self.cache = {} # pid -> {p_base, z_addr, s_addr, char_name}

    def open_process(self, pid):
        # PROCESS_ALL_ACCESS (0x001F0FFF) is needed for WriteProcessMemory
        return self.kernel32.OpenProcess(0x001F0FFF, False, pid)

    def read_mem(self, handle, addr, size):
        buf = ctypes.create_string_buffer(size)
        read = ctypes.c_size_t()
        if self.kernel32.ReadProcessMemory(handle, ctypes.c_void_p(addr), buf, size, ctypes.byref(read)):
            return buf.raw
        return None

    def write_mem(self, handle, addr, data):
        written = ctypes.c_size_t()
        return self.kernel32.WriteProcessMemory(handle, ctypes.c_void_p(addr), data, len(data), ctypes.byref(written))

    def write_f32(self, h, a, val):
        data = struct.pack("<f", val)
        return self.write_mem(h, a, data)

    def read_i32(self, h, a):
        d = self.read_mem(h, a, 4)
        return struct.unpack("<i", d)[0] if d else 0

    def read_u16(self, h, a):
        d = self.read_mem(h, a, 2)
        return struct.unpack("<H", d)[0] if d else 0

    def read_f32(self, h, a):
        d = self.read_mem(h, a, 4)
        return struct.unpack("<f", d)[0] if d else 0.0

    def read_str(self, h, a, max_len=32):
        d = self.read_mem(h, a, max_len)
        if not d: return ""
        try:
            end = d.find(b"\x00")
            if end != -1: d = d[:end]
            return d.decode("cp1252", errors="ignore").strip()
        except: return ""

    def name_score(self, name):
        name = (name or "").strip()
        if not (2 <= len(name) <= 24): return -10
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-[]()äöüÄÖÜß"
        bad = sum(1 for ch in name if ch not in allowed)
        if bad > 0: return -10
        return 2 + (3 if any(ch.isalpha() for ch in name) else 0)

    def is_valid_char(self, h, base):
        # Charakternamen prüfen
        name = self.read_str(h, base + OFFSETS["CHAR_NAME"])
        score = self.name_score(name)
        if score <= 0:
            return False
        
        # HP-Werte prüfen
        current_hp = self.read_i32(h, base + OFFSETS["CURRENT_HP"])
        max_hp = self.read_i32(h, base + OFFSETS["MAX_HP"])
        if current_hp <= 0 or max_hp <= 0 or current_hp > max_hp or max_hp > 100000:
            return False
        
        # MP-Werte prüfen
        current_mp = self.read_i32(h, base + OFFSETS["CURRENT_MP"])
        max_mp = self.read_i32(h, base + OFFSETS["MAX_MP"])
        if current_mp <= 0 or max_mp <= 0 or current_mp > max_mp or max_mp > 100000:
            return False
        
        return True

    def find_pids(self):
        pids = []
        snap = self.kernel32.CreateToolhelp32Snapshot(0x02, 0)
        class PE32(ctypes.Structure):
            _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                        ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                        ("szExeFile", ctypes.c_char * 260)]
        entry = PE32(dwSize=ctypes.sizeof(PE32))
        if self.kernel32.Process32First(snap, ctypes.byref(entry)):
            while True:
                if entry.szExeFile.decode().lower() == PROCESS_NAME.lower():
                    pids.append(entry.th32ProcessID)
                if not self.kernel32.Process32Next(snap, ctypes.byref(entry)): break
        self.kernel32.CloseHandle(snap)
        return pids

    def iter_suffix_addrs(self, base, size, suffix):
        mod = base & 0xFFFF  # Modulo 65536 (letzte 16 Bit der Basisadresse)
        # Berechne die erste Adresse im Bereich mit dem gewünschten Suffix
        if mod <= suffix:
            addr = base + (suffix - mod)
        else:
            addr = base + (0x10000 - mod + suffix)
        res = []
        while addr < base + size - 3:  # -3, um Lesen über den Bereich hinaus zu vermeiden
            res.append(addr)
            addr += SCAN_STEP  # Nächste Adresse mit gleichem Suffix (in 64KB-Schritten)
        return res

    def get_data(self):
        pids = self.find_pids()
        results = []
        
        # Aufräumen: Cache-Einträge für geschlossene Prozesse entfernen
        current_pids = set(pids)
        cached_pids = list(self.cache.keys())
        for pid in cached_pids:
            if pid not in current_pids:
                del self.cache[pid]

        for pid in pids:
            h = self.open_process(pid)
            if not h: continue
            
            p_base = None
            z_addr = None
            s_addr = None
            char_name = None
            
            # Versuche, gecachte Adressen zu nutzen (zuerst prüfen, ob sie noch gültig sind)
            if pid in self.cache:
                c = self.cache[pid]
                if self.is_valid_char(h, c["p_base"]):
                    p_base = c["p_base"]
                    char_name = self.read_str(h, p_base + OFFSETS["CHAR_NAME"])
                    z_addr = c["z_addr"]
                    
                    # Prüfe, ob die gecachte Status-Adresse noch gültig ist
                    cached_s_addr = c["s_addr"]
                    if cached_s_addr and self.read_str(h, cached_s_addr, len(char_name)) == char_name:
                        s_addr = cached_s_addr
                    else:
                        s_addr = 0
            
            if p_base is None:
                # Schritt 1: Spielerbasisadresse finden (suche nach CHAR_NAME-Offset-Suffix 0x1B6C)
                player_candidates = []
                mbi = MEMORY_BASIC_INFORMATION()
                curr = 0
                while self.kernel32.VirtualQueryEx(h, ctypes.c_void_p(curr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                    if mbi.State == 0x1000 and (mbi.Protect & 0x04 or mbi.Protect & 0x40): # MEM_COMMIT und lesbar
                        for char_name_addr in self.iter_suffix_addrs(mbi.BaseAddress, mbi.RegionSize, OFFSETS["CHAR_NAME"]):
                            base = char_name_addr - OFFSETS["CHAR_NAME"]
                            if self.is_valid_char(h, base):
                                name = self.read_str(h, base + OFFSETS["CHAR_NAME"])
                                player_candidates.append((base, self.name_score(name), name))
                    curr += mbi.RegionSize

                if not player_candidates:
                    self.kernel32.CloseHandle(h)
                    continue
                
                # Beste Spielerbasisadresse auswählen (höchster Name-Score)
                player_candidates.sort(key=lambda x: -x[1])
                p_base, _, char_name = player_candidates[0]

                # Schritt 2: Status-Adresse finden (Suffix 0xCF58)
                s_addr = 0
                found_valid_status = False

                # Zuerst prüfen, ob wir an der Status-Adresse der Charaktername steht
                curr = 0
                while self.kernel32.VirtualQueryEx(h, ctypes.c_void_p(curr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                    if not found_valid_status and mbi.State == 0x1000 and (mbi.Protect & 0x04 or mbi.Protect & 0x40):
                        for candidate_status_addr in self.iter_suffix_addrs(mbi.BaseAddress, mbi.RegionSize, OFFSETS["STATUS"]):
                            # Prüfe, ob an dieser Adresse der Charaktername steht (wie im Originalcode)
                            if self.read_str(h, candidate_status_addr, len(char_name)) == char_name:
                                s_addr = candidate_status_addr
                                found_valid_status = True
                                break
                    curr += mbi.RegionSize
                    if found_valid_status:
                        break

                # Schritt 3: Zoom-Adresse finden (Suffix 0x68E8)
                z_addr = 0
                zoom_candidates = []
                curr = 0
                while self.kernel32.VirtualQueryEx(h, ctypes.c_void_p(curr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                    if mbi.State == 0x1000 and (mbi.Protect & 0x04 or mbi.Protect & 0x40):
                        for candidate_zoom_addr in self.iter_suffix_addrs(mbi.BaseAddress, mbi.RegionSize, OFFSETS["ZOOM"]):
                            val = self.read_f32(h, candidate_zoom_addr)
                            if 0.1 <= val <= 50000.0: # Plausibler Zoom-Bereich
                                zoom_candidates.append(candidate_zoom_addr)
                    curr += mbi.RegionSize
                if zoom_candidates:
                    z_addr = zoom_candidates[0] # Nimm den ersten plausiblen Kandidaten
                
                # Cache die Ergebnisse
                self.cache[pid] = {
                    "p_base": p_base,
                    "z_addr": z_addr,
                    "s_addr": s_addr,
                    "char_name": char_name
                }

            # Werte auslesen
            status_val = self.read_str(h, s_addr, 32) if s_addr else "Not found"

            results.append({
                "pid": pid,
                "char_name": char_name,
                "hp": f"{self.read_i32(h, p_base + OFFSETS['CURRENT_HP'])}",
                "hp_max": f"{self.read_i32(h, p_base + OFFSETS['MAX_HP'])}",
                "mp": f"{self.read_i32(h, p_base + OFFSETS['CURRENT_MP'])}",
                "mp_max": f"{self.read_i32(h, p_base + OFFSETS['MAX_MP'])}",
                "hp_stone": f"{self.read_u16(h, p_base + OFFSETS['HP_STONE'])}",
                "mp_stone": f"{self.read_u16(h, p_base + OFFSETS['MP_STONE'])}",
                "status": status_val,
                "zoom": f"{self.read_f32(h, z_addr):.1f}" if z_addr else "???",
                "p_base": hex(p_base),
                "z_addr": hex(z_addr) if z_addr else "???",
                "s_addr": hex(s_addr) if s_addr else "???",
                "char_name_addr": hex(p_base + OFFSETS["CHAR_NAME"]),
                "hp_addr": hex(p_base + OFFSETS["CURRENT_HP"]),
                "hp_max_addr": hex(p_base + OFFSETS["MAX_HP"]),
                "mp_addr": hex(p_base + OFFSETS["CURRENT_MP"]),
                "mp_max_addr": hex(p_base + OFFSETS["MAX_MP"]),
                "hp_stone_addr": hex(p_base + OFFSETS["HP_STONE"]),
                "mp_stone_addr": hex(p_base + OFFSETS["MP_STONE"]),
                "zoom_addr": hex(z_addr) if z_addr else "???"
            })
            self.kernel32.CloseHandle(h)
        return results

class ScannerWorker(QObject):
    data_ready = pyqtSignal(list)

    def __init__(self, scanner):
        super().__init__()
        self.scanner = scanner
        self._running = True

    def run(self):
        while self._running:
            try:
                results = self.scanner.get_data()
                # Check again if still running before emitting
                if self._running:
                    self.data_ready.emit(results)
            except RuntimeError:
                # This happens if the C++ object is deleted
                break
            except Exception as e:
                print(f"[ScannerWorker] Error: {e}")
            QThread.msleep(100)

    def stop(self):
        self._running = False
