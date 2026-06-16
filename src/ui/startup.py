import sys
import os
import json
import requests
import zipfile
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QProgressBar, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont


VERSION = "2.0.1"
VERSION_INFO_URL = "https://raw.githubusercontent.com/RedSlimeC/Phoenix-V2/main/version_info.json"


class UpdateCheckThread(QThread):
    check_finished = pyqtSignal(bool, dict, str)  # (has_update, version_info, error)
    
    def run(self):
        try:
            response = requests.get(VERSION_INFO_URL, timeout=10)
            response.raise_for_status()
            version_info = response.json()
            
            has_update = self._compare_versions(VERSION, version_info["version"])
            self.check_finished.emit(has_update, version_info, "")
        except Exception as e:
            self.check_finished.emit(False, {}, str(e))
    
    def _compare_versions(self, current, latest):
        current_parts = list(map(int, current.split(".")))
        latest_parts = list(map(int, latest.split(".")))
        
        for curr, lat in zip(current_parts, latest_parts):
            if lat > curr:
                return True
            elif curr > lat:
                return False
        return len(latest_parts) > len(current_parts)


class DownloadThread(QThread):
    progress = pyqtSignal(int)
    download_finished = pyqtSignal(str, str)  # (file_path, error)
    
    def __init__(self, url):
        super().__init__()
        self.url = url
    
    def run(self):
        try:
            response = requests.get(self.url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            
            temp_path = os.path.join(os.path.dirname(sys.executable), "phoenix_update.exe")
            
            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.progress.emit(progress)
            
            self.download_finished.emit(temp_path, "")
        except Exception as e:
            self.download_finished.emit("", str(e))


class StartupWidget(QWidget):
    start_app = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.version_info = None
        self.has_update = False
        self.init_ui()
        self.check_for_updates()
    
    def init_ui(self):
        self.setFixedSize(400, 500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Phoenix Launcher")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Current version
        self.current_version_label = QLabel(f"Current Version: {VERSION}")
        self.current_version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.current_version_label)
        
        # Status label
        self.status_label = QLabel("Checking for updates...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Patchlog
        patchlog_label = QLabel("Patch History:")
        patchlog_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(patchlog_label)
        
        self.patchlog_text = QTextEdit()
        self.patchlog_text.setReadOnly(True)
        self.patchlog_text.setMaximumHeight(250)
        layout.addWidget(self.patchlog_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.update_button = QPushButton("Update")
        self.update_button.setMinimumHeight(40)
        self.update_button.clicked.connect(self.start_update)
        self.update_button.setVisible(False)
        button_layout.addWidget(self.update_button)
        
        self.start_button = QPushButton("Start")
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self.start_app.emit)
        self.start_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        
        layout.addLayout(button_layout)
    
    def check_for_updates(self):
        self.check_thread = UpdateCheckThread()
        self.check_thread.check_finished.connect(self.on_check_finished)
        self.check_thread.start()
    
    def on_check_finished(self, has_update, version_info, error):
        self.version_info = version_info
        self.has_update = has_update
        
        if error:
            self.status_label.setText(f"Failed to check updates: {error}")
        else:
            if has_update:
                self.status_label.setText(f"New version available: {version_info['version']}")
                self.update_button.setVisible(True)
            else:
                self.status_label.setText("You're up to date!")
        
        self.update_patchlog(version_info.get("patchlog", []))
        self.start_button.setEnabled(True)
    
    def update_patchlog(self, patchlog):
        html = ""
        for entry in patchlog:
            html += f"<h3>{entry['version']} - {entry['date']}</h3>"
            html += "<ul>"
            for change in entry["changes"]:
                html += f"<li>{change}</li>"
            html += "</ul>"
        self.patchlog_text.setHtml(html)
    
    def start_update(self):
        if not self.version_info:
            return
        
        url = self.version_info["download_url"]
        self.update_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Downloading update...")
        
        self.download_thread = DownloadThread(url)
        self.download_thread.progress.connect(self.progress_bar.setValue)
        self.download_thread.download_finished.connect(self.on_download_finished)
        self.download_thread.start()
    
    def on_download_finished(self, file_path, error):
        if error:
            self.status_label.setText(f"Download failed: {error}")
            self.update_button.setEnabled(True)
            self.start_button.setEnabled(True)
            self.progress_bar.setVisible(False)
            return
        
        self.status_label.setText("Update downloaded! Restarting...")
        
        # Replace current executable with new one
        try:
            current_exe = sys.executable
            backup_exe = current_exe + ".bak"
            
            # Backup current exe
            if os.path.exists(backup_exe):
                os.remove(backup_exe)
            os.rename(current_exe, backup_exe)
            
            # Move new exe
            os.rename(file_path, current_exe)
            
            # Restart the app
            subprocess.Popen([current_exe])
            sys.exit(0)
        except Exception as e:
            self.status_label.setText(f"Failed to apply update: {str(e)}")
            self.update_button.setEnabled(True)
            self.start_button.setEnabled(True)
            self.progress_bar.setVisible(False)
