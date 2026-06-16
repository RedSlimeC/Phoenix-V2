from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal

class GuidesWidget(QWidget):
    back_to_main = pyqtSignal()

    def __init__(self, user_data, db):
        super().__init__()
        self.user_data = user_data
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Title
        title = QLabel("GUIDES")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Scroll Area for Guides
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)

        # Placeholder - you can add guides here later!
        placeholder = QLabel("Hier werden später Guides hinzugefügt!")
        placeholder.setStyleSheet("color: #8c8c8c; font-size: 14px;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setWordWrap(True)
        scroll_layout.addWidget(placeholder)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Back Button
        back_btn = QPushButton("BACK")
        back_btn.setObjectName("primary_btn")
        back_btn.setStyleSheet("font-weight: 900; font-size: 14px; background-color: transparent; border: 1px solid #ffffff;")
        back_btn.setFixedSize(100, 35)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.back_to_main.emit)

        back_container = QVBoxLayout()
        back_container.addStretch()
        back_container.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        back_container.addStretch()
        layout.addLayout(back_container)
