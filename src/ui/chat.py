from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QFrame, QPlainTextEdit, QTextEdit, QSizePolicy, QTabWidget, QInputDialog, QMenu, QProgressBar, QDialog
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QDateTime, QPoint
from PyQt6.QtGui import QPixmap, QIcon, QCursor, QMovie
from datetime import datetime, timezone
import os

# QMovie cache to reuse instances for the same path
_movie_cache = {}

def parse_badge_filename(path):
    filename = os.path.basename(path)
    if "@" in filename:
        name_part, desc_part = filename.split("@", 1)
        desc, ext = os.path.splitext(desc_part)
        return (name_part, desc)
    else:
        name, ext = os.path.splitext(filename)
        return (name, "")

def get_cached_movie(path, scaled_size):
    """Get a cached QMovie instance for a given path and size, or create a new one"""
    key = (path, scaled_size.width(), scaled_size.height())
    if key not in _movie_cache:
        movie = QMovie(path)
        movie.setCacheMode(QMovie.CacheMode.CacheAll)
        movie.setScaledSize(scaled_size)
        _movie_cache[key] = movie
    return _movie_cache[key]

class MessageItem(QWidget):
    delete_requested = pyqtSignal(str)
    inspect_user = pyqtSignal(str)
    private_message = pyqtSignal(str)
    mute_user = pyqtSignal(str)

    def __init__(self, msg_data, current_user_data, db):
        super().__init__()
        self.msg_id = str(msg_data["_id"])
        self.user_id = msg_data["user_id"]
        self.user_name = msg_data["user_name"]
        self.db = db
        self.current_user_data = current_user_data
        self.background_movie = None
        self.avatar_movie = None
        self.frame_movie = None
        self.init_ui(msg_data)

    def init_ui(self, data):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)

        # Fetch latest user data from database (for old messages that don't have background/frame)
        user = self.db.users.find_one({"_id": self.user_id})
        if user:
            user_image = user.get("image")
            user_background = user.get("equipped_background")
            user_frame = user.get("equipped_frame")
        else:
            user_image = data.get("user_image")
            user_background = data.get("user_background")
            user_frame = data.get("user_frame")

        # Avatar Container (46x46)
        avatar_container = QWidget()
        avatar_container.setFixedSize(46, 46)
        avatar_container.setStyleSheet("background-color: transparent;")
        avatar_container.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Background (45x45 centered)
        background_lbl = QLabel(avatar_container)
        background_lbl.setFixedSize(45, 45)
        background_lbl.move(0, 0)
        background_lbl.setStyleSheet("background-color: #000000;")
        background_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if user_background and os.path.exists(user_background):
            if user_background.lower().endswith(".gif"):
                self.background_movie = get_cached_movie(user_background, background_lbl.size())
                background_lbl.setMovie(self.background_movie)
                self.background_movie.start()
            else:
                pixmap = QPixmap(user_background)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(45, 45, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    background_lbl.setPixmap(scaled)
        background_lbl.show()
        
        # Avatar (40x40 centered)
        avatar_lbl = QLabel(avatar_container)
        avatar_lbl.setFixedSize(40, 40)
        avatar_lbl.move(3, 3)  # (46-40)/2 = 3
        avatar_lbl.setStyleSheet("background-color: transparent; border: none;")
        avatar_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if user_image and os.path.exists(user_image):
            if user_image.lower().endswith(".gif"):
                self.avatar_movie = get_cached_movie(user_image, avatar_lbl.size())
                avatar_lbl.setMovie(self.avatar_movie)
                self.avatar_movie.start()
            else:
                pixmap = QPixmap(user_image)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(40, 40, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    avatar_lbl.setPixmap(scaled)
        avatar_lbl.show()
        
        # Frame (46x46)
        frame_lbl = QLabel(avatar_container)
        frame_lbl.setFixedSize(46, 46)
        frame_lbl.move(0, 0)
        frame_lbl.setStyleSheet("background-color: transparent; border: none;")
        frame_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if user_frame and os.path.exists(user_frame):
            if user_frame.lower().endswith(".gif"):
                self.frame_movie = get_cached_movie(user_frame, frame_lbl.size())
                frame_lbl.setMovie(self.frame_movie)
                self.frame_movie.start()
            else:
                pixmap = QPixmap(user_frame)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(46, 46, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    frame_lbl.setPixmap(scaled)
        frame_lbl.show()
        
        # Connect click events
        avatar_container.mousePressEvent = self.handle_click
        layout.addWidget(avatar_container, alignment=Qt.AlignmentFlag.AlignTop)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)

        # Header: Name (Clickable), Level, Rank, Time
        header_layout = QHBoxLayout()
        header_layout.setSpacing(5)

        self.name_lbl = QLabel(data.get("user_name", "User"))
        self.name_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.name_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 11px;")
        
        # Connect click events for name and avatar (Left and Right Click)
        self.name_lbl.mousePressEvent = self.handle_click

        level_lbl = QLabel(f"Lv {data.get('user_level', 1)}")
        level_lbl.setStyleSheet("color: #8c8c8c; font-size: 9px;")

        header_layout.addWidget(self.name_lbl)
        header_layout.addWidget(level_lbl)

        # Only show rank if it's 7 or higher
        user_rank = data.get("user_rank", 1)
        if user_rank >= 7:
            rank_name = self.db.get_rank_name(user_rank)
            rank_lbl = QLabel(rank_name)
            rank_lbl.setStyleSheet("color: #ff2b2b; font-size: 9px; font-weight: bold;")
            header_layout.addWidget(rank_lbl)

        time_lbl = QLabel(self.format_time(data.get("timestamp")))
        time_lbl.setStyleSheet("color: #666666; font-size: 9px;")

        header_layout.addStretch()
        header_layout.addWidget(time_lbl)
        
        # Delete button for own messages
        if self.user_id == self.current_user_data["_id"]:
            del_btn = QPushButton("×")
            del_btn.setFixedSize(15, 15)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.setStyleSheet("""
                QPushButton {
                    color: #666666;
                    background: transparent;
                    border: none;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    color: #ff2b2b;
                }
            """)
            del_btn.clicked.connect(lambda: self.delete_requested.emit(self.msg_id))
            header_layout.addWidget(del_btn)

        content_layout.addLayout(header_layout)

        # Message Text
        self.msg_display = QTextEdit()
        self.msg_display.setReadOnly(True)
        self.msg_display.setPlainText(data.get("text", ""))
        self.msg_display.setFrameStyle(QFrame.Shape.NoFrame)
        self.msg_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.msg_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.msg_display.setStyleSheet("""
            QTextEdit {
                color: #cccccc;
                font-size: 11px;
                background: transparent;
                padding: 0px;
            }
        """)
        
        # This is a trick to make QTextEdit behave like a label and wrap long words
        self.msg_display.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        
        # Calculate required height
        doc = self.msg_display.document()
        # Bind width to parent container width (roughly chat area width minus avatar and margins)
        # Using a safer width calculation
        doc.setTextWidth(170) 
        height = int(doc.size().height()) + 5
        self.msg_display.setFixedHeight(height)
        self.msg_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        content_layout.addWidget(self.msg_display)

        layout.addLayout(content_layout)

    def handle_click(self, event):
        if event.button() in [Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton]:
            self.show_context_menu(event)

    def show_context_menu(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                color: #ffffff;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #ff2b2b;
            }
        """)
        
        inspect_act = menu.addAction("Inspect")
        inspect_act.triggered.connect(lambda: self.inspect_user.emit(self.user_name))
        
        if self.user_name != self.current_user_data["name"]:
            private_act = menu.addAction("Private Message")
            private_act.triggered.connect(lambda: self.private_message.emit(self.user_name))
        
        # Mute option for Rank 7+
        if self.current_user_data.get("rank", 1) >= 7:
            is_muted = self.db.is_user_muted(self.user_name)
            mute_text = "Remove Mute" if is_muted else "Mute"
            mute_act = menu.addAction(mute_text)
            mute_act.triggered.connect(lambda: self.mute_user.emit(self.user_name))
        
        menu.exec(QCursor.pos())

    def format_time(self, dt):
        if not dt: return ""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except ValueError:
                return ""
        
        now = datetime.now(timezone.utc)
        
        # Ensure dt is offset-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elif dt.tzinfo.utcoffset(dt) is None:
            dt = dt.replace(tzinfo=timezone.utc)
            
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} days ago"
        seconds = diff.total_seconds()
        if seconds < 60:
            return "just now"
        minutes = int(seconds // 60)
        if minutes < 60:
            return f"{minutes} minutes ago"
        hours = minutes // 60
        return f"{hours} hours ago"

class InspectWidget(QWidget):
    back_to_chat = pyqtSignal()

    def __init__(self, user_data, db, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.db = db
        self.background_movie = None
        self.avatar_movie = None
        self.frame_movie = None
        self.badge_movies = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 25, 20, 20)
        layout.setSpacing(12)

        # Avatar Container (with background and frame) - same as account.py
        avatar_container = QWidget()
        avatar_container.setFixedSize(69, 69)
        avatar_container.setStyleSheet("background-color: transparent;")
        
        # Background (68x68 centered)
        background_lbl = QLabel(avatar_container)
        background_lbl.setFixedSize(68, 68)
        background_lbl.move(0, 0)
        background_lbl.setStyleSheet("background-color: #000000;")
        background_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        background_path = self.user_data.get("equipped_background")
        if background_path and os.path.exists(background_path):
            if background_path.lower().endswith(".gif"):
                self.background_movie = get_cached_movie(background_path, background_lbl.size())
                background_lbl.setMovie(self.background_movie)
                self.background_movie.start()
            else:
                pixmap = QPixmap(background_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(68, 68, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    background_lbl.setPixmap(scaled)
        background_lbl.show()
        
        # Avatar (60x60 centered)
        avatar_lbl = QLabel(avatar_container)
        avatar_lbl.setFixedSize(60, 60)
        avatar_lbl.move(4, 4)  # (69-60)/2 = 4.5 → 4
        avatar_lbl.setStyleSheet("background-color: transparent; border: none;")
        avatar_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        user_image = self.user_data.get("image")
        if user_image and os.path.exists(user_image):
            if user_image.lower().endswith(".gif"):
                self.avatar_movie = get_cached_movie(user_image, avatar_lbl.size())
                avatar_lbl.setMovie(self.avatar_movie)
                self.avatar_movie.start()
            else:
                pixmap = QPixmap(user_image)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(60, 60, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    avatar_lbl.setPixmap(scaled)
        avatar_lbl.show()
        
        # Frame (69x69)
        frame_lbl = QLabel(avatar_container)
        frame_lbl.setFixedSize(69, 69)
        frame_lbl.move(0, 0)
        frame_lbl.setStyleSheet("background-color: transparent; border: none;")
        frame_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        frame_path = self.user_data.get("equipped_frame")
        if frame_path and os.path.exists(frame_path):
            if frame_path.lower().endswith(".gif"):
                self.frame_movie = get_cached_movie(frame_path, frame_lbl.size())
                frame_lbl.setMovie(self.frame_movie)
                self.frame_movie.start()
            else:
                pixmap = QPixmap(frame_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(69, 69, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    frame_lbl.setPixmap(scaled)
        frame_lbl.show()
        
        avatar_layout = QHBoxLayout()
        avatar_layout.addStretch()
        avatar_layout.addWidget(avatar_container)
        avatar_layout.addStretch()
        layout.addLayout(avatar_layout)
        
        # Badges (36x36 each, no border)
        badges = self.user_data.get("equipped_badges", [])
        if badges:
            badges_layout = QHBoxLayout()
            badges_layout.setSpacing(2)
            badges_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            for badge_path in badges:
                if badge_path and os.path.exists(badge_path):
                    badge_lbl = QLabel()
                    badge_lbl.setFixedSize(36, 36)
                    badge_lbl.setStyleSheet("""
                        QLabel {
                            background-color: transparent; 
                            border: none;
                        }
                        QToolTip {
                            background-color: #1a1a1a;
                            color: #ffffff;
                            border: 1px solid #ff2b2b;
                            padding: 4px;
                            font-size: 11px;
                        }
                    """)
                    # Add tooltip
                    name, desc = parse_badge_filename(badge_path)
                    tooltip = f"{name}\n{desc}" if desc else name
                    badge_lbl.setToolTip(tooltip)
                    
                    if badge_path.lower().endswith(".gif"):
                        badge_movie = get_cached_movie(badge_path, badge_lbl.size())
                        self.badge_movies.append(badge_movie)
                        badge_lbl.setMovie(badge_movie)
                        badge_movie.start()
                    else:
                        pixmap = QPixmap(badge_path)
                        if not pixmap.isNull():
                            scaled = pixmap.scaled(36, 36, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                            badge_lbl.setPixmap(scaled)
                    badges_layout.addWidget(badge_lbl)
            layout.addLayout(badges_layout)
        
        # Spacer
        layout.addSpacing(5)

        # Info
        name = self.user_data.get('name', 'User')
        level = self.user_data.get('level', 1)
        xp = self.user_data.get('xp', 0)
        max_xp = self.user_data.get('max_xp', 100)
        xp_perc = (xp / max_xp * 100) if max_xp > 0 else 0
        rank_name = self.db.get_rank_name(self.user_data.get('rank', 1))
        joined = self.user_data.get('createdAt', datetime.now())
        if isinstance(joined, datetime):
            joined_str = joined.strftime("%d.%m.%Y")
        else:
            joined_str = "Unknown"

        def create_info_row(label, value, color="#ffffff"):
            row = QHBoxLayout()
            l = QLabel(f"{label}:")
            l.setStyleSheet("color: #8c8c8c; font-size: 11px; border: none;")
            v = QLabel(str(value))
            v.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; border: none;")
            row.addWidget(l)
            row.addStretch()
            row.addWidget(v)
            return row

        layout.addLayout(create_info_row("Account", name))
        layout.addLayout(create_info_row("Level", level))
        
        xp_bar = QProgressBar()
        xp_bar.setFixedHeight(10)
        xp_bar.setMaximum(max_xp)
        xp_bar.setValue(xp)
        xp_bar.setTextVisible(False)
        xp_bar.setStyleSheet("""
            QProgressBar {
                background-color: #000000;
                border: 1px solid #333333;
                border-radius: 5px;
            }
            QProgressBar::chunk {
                background-color: #ff2b2b;
                border-radius: 4px;
            }
        """)
        layout.addWidget(xp_bar)
        
        xp_text = QLabel(f"{xp} / {max_xp} ({int(xp_perc)}%)")
        xp_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        xp_text.setStyleSheet("color: #8c8c8c; font-size: 9px; border: none;")
        layout.addWidget(xp_text)

        layout.addLayout(create_info_row("Rank", rank_name, "#ff2b2b"))
        layout.addLayout(create_info_row("Member since", joined_str))

        back_btn = QPushButton("BACK")
        back_btn.setObjectName("link_btn_red")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.back_to_chat.emit)

        back_container = QHBoxLayout()
        back_container.addStretch()
        back_container.addWidget(back_btn)
        back_container.addStretch()
        layout.addLayout(back_container)

class ChatInput(QPlainTextEdit):
    returnPressed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setPlaceholderText("Type a message...")
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                color: #ffffff;
                padding: 5px;
                font-size: 11px;
            }
        """)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.returnPressed.emit()
        else:
            super().keyPressEvent(event)

class ChatWidget(QWidget):
    back_to_main = pyqtSignal()
    inspect_user = pyqtSignal(dict)

    def __init__(self, user_data, db):
        super().__init__()
        self.user_data = user_data
        self.db = db
        self.private_tabs = {} # partner_name -> tab_index
        self.tab_blink_state = {} # tab_index -> bool
        self.init_ui()
        
        # Check if user is muted initially
        user = self.db.users.find_one({"_id": self.user_data["_id"]})
        is_muted = user.get("is_muted", False) if user else False
        if is_muted:
            self.msg_input.setPlaceholderText("You are muted")
        
        # Load initial messages
        self.refresh_pane(self.general_chat)
        self.scroll_to_bottom(self.general_chat)
        
        # Auto-refresh timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_all)
        self.timer.start(2000) # Every 2 seconds

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Style Tabs
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #1a1a1a;
                background: #0c0c0c;
            }
            QTabBar::tab {
                background: #1a1a1a;
                color: #888888;
                padding: 5px 10px;
                font-size: 10px;
                font-weight: bold;
                border: 1px solid #000000;
                min-width: 60px;
            }
            QTabBar::tab:selected {
                background: #262626;
                color: #ff2b2b;
                border-bottom: 2px solid #ff2b2b;
            }
            QTabBar::close-button {
                image: none;
                background: #333333;
                subcontrol-position: right;
                width: 14px;
                height: 14px;
                border-radius: 2px;
                margin: 2px;
            }
            QTabBar::close-button:hover {
                background: #ff2b2b;
            }
        """)
        
        # General Tab
        self.general_chat = self.create_chat_pane("General")
        self.tabs.addTab(self.general_chat, "GENERAL")
        
        # Restore open chats from DB
        self.restore_open_chats()
        
        # Hide close button for the first tab (General)
        self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().ButtonPosition.RightSide, None)
        
        layout.addWidget(self.tabs, 1) # Add stretch factor 1 here

        # Input Area (Global for current tab)
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.msg_input = ChatInput()
        self.msg_input.returnPressed.connect(self.send_message)
        
        send_btn = QPushButton("SEND")
        send_btn.setFixedSize(50, 50)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff2b2b;
                color: #ffffff;
                font-weight: bold;
                font-size: 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #ff4545;
            }
        """)
        send_btn.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.msg_input)
        input_layout.addWidget(send_btn)
        layout.addWidget(input_container)

        # Back
        back_btn = QPushButton("BACK")
        back_btn.setObjectName("link_btn_red")
        back_btn.clicked.connect(self.back_to_main.emit)
        layout.addWidget(back_btn)

    def create_chat_pane(self, channel, partner=None):
        pane = QWidget()
        pane_layout = QVBoxLayout(pane)
        pane_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add a custom 'x' button for the tab if it's private
        # Since we use QTabWidget's built-in close button, we just style it.
        # But we need to make sure it's visible. 
        # Qt's QTabBar::close-button can be tricky without an image.
        # Let's use a small QPushButton as a tab button for better control.
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.verticalScrollBar().setStyleSheet("QScrollBar:vertical { width: 0px; background: transparent; }")
        scroll.setStyleSheet("background-color: #0c0c0c; border: none;")
        
        content = QWidget()
        chat_layout = QVBoxLayout(content)
        chat_layout.setContentsMargins(5, 5, 5, 5)
        chat_layout.setSpacing(5)
        chat_layout.addStretch()
        
        scroll.setWidget(content)
        pane_layout.addWidget(scroll)
        
        # Store metadata in pane
        pane.channel = channel
        pane.partner = partner
        pane.chat_layout = chat_layout
        pane.scroll = scroll
        
        # Scroll tracking
        pane.last_scroll_time = datetime.now(timezone.utc)
        scroll.verticalScrollBar().valueChanged.connect(lambda: self.on_scroll_activity(pane))
        
        return pane

    def on_scroll_activity(self, pane):
        pane.last_scroll_time = datetime.now(timezone.utc)

    def scroll_to_bottom(self, pane):
        QTimer.singleShot(50, lambda: pane.scroll.verticalScrollBar().setValue(pane.scroll.verticalScrollBar().maximum()))

    def request_private_chat(self):
        name, ok = QInputDialog.getText(self, "Private Chat", "Enter Username:")
        if ok and name:
            self.open_private_tab(name)

    def open_private_tab(self, partner_name):
        if partner_name == self.user_data["name"]: return
        if partner_name in self.private_tabs:
            self.tabs.setCurrentIndex(self.private_tabs[partner_name])
            return
            
        pane = self.create_chat_pane("Private", partner_name)
        idx = self.tabs.addTab(pane, partner_name.upper())
        self.private_tabs[partner_name] = idx
        
        # Add custom 'x' label to the tab button area since image:none hides the button sometimes
        close_btn = QPushButton("×")
        close_btn.setFixedSize(14, 14)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #333333;
                color: #ffffff;
                border: none;
                border-radius: 2px;
                font-size: 10px;
                font-weight: bold;
                margin: 0px;
                padding: 0px;
            }
            QPushButton:hover {
                background: #ff2b2b;
            }
        """)
        close_btn.clicked.connect(lambda: self.close_tab(self.tabs.indexOf(pane)))
        self.tabs.tabBar().setTabButton(idx, self.tabs.tabBar().ButtonPosition.RightSide, close_btn)
        
        # Save to DB
        self.db.add_open_chat(self.user_data["_id"], partner_name)
        
        self.tabs.setCurrentIndex(idx)
        self.refresh_pane(pane)

    def close_tab(self, index):
        if index == 0: return # Don't close General
        pane = self.tabs.widget(index)
        if hasattr(pane, 'partner') and pane.partner in self.private_tabs:
            partner = pane.partner
            # Remove from DB
            self.db.remove_open_chat(self.user_data["_id"], partner)
            del self.private_tabs[partner]
            
        self.tabs.removeTab(index)
        # Update indices in private_tabs
        new_tabs = {}
        for name, _ in self.private_tabs.items():
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i).upper() == name.upper():
                    new_tabs[name] = i
        self.private_tabs = new_tabs

    def on_tab_changed(self, index):
        pane = self.tabs.widget(index)
        if pane:
            # Scroll to bottom immediately on tab change
            self.scroll_to_bottom(pane)
            
            if hasattr(pane, 'partner') and pane.partner:
                self.db.mark_as_read(self.user_data["name"], pane.partner)
                # Reset blink
                self.tabs.tabBar().setTabTextColor(index, Qt.GlobalColor.white if index != self.tabs.currentIndex() else Qt.GlobalColor.red)
                if index in self.tab_blink_state:
                    del self.tab_blink_state[index]

    def send_message(self):
        text = self.msg_input.toPlainText().strip()
        if not text: return
        
        current_pane = self.tabs.currentWidget()
        if current_pane.channel == "General":
            success, msg = self.db.send_message(self.user_data["_id"], text, "General")
        else:
            success, msg = self.db.send_message(self.user_data["_id"], text, "Private", current_pane.partner)
        
        if success:
            self.msg_input.clear()
            self.refresh_pane(current_pane)
        else:
            # Maybe show a small warning if muted
            self.msg_input.setPlaceholderText(msg)
            QTimer.singleShot(3000, lambda: self.msg_input.setPlaceholderText("Type a message..."))

    def refresh_all(self):
        current_pane = self.tabs.currentWidget()
        if current_pane:
            # Refresh current tab
            self.refresh_pane(current_pane)
            
            # Auto-scroll if inactive for 2 seconds
            if (datetime.now(timezone.utc) - current_pane.last_scroll_time).total_seconds() >= 2:
                self.scroll_to_bottom(current_pane)
        
        # Check if user is muted
        user = self.db.users.find_one({"_id": self.user_data["_id"]})
        is_muted = user.get("is_muted", False) if user else False
        if is_muted:
            self.msg_input.setPlaceholderText("You are muted")
        else:
            self.msg_input.setPlaceholderText("Type a message...")
        
        # Check for new private messages
        unread = self.db.get_unread_private_messages(self.user_data["name"])
        for msg in unread:
            sender = msg["user_name"]
            if sender not in self.private_tabs:
                # Don't open tab automatically, just track that we have unread messages for it
                # We still need to create the tab so we can blink it, but don't switch to it
                self.create_private_tab_silently(sender)
            
            # Blink tab if not current
            idx = self.private_tabs[sender]
            if idx != self.tabs.currentIndex():
                self.blink_tab(idx)

    def restore_open_chats(self):
        # Fetch fresh user data for open chats
        user = self.db.users.find_one({"_id": self.user_data["_id"]})
        if user and "open_private_chats" in user:
            for partner in user["open_private_chats"]:
                if partner not in self.private_tabs:
                    self.create_private_tab_silently(partner)

    def create_private_tab_silently(self, partner_name):
        if partner_name == self.user_data["name"]: return
        if partner_name in self.private_tabs: return
            
        pane = self.create_chat_pane("Private", partner_name)
        idx = self.tabs.addTab(pane, partner_name.upper())
        self.private_tabs[partner_name] = idx
        
        # Add custom 'x' button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(14, 14)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #333333;
                color: #ffffff;
                border: none;
                border-radius: 2px;
                font-size: 10px;
                font-weight: bold;
                margin: 0px;
                padding: 0px;
            }
            QPushButton:hover {
                background: #ff2b2b;
            }
        """)
        close_btn.clicked.connect(lambda: self.close_tab(self.tabs.indexOf(pane)))
        self.tabs.tabBar().setTabButton(idx, self.tabs.tabBar().ButtonPosition.RightSide, close_btn)
        
        # Don't setCurrentIndex here
        self.refresh_pane(pane)

    def blink_tab(self, index):
        current_color = self.tabs.tabBar().tabTextColor(index)
        if current_color == Qt.GlobalColor.red:
            self.tabs.tabBar().setTabTextColor(index, Qt.GlobalColor.white)
        else:
            self.tabs.tabBar().setTabTextColor(index, Qt.GlobalColor.red)

    def refresh_pane(self, pane):
        if pane.channel == "General":
            messages = self.db.get_messages("General")
        else:
            messages = self.db.get_private_messages(self.user_data["name"], pane.partner)
            
        at_bottom = pane.scroll.verticalScrollBar().value() == pane.scroll.verticalScrollBar().maximum()
        
        # Clear (keep stretch)
        while pane.chat_layout.count() > 1:
            child = pane.chat_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        for msg in reversed(messages):
            item = MessageItem(msg, self.user_data, self.db)
            item.delete_requested.connect(lambda mid: self.handle_delete(mid, pane))
            item.inspect_user.connect(self.handle_inspect)
            item.private_message.connect(self.open_private_tab)
            item.mute_user.connect(self.handle_mute)
            pane.chat_layout.insertWidget(pane.chat_layout.count() - 1, item)
            
        if at_bottom:
            QTimer.singleShot(100, lambda: pane.scroll.verticalScrollBar().setValue(pane.scroll.verticalScrollBar().maximum()))

    def handle_inspect(self, username):
        user = self.db.users.find_one({"name": username})
        if user:
            self.inspect_user.emit(user)

    def handle_mute(self, username):
        success, msg = self.db.toggle_mute(username)
        if success:
            self.refresh_all()

    def handle_delete(self, msg_id, pane):
        if self.db.delete_message(msg_id, self.user_data["_id"]):
            self.refresh_pane(pane)
