from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

class FeatureToggle(QWidget):
    settings_clicked = pyqtSignal(str) # Emits the name of the feature
    toggled = pyqtSignal(bool) # Emits the new state
    
    def __init__(self, name, is_locked=False):
        super().__init__()
        self.is_on = False
        self.is_locked = is_locked
        self.name = name
        self.init_ui()

    def init_ui(self):
        # Clear layout if it exists
        if self.layout():
            # Correctly clear existing layout
            while self.layout().count():
                child = self.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            layout = self.layout()
        else:
            layout = QHBoxLayout(self)
            
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        self.name_lbl = QLabel(self.name)
        if self.is_locked:
            self.name_lbl.setObjectName("feature_name_locked")
        else:
            self.name_lbl.setObjectName("feature_name")
        layout.addWidget(self.name_lbl)
        layout.addStretch()

        if self.is_locked:
            self.premium_lbl = QLabel("Requires Premium-Membership")
            self.premium_lbl.setObjectName("premium_hint")
            layout.addWidget(self.premium_lbl)
        else:
            self.container = QWidget()
            self.container.setObjectName("toggle_container")
            self.container.setStyleSheet("""
                QWidget#toggle_container {
                    background-color: #000000;
                    border: 1px solid #333333;
                    border-radius: 4px;
                }
            """)
            
            container_layout = QHBoxLayout(self.container)
            container_layout.setContentsMargins(2, 2, 2, 2)
            container_layout.setSpacing(0)

            self.btn_off = QPushButton("OFF")
            self.btn_off.setFixedSize(38, 20)
            self.btn_off.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_off.clicked.connect(self.toggle)
            
            self.btn_on = QPushButton("ON")
            self.btn_on.setFixedSize(38, 20)
            self.btn_on.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_on.clicked.connect(self.toggle)

            container_layout.addWidget(self.btn_off)
            container_layout.addWidget(self.btn_on)
            layout.addWidget(self.container)

        # Settings icon
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("settings_icon")
        self.settings_btn.setFixedSize(25, 25)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8c8c8c;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        self.settings_btn.clicked.connect(lambda: self.settings_clicked.emit(self.name))
        layout.addWidget(self.settings_btn)
        
        if not self.is_locked:
            self.update_style()

    def set_locked(self, locked):
        if self.is_locked != locked:
            self.is_locked = locked
            self.init_ui()
            # Ensure stylesheet is re-applied because objectNames might have changed
            self.style().unpolish(self)
            self.style().polish(self)

    def set_on(self, is_on: bool):
        if self.is_locked:
            return
        self.is_on = bool(is_on)
        self.update_style()

    def toggle(self):
        if not self.is_locked:
            self.is_on = not self.is_on
            self.update_style()
            self.toggled.emit(self.is_on)

    def update_style(self):
        # Apply styles directly to the buttons to bypass any global stylesheet issues
        base_style = "border: none; border-radius: 3px; font-size: 10px; font-weight: bold;"
        
        if self.is_on:
            # ON State
            self.btn_on.setStyleSheet(f"{base_style} background-color: #26d17d; color: #ffffff;")
            self.btn_off.setStyleSheet(f"{base_style} background-color: transparent; color: #ffffff;")
        else:
            # OFF State
            self.btn_off.setStyleSheet(f"{base_style} background-color: #8c2b2b; color: #ffffff;")
            self.btn_on.setStyleSheet(f"{base_style} background-color: transparent; color: #ffffff;")
