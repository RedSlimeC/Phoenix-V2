from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import Qt, pyqtSignal

class AppSettingsWidget(QWidget):
    back_to_main = pyqtSignal()
    settings_changed = pyqtSignal(dict)

    def __init__(self, user_data, db):
        super().__init__()
        self.user_data = user_data
        self.db = db
        self.settings = self.db.get_app_settings(user_data["_id"])
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        # Header
        header = QLabel("App Settings")
        header.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Always on Top Setting
        ontop_layout = QHBoxLayout()
        ontop_label = QLabel("Always on Top")
        ontop_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        
        self.ontop_btn = QPushButton("ON" if self.settings.get("always_on_top", True) else "OFF")
        self.ontop_btn.setFixedSize(60, 30)
        self.ontop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn_style()
        self.ontop_btn.clicked.connect(self.toggle_always_on_top)
        
        ontop_layout.addWidget(ontop_label)
        ontop_layout.addStretch()
        ontop_layout.addWidget(self.ontop_btn)
        layout.addLayout(ontop_layout)
        
        desc = QLabel("If enabled, the app will always stay above other windows.")
        desc.setStyleSheet("color: #8c8c8c; font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addStretch()

        # Back Button
        back_btn = QPushButton("BACK")
        back_btn.setObjectName("link_btn_red")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.back_to_main.emit)

        back_container = QHBoxLayout()
        back_container.addStretch()
        back_container.addWidget(back_btn)
        back_container.addStretch()
        layout.addLayout(back_container)

    def toggle_always_on_top(self):
        current = self.settings.get("always_on_top", True)
        self.settings["always_on_top"] = not current
        self.ontop_btn.setText("ON" if self.settings["always_on_top"] else "OFF")
        self.update_btn_style()
        self.db.save_app_settings(self.user_data["_id"], self.settings)
        self.settings_changed.emit(self.settings)

    def update_btn_style(self):
        if self.settings.get("always_on_top", True):
            self.ontop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #26d17d;
                    color: white;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)
        else:
            self.ontop_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8c2b2b;
                    color: white;
                    border-radius: 4px;
                    font-weight: bold;
                }
            """)
