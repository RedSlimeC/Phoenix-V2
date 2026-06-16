from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

class UltraZoomSettingsWidget(QWidget):
    back_to_main = pyqtSignal()
    zoom_changed = pyqtSignal(float)

    def __init__(self, user_data, db):
        super().__init__()
        self.user_data = user_data
        self.db = db
        self.zoom_value = self.db.get_zoom_settings(user_data["_id"])
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header
        header = QLabel("Ultra Zoom Settings")
        header.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Zoom Distance Label
        layout.addWidget(QLabel("Zoom Distance", styleSheet="color: #8c8c8c; font-size: 12px;"))

        # Current Zoom Display
        self.val_lbl = QLabel(str(self.zoom_value))
        self.val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.val_lbl.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #333333;
            border-radius: 4px;
            padding: 10px;
            color: #ffffff;
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(self.val_lbl)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(360, 7200)
        self.slider.setValue(int(self.zoom_value))
        self.slider.setTickInterval(100)
        self.slider.setStyleSheet("""
            QSlider::handle:horizontal {
                background: #ff2b2b;
                border: 1px solid #ff2b2b;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #333333;
                height: 4px;
                background: #1a1a1a;
                margin: 2px 0;
                border-radius: 2px;
            }
        """)
        self.slider.valueChanged.connect(self.on_slider_change)
        layout.addWidget(self.slider)

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

    def on_slider_change(self, value):
        self.zoom_value = value
        self.val_lbl.setText(str(value))
        self.db.save_zoom_settings(self.user_data["_id"], value)
        self.zoom_changed.emit(float(value))
