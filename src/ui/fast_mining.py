from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QScreen, QPixmap
import os

class HelpOverlay(QWidget):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.img_label = QLabel()
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            # Scale if needed, but the original image is small (mining bar)
            self.img_label.setPixmap(pixmap)
        
        self.img_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 2px solid #ff2b2b;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.img_label)

    def show_at(self, pos):
        self.move(pos)
        self.show()

class RegionSelector(QWidget):
    region_selected = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.showFullScreen()
        
        self.begin = None
        self.end = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setBrush(QColor(0, 0, 0, 100))
        painter.drawRect(self.rect())

        if self.begin and self.end:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 43, 43), 2))
            rect = QRect(self.begin, self.end)
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = self.begin
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        if self.begin and self.end:
            rect = QRect(self.begin, self.end).normalized()
            # We need absolute coordinates
            screen = QApplication.primaryScreen().geometry()
            region = {
                "left": rect.left() + screen.left(),
                "top": rect.top() + screen.top(),
                "width": rect.width(),
                "height": rect.height()
            }
            self.region_selected.emit(region)
        self.close()

class FastMiningSettingsWidget(QWidget):
    back_to_main = pyqtSignal()
    settings_changed = pyqtSignal()

    def __init__(self, user_data, db):
        super().__init__()
        self.user_data = user_data
        self.db = db
        self.settings = self.db.get_mining_settings(user_data["_id"])
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Header
        header = QLabel("Fast Mining Settings")
        header.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Region Section Header with Help
        region_header_layout = QHBoxLayout()
        region_header_layout.addWidget(QLabel("Mining Region", styleSheet="color: #8c8c8c; font-size: 12px;"))
        
        self.help_btn = QPushButton("?")
        self.help_btn.setFixedSize(18, 18)
        self.help_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.help_btn.setStyleSheet("""
            QPushButton {
                background-color: #262626;
                color: #8c8c8c;
                border-radius: 9px;
                font-size: 11px;
                font-weight: bold;
                border: 1px solid #333333;
            }
            QPushButton:hover {
                color: #ffffff;
                border: 1px solid #ff2b2b;
            }
        """)
        self.help_btn.clicked.connect(self.show_help)
        region_header_layout.addWidget(self.help_btn)
        region_header_layout.addStretch()
        layout.addLayout(region_header_layout)

        self.region_lbl = QLabel(self.get_region_text())
        self.region_lbl.setStyleSheet("""
            background-color: #1a1a1a;
            border: 1px solid #333333;
            border-radius: 4px;
            padding: 8px;
            color: #ffffff;
            font-size: 11px;
        """)
        layout.addWidget(self.region_lbl)

        self.select_btn = QPushButton("SELECT REGION")
        self.select_btn.setObjectName("action_btn_green")
        self.select_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_btn.clicked.connect(self.start_selection)
        layout.addWidget(self.select_btn)

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

    def get_region_text(self):
        r = self.settings.get("region")
        if not r: return "No region selected"
        return f"X: {r['left']}, Y: {r['top']} ({r['width']}x{r['height']})"

    def start_selection(self):
        self.selector = RegionSelector()
        self.selector.region_selected.connect(self.on_region_selected)
        self.selector.show()

    def on_region_selected(self, region):
        self.settings["region"] = region
        self.settings["delay_ms"] = 1 # Fixed to 1ms
        self.region_lbl.setText(self.get_region_text())
        self.save_settings()

    def save_settings(self):
        self.db.save_mining_settings(self.user_data["_id"], self.settings)
        self.settings_changed.emit()

    def show_help(self):
        # Calculate position: above the help button
        btn_pos = self.help_btn.mapToGlobal(self.help_btn.rect().topLeft())
        
        img_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images", "help", "help_area_04.png")
        if not os.path.exists(img_path):
            # Fallback if path structure is different
            img_path = "src/images/help/help_area_04.png"
            
        self.help_overlay = HelpOverlay(img_path)
        # Show it slightly offset to the left and above
        self.help_overlay.show_at(btn_pos + QPoint(-100, -60))
