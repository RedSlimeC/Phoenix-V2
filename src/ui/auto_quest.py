from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSpinBox, QLineEdit, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from src.ui.fast_mining import RegionSelector, HelpOverlay
import os

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def __init__(self, text):
        super().__init__(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
                font-size: 11px;
            }
            QLabel:hover {
                border: 1px solid #ff2b2b;
                background-color: #262626;
            }
        """)
    def mousePressEvent(self, event):
        self.clicked.emit()

class AutoQuestSettingsWidget(QWidget):
    back_to_main = pyqtSignal()
    settings_changed = pyqtSignal()

    def __init__(self, user_data, db):
        super().__init__()
        self.user_data = user_data
        self.db = db
        self.settings = self.db.get_quest_settings(user_data["_id"])
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(8)

        # Header
        header = QLabel("Auto Quest Settings")
        header.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: bold;")
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        content = QWidget()
        scroll_layout = QVBoxLayout(content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)

        # Reward Region
        scroll_layout.addLayout(self.create_header_with_help("Reward Area", "help_area_01.png"))
        self.reward_lbl = ClickableLabel(self.get_region_text(self.settings.get("region")))
        self.reward_lbl.clicked.connect(lambda: self.start_selection("region"))
        scroll_layout.addWidget(self.reward_lbl)

        # Click Target
        scroll_layout.addLayout(self.create_header_with_help("Accept Button", "help_area_02.png"))
        self.target_lbl = ClickableLabel(self.get_target_text())
        self.target_lbl.clicked.connect(lambda: self.start_selection("click_target"))
        scroll_layout.addWidget(self.target_lbl)

        # Quest Window Detection
        scroll_layout.addLayout(self.create_header_with_help("Auto-Open Window", "help_area_03.png"))
        
        qw_row = QHBoxLayout()
        self.qw_btn = QPushButton("ON" if self.settings.get("quest_window_enabled") else "OFF")
        self.qw_btn.setFixedSize(45, 22)
        self.update_toggle_style(self.qw_btn, self.settings.get("quest_window_enabled"))
        self.qw_btn.clicked.connect(self.toggle_qw)
        qw_row.addWidget(self.qw_btn)
        
        qw_row.addWidget(QLabel("Hotkey:", styleSheet="color: #8c8c8c; font-size: 11px;"))
        self.qw_key_input = QLineEdit()
        self.qw_key_input.setFixedWidth(30)
        self.qw_key_input.setText(self.settings.get("quest_window_key", "l"))
        self.qw_key_input.setMaxLength(1)
        self.qw_key_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qw_key_input.textChanged.connect(self.save_settings)
        qw_row.addWidget(self.qw_key_input)
        qw_row.addStretch()
        scroll_layout.addLayout(qw_row)

        self.qw_region_lbl = ClickableLabel(self.get_region_text(self.settings.get("quest_window_region")))
        self.qw_region_lbl.clicked.connect(lambda: self.start_selection("quest_window_region"))
        scroll_layout.addWidget(self.qw_region_lbl)

        # Space Settings
        space_row = QHBoxLayout()
        space_row.addWidget(QLabel("Space Count:", styleSheet="color: #8c8c8c; font-size: 11px;"))
        self.space_spin = QSpinBox()
        self.space_spin.setRange(0, 50)
        self.space_spin.setValue(self.settings.get("space_count", 10))
        self.space_spin.valueChanged.connect(self.save_settings)
        space_row.addWidget(self.space_spin)
        space_row.addStretch()
        scroll_layout.addLayout(space_row)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)

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

    def create_header_with_help(self, text, help_img):
        h_layout = QHBoxLayout()
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #8c8c8c; font-size: 11px; font-weight: bold;")
        h_layout.addWidget(lbl)
        
        help_btn = QPushButton("?")
        help_btn.setFixedSize(16, 16)
        help_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #555555;
                border-radius: 8px;
                font-size: 12px;
                border: 1px solid #333333;
            }
            QPushButton:hover { color: #ffffff; border: 1px solid #ff2b2b; background-color: #262626; }
        """)
        help_btn.clicked.connect(lambda: self.show_help(help_btn, help_img))
        h_layout.addWidget(help_btn)
        h_layout.addStretch()
        return h_layout

    def get_region_text(self, r):
        if not r: return "Click to select region"
        return f"X: {r['left']}, Y: {r['top']} ({r['width']}x{r['height']})"

    def get_target_text(self):
        t = self.settings.get("click_target")
        if not t: return "Click to select target"
        return f"X: {t['x']}, Y: {t['y']}"

    def start_selection(self, field):
        self.selector = RegionSelector()
        if field == "click_target":
            self.selector.region_selected.connect(lambda r: self.on_target_selected(r))
        else:
            self.selector.region_selected.connect(lambda r: self.on_region_selected(field, r))
        self.selector.show()

    def on_region_selected(self, field, region):
        self.settings[field] = region
        if field == "region": self.reward_lbl.setText(self.get_region_text(region))
        else: self.qw_region_lbl.setText(self.get_region_text(region))
        self.save_settings()

    def on_target_selected(self, region):
        target = {
            "x": region["left"] + region["width"] // 2,
            "y": region["top"] + region["height"] // 2
        }
        self.settings["click_target"] = target
        self.target_lbl.setText(self.get_target_text())
        self.save_settings()

    def toggle_qw(self):
        curr = self.settings.get("quest_window_enabled", False)
        self.settings["quest_window_enabled"] = not curr
        self.qw_btn.setText("ON" if self.settings["quest_window_enabled"] else "OFF")
        self.update_toggle_style(self.qw_btn, self.settings["quest_window_enabled"])
        self.save_settings()

    def update_toggle_style(self, btn, is_on):
        color = "#26d17d" if is_on else "#8c2b2b"
        btn.setStyleSheet(f"background-color: {color}; color: white; border-radius: 4px; font-weight: bold; font-size: 10px;")

    def save_settings(self):
        # Default values as requested
        self.settings["keywords"] = ["belohnung", "reward"]
        self.settings["space_interval"] = 50
        self.settings["space_count"] = self.space_spin.value()
        self.settings["quest_window_key"] = self.qw_key_input.text().lower() or "l"
        self.db.save_quest_settings(self.user_data["_id"], self.settings)
        self.settings_changed.emit()

    def show_help(self, btn, img_name):
        pos = btn.mapToGlobal(btn.rect().topLeft())
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "help", img_name)
        self.help_overlay = HelpOverlay(img_path)
        self.help_overlay.show_at(pos + QPoint(-130, -80))
