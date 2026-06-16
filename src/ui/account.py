import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QGridLayout, QMessageBox, QTabWidget, QStackedLayout, QDialog, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QIcon, QMovie

# QMovie cache to reuse instances for the same path
_movie_cache = {}

def parse_badge_filename(path):
    filename = os.path.basename(path)
    # Split at @
    if "@" in filename:
        name_part, desc_part = filename.split("@", 1)
        # Remove extension from desc_part
        desc, ext = os.path.splitext(desc_part)
        return (name_part, desc)
    else:
        # No @, use filename without extension as name, no description
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

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

class ClickableAvatarContainer(QWidget):
    clicked = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

class AvatarSelectionWidget(QWidget):
    back_to_account = pyqtSignal()

    def __init__(self, user_data, db):
        super().__init__()
        self.user_data = user_data
        self.db = db
        self.current_tab = "avatar"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #1a1a1a;
                background: #0c0c0c;
            }
            QTabBar::tab {
                background: #1a1a1a;
                color: #888888;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: bold;
                border: 1px solid #000000;
            }
            QTabBar::tab:selected {
                background: #262626;
                color: #ff2b2b;
                border-bottom: 2px solid #ff2b2b;
            }
        """)

        self.avatar_tab = self.create_tab("avatar")
        self.frame_tab = self.create_tab("frame")
        self.background_tab = self.create_tab("background")
        self.badge_tab = self.create_tab("badge")

        self.tabs.addTab(self.avatar_tab, "AVATAR")
        self.tabs.addTab(self.frame_tab, "FRAME")
        self.tabs.addTab(self.background_tab, "BG")
        self.tabs.addTab(self.badge_tab, "BADGE")

        self.tabs.currentChanged.connect(self.on_tab_changed)

        layout.addWidget(self.tabs)

        back_btn = QPushButton("BACK")
        back_btn.setObjectName("link_btn_red")
        back_btn.clicked.connect(self.back_to_account.emit)
        layout.addWidget(back_btn)

        self.load_all_categories("avatar")

    def create_tab(self, category):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")

        scroll_content = QWidget()
        self.main_layout = QVBoxLayout(scroll_content)
        self.main_layout.setSpacing(15)

        scroll.setWidget(scroll_content)
        tab_layout.addWidget(scroll)

        return tab

    def on_tab_changed(self, index):
        categories = ["avatar", "frame", "background", "badge"]
        self.current_tab = categories[index]
        self.load_all_categories(self.current_tab)

    def load_all_categories(self, category):
        tab = {
            "avatar": self.avatar_tab,
            "frame": self.frame_tab,
            "background": self.background_tab,
            "badge": self.badge_tab
        }[category]

        # Clear tab content
        scroll = tab.findChild(QScrollArea)
        if scroll:
            scroll_content = scroll.widget()
            main_layout = scroll_content.layout()
            while main_layout.count():
                child = main_layout.takeAt(0)
                if child.widget(): child.widget().deleteLater()

        base_path_map = {
            "avatar": r"c:\Users\havan\Downloads\Phoenix\src\images\account_icons",
            "frame": r"c:\Users\havan\Downloads\Phoenix\src\images\frame",
            "background": r"c:\Users\havan\Downloads\Phoenix\src\images\avatar_background",
            "badge": r"c:\Users\havan\Downloads\Phoenix\src\images\badge"
        }
        base_path = base_path_map[category]

        # 1. Normal Levels
        self.add_category_section(main_layout, "LEVEL REWARDS", base_path, is_level=True, category=category)

        # 2. Premium (Rank 2+)
        if self.user_data.get('rank', 1) >= 2:
            premium_path = os.path.join(base_path, "Premium")
            self.add_category_section(main_layout, "PREMIUM EXCLUSIVE", premium_path, category=category)

        # 3. Staff (Rank 7+)
        if self.user_data.get('rank', 1) >= 7:
            staff_path = os.path.join(base_path, "Staff")
            self.add_category_section(main_layout, "STAFF ONLY", staff_path, category=category)

        # 4. Acquired Items
        self.add_acquired_section(main_layout, base_path, category)

        # 5. Coin Shop (Rotating)
        self.add_shop_section(main_layout, base_path, category)

    def add_acquired_section(self, main_layout, base_path, category):
        unlocked_field_map = {
            "avatar": "unlocked_avatars",
            "frame": "unlocked_frames",
            "background": "unlocked_backgrounds",
            "badge": "unlocked_badges"
        }
        unlocked = self.user_data.get(unlocked_field_map[category], [])

        shop_path = os.path.join(base_path, "Shop")

        acquired_shop_items = []
        for path in unlocked:
            if path.startswith(shop_path):
                acquired_shop_items.append(path)

        if not acquired_shop_items: return

        section_title = QLabel("ACQUIRED ITEMS")
        section_title.setStyleSheet("color: #26d17d; font-weight: bold; font-size: 12px; margin-top: 10px;")
        main_layout.addWidget(section_title)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)

        row, col = 0, 0
        for img_path in acquired_shop_items:
            self.add_item(grid, img_path, row, col, category=category)
            col += 1
            if col > 2: col = 0; row += 1

        main_layout.addWidget(grid_widget)

    def add_shop_section(self, main_layout, base_path, category):
        shop_path = os.path.join(base_path, "Shop")
        shop_items = self.db.get_current_shop_icons(self.user_data["_id"], category)
        if not shop_items: return

        # Title with Timer
        title_layout = QHBoxLayout()
        section_title = QLabel("COIN SHOP")
        section_title.setStyleSheet("color: #ff2b2b; font-weight: bold; font-size: 12px;")

        # Calculate time until refresh
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        if now.hour < 12:
            next_refresh = now.replace(hour=12, minute=0, second=0, microsecond=0)
        else:
            next_refresh = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        diff = next_refresh - now
        hours, rem = divmod(diff.seconds, 3600)
        minutes, _ = divmod(rem, 60)

        timer_lbl = QLabel(f"(Refresh in {hours:02d}:{minutes:02d})")
        timer_lbl.setStyleSheet("color: #8c8c8c; font-size: 10px; font-weight: normal;")

        title_layout.addWidget(section_title)
        title_layout.addWidget(timer_lbl)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)

        row, col = 0, 0
        unlocked_field_map = {
            "avatar": "unlocked_avatars",
            "frame": "unlocked_frames",
            "background": "unlocked_backgrounds",
            "badge": "unlocked_badges"
        }
        unlocked = self.user_data.get(unlocked_field_map[category], [])

        for item in shop_items:
            filename = item["filename"]
            price = item["price"]
            img_path = os.path.join(shop_path, filename)

            # Only show in shop if NOT already acquired
            if img_path not in unlocked:
                self.add_item(grid, img_path, row, col, price=price, category=category)
                col += 1
                if col > 2: col = 0; row += 1

        main_layout.addWidget(grid_widget)

    def add_category_section(self, main_layout, title_text, path, is_level=False, category="avatar"):
        if not os.path.exists(path): return

        section_title = QLabel(title_text)
        section_title.setStyleSheet("color: #ff2b2b; font-weight: bold; font-size: 12px; margin-top: 10px;")
        main_layout.addWidget(section_title)

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(10)
        grid.setContentsMargins(0, 0, 0, 0)

        row, col = 0, 0

        if is_level:
            # Handle the numbered folders
            for foldername in sorted(os.listdir(path)):
                folder_path = os.path.join(path, foldername)
                if os.path.isdir(folder_path):
                    try:
                        level_req = int(foldername)
                    except ValueError: continue

                    if self.user_data.get('level', 1) >= level_req:
                        for filename in os.listdir(folder_path):
                            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                                self.add_item(grid, os.path.join(folder_path, filename), row, col, category=category)
                                col += 1
                                if col > 2: col = 0; row += 1
        else:
            # Direct files in the path
            for filename in os.listdir(path):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    img_path = os.path.join(path, filename)
                    self.add_item(grid, img_path, row, col, category=category)
                    col += 1
                    if col > 2: col = 0; row += 1

        main_layout.addWidget(grid_widget)

    def add_item(self, grid, path, row, col, price=None, category="avatar"):
        from PyQt6.QtGui import QMovie
        
        container = QWidget()
        item_layout = QVBoxLayout(container)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(2)

        btn = QPushButton()
        btn.setFixedSize(46, 46)  # Same as frame size
        
        # Compute tooltip first
        badge_tooltip = None
        if category == "badge":
            name, desc = parse_badge_filename(path)
            badge_tooltip = f"{name}\n{desc}" if desc else name
        
        if path.lower().endswith('.gif'):
            # For GIFs, use a QLabel inside the button
            lbl = QLabel()
            lbl.setFixedSize(40, 40)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            movie = QMovie(path)
            movie.setCacheMode(QMovie.CacheMode.CacheAll)
            movie.setScaledSize(lbl.size())
            lbl.setMovie(movie)
            movie.start()
            # Add to button layout
            btn_layout = QVBoxLayout(btn)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                icon_pixmap = pixmap.scaled(40, 40, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                btn.setIcon(QIcon(icon_pixmap))
                btn.setIconSize(icon_pixmap.size())

        unlocked_field_map = {
            "avatar": "unlocked_avatars",
            "frame": "unlocked_frames",
            "background": "unlocked_backgrounds",
            "badge": "unlocked_badges"
        }
        unlocked_list = self.user_data.get(unlocked_field_map[category], [])
        is_unlocked = (path in unlocked_list) or (price is None)

        # Check if item is equipped
        equipped_field_map = {
            "avatar": "image",
            "frame": "equipped_frame",
            "background": "equipped_background",
            "badge": "equipped_badges"
        }
        is_equipped = False
        if category == "badge":
            is_equipped = path in self.user_data.get(equipped_field_map[category], [])
        else:
            is_equipped = path == self.user_data.get(equipped_field_map[category])

        border_color = "#333333"
        if is_equipped:
            border_color = "#26d17d"
        elif not is_unlocked:
            border_color = "#444444"
            btn.setToolTip(f"Costs {price} Coins")
        elif category == "badge" and badge_tooltip:
            btn.setToolTip(badge_tooltip)

        # Build style sheet with tooltip if badge
        style_sheet = f"""
            QPushButton {{
                background-color: #262626;
                border: 2px solid {border_color};
                border-radius: 5px;
            }}
            QPushButton:hover {{
                border: 2px solid #ff2b2b;
                background-color: #333333;
            }}
        """
        
        if category == "badge":
            style_sheet += """
                QToolTip {
                    background-color: #1a1a1a;
                    color: #ffffff;
                    border: 1px solid #ff2b2b;
                    padding: 4px;
                    font-size: 11px;
                }
            """
        
        btn.setStyleSheet(style_sheet)

        if is_unlocked:
            btn.clicked.connect(lambda: self.handle_select(path, category))
        else:
            btn.clicked.connect(lambda: self.handle_purchase(path, price, category))

        item_layout.addWidget(btn)

        if price is not None and not is_unlocked:
            price_lbl = QLabel(f"{price} Coins")
            price_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            price_lbl.setStyleSheet("color: #ffd700; font-size: 9px; font-weight: bold;")
            item_layout.addWidget(price_lbl)
        elif price is not None:
            status_lbl = QLabel("OWNED")
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_lbl.setStyleSheet("color: #26d17d; font-size: 8px; font-weight: bold;")
            item_layout.addWidget(status_lbl)
        elif is_equipped:
            status_lbl = QLabel("EQUIPPED")
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_lbl.setStyleSheet("color: #26d17d; font-size: 8px; font-weight: bold;")
            item_layout.addWidget(status_lbl)

        grid.addWidget(container, row, col)

    def handle_select(self, path, category):
        if category == "avatar":
            self.db.users.update_one({"_id": self.user_data["_id"]}, {"$set": {"image": path}})
        elif category == "frame":
            self.db.users.update_one({"_id": self.user_data["_id"]}, {"$set": {"equipped_frame": path}})
        elif category == "background":
            self.db.users.update_one({"_id": self.user_data["_id"]}, {"$set": {"equipped_background": path}})
        elif category == "badge":
            equipped = self.user_data.get("equipped_badges", [])
            if path in equipped:
                equipped.remove(path)
                self.db.users.update_one({"_id": self.user_data["_id"]}, {"$set": {"equipped_badges": equipped}})
            else:
                if len(equipped) < 2:
                    equipped.append(path)
                    self.db.users.update_one({"_id": self.user_data["_id"]}, {"$set": {"equipped_badges": equipped}})

        # Refresh everything
        user = self.db.users.find_one({"_id": self.user_data["_id"]})
        if user:
            self.user_data = user
            self.load_all_categories(category)

    def handle_purchase(self, path, price, category):
        # Confirmation Dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        msg_box.setText(f"Buy for {price} Coins?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        # Style the message box to match the app theme
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #1a1a1a;
                border: 2px solid #333333;
            }
            QLabel {
                color: #ffffff;
                font-size: 13px;
                padding: 10px;
            }
            QPushButton {
                background-color: #262626;
                color: #ffffff;
                border: 1px solid #333333;
                padding: 5px 15px;
                border-radius: 3px;
                min-width: 60px;
                margin-bottom: 10px;
            }
            QPushButton:hover {
                background-color: #ff2b2b;
                border: 1px solid #ff2b2b;
            }
        """)

        if msg_box.exec() == QMessageBox.StandardButton.Yes:
            buy_func_map = {
                "avatar": self.db.buy_avatar,
                "frame": self.db.buy_frame,
                "background": self.db.buy_background,
                "badge": self.db.buy_badge
            }
            success, msg = buy_func_map[category](self.user_data["_id"], path, price)
            if success:
                # Refresh everything
                user = self.db.users.find_one({"_id": self.user_data["_id"]})
                if user:
                    self.user_data = user
                    self.load_all_categories(category)

    def refresh_user_data(self, new_data):
        self.user_data = new_data
        self.load_all_categories(self.current_tab)

class BuyPremiumWidget(QWidget):
    back_to_account = pyqtSignal()

    def __init__(self, db, user_data, parent=None):
        super().__init__(parent)
        self.db = db
        self.user_data = user_data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel("PREMIUM MEMBERSHIP")
        title.setStyleSheet("color: #ff2b2b; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        offers = [
            ("1 Day", 25),
            ("3 Days", 50),
            ("7 Days", 100),
            ("14 Days", 150),
            ("30 Days", 250)
        ]

        for o_name, price in offers:
            btn_text = (
                f"Premium Membership ({o_name}) - {price} Coins"
            )

            offer_btn = QPushButton(btn_text)
            offer_btn.setFixedSize(250, 45)
            offer_btn.setStyleSheet("""
                QPushButton {
                    background-color: #262626;
                    color: #ffffff;
                    border: 1px solid #333333;
                    font-weight: bold;
                    border-radius: 4px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #ff2b2b;
                    border: 1px solid #ff2b2b;
                }
            """)
            days = int(o_name.split()[0])
            offer_btn.clicked.connect(lambda checked, d=days: self.buy_premium(d))
            layout.addWidget(offer_btn)

        layout.addStretch()

        back_btn = QPushButton("BACK")
        back_btn.setObjectName("primary_btn")
        back_btn.setStyleSheet("font-weight: 900; font-size: 14px; background-color: transparent; border: 1px solid #ffffff;")
        back_btn.setFixedSize(100, 35)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.back_to_account.emit)

        back_container = QVBoxLayout()
        back_container.addStretch()
        back_container.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        back_container.addStretch()
        layout.addLayout(back_container)

    def buy_premium(self, days):
        success, msg = self.db.buy_premium(self.user_data["_id"], days)
        if success:
            self.back_to_account.emit()

    def refresh_user_data(self, user_data):
        self.user_data = user_data


class BuyCoinsWidget(QWidget):
    back_to_account = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel("BUY COINS")
        title.setStyleSheet("color: #ffd700; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        info = QLabel("Coming soon!")
        info.setStyleSheet("color: #8c8c8c; font-size: 13px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        layout.addStretch()

        close_btn = QPushButton("BACK")
        close_btn.setFixedSize(250, 35)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: 1px solid #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ffffff;
                color: #000000;
            }
        """)
        close_btn.clicked.connect(self.back_to_account.emit)
        layout.addWidget(close_btn)

class AccountSettingsWidget(QWidget):
    back_to_main = pyqtSignal()
    open_avatar_selection = pyqtSignal()
    open_buy_premium = pyqtSignal()
    open_lucky_wheel = pyqtSignal()
    open_achievement = pyqtSignal()
    user_updated = pyqtSignal(dict)

    def __init__(self, user_data, db, app):
        super().__init__()
        self.user_data = user_data
        self.db = db
        self.app = app  # Reference to PhoenixApp for synced timer
        self.init_ui()

        # Auto-refresh timer - now every 100ms for smooth animation
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(100)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 15, 10, 15)
        layout.setSpacing(10)

        # Title
        title = QLabel("ACCOUNT")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Profile Section
        profile_layout = QHBoxLayout()
        profile_layout.setSpacing(8)

        # Avatar + Badges Container
        avatar_badges_layout = QVBoxLayout()
        avatar_badges_layout.setSpacing(8) # Space between avatar and badges
        avatar_badges_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # Avatar Container (69x69 for frame - 50% bigger than original 46)
        avatar_container = ClickableAvatarContainer()
        avatar_container.setFixedSize(69, 69)
        avatar_container.setStyleSheet("background-color: transparent;")
        avatar_container.clicked.connect(self.open_avatar_selection.emit)
        
        # Use absolute positioning for perfect control
        # Add widgets in order: background (bottom), avatar, frame (top)
        
        # 1. Background (68x68 centered) - original 45px *1.5
        self.background_lbl = QLabel(avatar_container)
        self.background_lbl.setFixedSize(68, 68)
        self.background_lbl.move(0, 0)  # (69-68)/2 = 0.5 → rounded to 0px
        self.background_lbl.setStyleSheet("background-color: #000000;")
        self.background_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.background_lbl.show()
        
        # 2. Avatar (60x60 centered, on top of background)
        self.avatar_lbl = QLabel(avatar_container)
        self.avatar_lbl.setFixedSize(60, 60)
        self.avatar_lbl.move(4, 4)  # (69-60)/2 = 4.5 → 4
        self.avatar_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.avatar_lbl.show()
        
        # 3. Frame (69x69, covers entire container, on top of everything)
        self.frame_lbl = QLabel(avatar_container)
        self.frame_lbl.setFixedSize(69, 69)
        self.frame_lbl.move(0, 0)
        self.frame_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.frame_lbl.show()

        avatar_badges_layout.addWidget(avatar_container)

        # Badges (36x36 each, 2px spacing)
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(2)
        badges_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.badge1_lbl = ClickableLabel()
        self.badge1_lbl.setFixedSize(36, 36)
        self.badge1_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge1_lbl.clicked.connect(self.open_avatar_selection.emit)
        badges_layout.addWidget(self.badge1_lbl)

        self.badge2_lbl = ClickableLabel()
        self.badge2_lbl.setFixedSize(36, 36)
        self.badge2_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge2_lbl.clicked.connect(self.open_avatar_selection.emit)
        badges_layout.addWidget(self.badge2_lbl)

        avatar_badges_layout.addLayout(badges_layout)
        profile_layout.addLayout(avatar_badges_layout)

        # User Info Text
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)  # No default spacing
        info_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.name_lv_lbl = QLabel()
        self.name_lv_lbl.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 16px;")
        self.name_lv_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # XP Bar
        self.xp_bar = QProgressBar()
        self.xp_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333333;
                border-radius: 3px;
                text-align: center;
                color: #ffffff;
                background-color: #1a1a1a;
            }
            QProgressBar::chunk {
                background-color: #ff2b2b;
                border-radius: 2px;
            }
        """)
        self.xp_bar.setFixedHeight(14)  # Smaller height
        
        # Next XP Timer Bar
        self.xp_timer_bar = QProgressBar()
        self.xp_timer_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333333;
                border-radius: 3px;
                text-align: center;
                color: transparent;
                background-color: #1a1a1a;
            }
            QProgressBar::chunk {
                background-color: #ffd700;
                border-radius: 2px;
            }
        """)
        self.xp_timer_bar.setFixedHeight(5)  # Much smaller height (5px)
        self.xp_timer_bar.setMaximum(10000)  # 10000 ms total
        self.xp_timer_bar.setValue(0)  # Starts empty
        self.xp_timer_bar.setTextVisible(False)  # Remove text

        self.rank_lbl = QLabel()
        self.rank_lbl.setStyleSheet("color: #8c8c8c; font-size: 12px;")
        self.rank_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.coins_lbl = QLabel()
        self.coins_lbl.setStyleSheet("color: #8c8c8c; font-size: 12px;")
        self.coins_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)

        info_layout.addWidget(self.name_lv_lbl)
        info_layout.addSpacing(4)  # Space between name and XP bar
        info_layout.addWidget(self.xp_bar)
        info_layout.addSpacing(1)  # Exactly 1px between XP bar and timer bar
        info_layout.addWidget(self.xp_timer_bar)
        info_layout.addSpacing(4)  # Space between timer bar and rank
        info_layout.addWidget(self.rank_lbl)
        info_layout.addWidget(self.coins_lbl)

        profile_layout.addLayout(info_layout)
        layout.addLayout(profile_layout)

        layout.addSpacing(15)
        
        # Premium Active Label
        self.premium_active_lbl = QLabel()
        self.premium_active_lbl.setStyleSheet("color: #ff2b2b; font-size: 11px;")
        self.premium_active_lbl.setWordWrap(True)
        layout.addWidget(self.premium_active_lbl)

        layout.addSpacing(5)

        # Buttons Section
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(5)

        # Row 1: Buy Premium + Lucky Wheel
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(5)
        row1_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Buy Premium Button
        buy_premium_btn = QPushButton("Buy Premium")
        buy_premium_btn.setFixedSize(120, 35)
        buy_premium_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff2b2b;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff4545;
            }
        """)
        buy_premium_btn.clicked.connect(self.open_buy_premium_dialog)
        row1_layout.addWidget(buy_premium_btn)

        # Lucky Wheel Button
        lucky_wheel_btn = QPushButton("Lucky Wheel")
        lucky_wheel_btn.setFixedSize(120, 35)
        lucky_wheel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd700;
                color: #000000;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ffe55c;
            }
        """)
        lucky_wheel_btn.clicked.connect(self.open_lucky_wheel.emit)
        row1_layout.addWidget(lucky_wheel_btn)

        buttons_layout.addLayout(row1_layout)

        # Row 2: Achievement Button (Placeholder)
        achievement_btn = QPushButton("Achievements")
        achievement_btn.setFixedSize(245, 35)
        achievement_btn.setStyleSheet("""
            QPushButton {
                background-color: #26d17d;
                color: #000000;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3ae08e;
            }
        """)
        achievement_btn.clicked.connect(self.open_achievement.emit)
        buttons_layout.addWidget(achievement_btn)

        layout.addLayout(buttons_layout)

        # Status Label (Hidden by default, used for errors)
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #ff2b2b; font-size: 11px;")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_lbl)

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

        # Initial UI refresh
        self.refresh_ui()

    def refresh_ui(self):
        # Refresh Avatar, Background, Frame, Badges
        self.refresh_avatar()

        # Refresh Labels
        name = self.user_data.get('name', 'User')
        level = self.user_data.get('level', 1)
        xp = self.user_data.get('xp', 0)
        max_xp = self.user_data.get('max_xp', 100)
        xp_perc = (xp / max_xp * 100) if max_xp > 0 else 0
        rank_name = self.db.get_rank_name(self.user_data.get('rank', 1))
        coins = self.user_data.get('coins', 0)

        self.name_lv_lbl.setText(f"{name}, Lv {level}")
        self.xp_bar.setMaximum(max_xp)
        self.xp_bar.setValue(xp)
        self.xp_bar.setFormat(f"{xp} / {max_xp} ({int(xp_perc)}%)")
        
        # Update XP timer bar using app's elapsed timer for perfect sync
        elapsed = self.app.xp_elapsed_timer.elapsed()
        # Ensure elapsed doesn't exceed 10000ms
        elapsed = min(elapsed, 10000)
        self.xp_timer_bar.setValue(elapsed)
        
        self.rank_lbl.setText(rank_name)
        self.coins_lbl.setText(f"Coins: {coins}")

        # Refresh Premium Active Timer
        premium_until = self.user_data.get('premium_until')
        if premium_until:
            from datetime import datetime, timezone
            if isinstance(premium_until, str):
                # Handle potential string dates if not converted by mongo driver
                try:
                    premium_until = datetime.fromisoformat(premium_until)
                except: pass

            # Ensure premium_until is offset-aware
            if premium_until.tzinfo is None:
                premium_until = premium_until.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)

            if premium_until > now:
                diff = premium_until - now
                days = diff.days
                hours, rem = divmod(diff.seconds, 3600)
                minutes, _ = divmod(rem, 60)
                self.premium_active_lbl.setText(f"Premium lasts: {days} Days, {hours} Hours, {minutes} Minutes")
                self.premium_active_lbl.show()
            else:
                self.premium_active_lbl.hide()
        else:
            self.premium_active_lbl.hide()

    def refresh_avatar(self):
        from PyQt6.QtGui import QMovie
        
        # Background (68x68)
        bg_path = self.user_data.get("equipped_background")
        if bg_path and os.path.exists(bg_path):
            if bg_path.lower().endswith(".gif"):
                self.bg_movie = get_cached_movie(bg_path, self.background_lbl.size())
                self.background_lbl.setMovie(self.bg_movie)
                self.bg_movie.start()
            else:
                pixmap = QPixmap(bg_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(68, 68, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.background_lbl.setPixmap(scaled)
        else:
            self.background_lbl.clear()
            self.background_lbl.setStyleSheet("background-color: #000000;")
        
        # Avatar (60x60)
        avatar_path = self.user_data.get("image")
        if avatar_path and os.path.exists(avatar_path):
            if avatar_path.lower().endswith(".gif"):
                self.avatar_movie = get_cached_movie(avatar_path, self.avatar_lbl.size())
                self.avatar_lbl.setMovie(self.avatar_movie)
                self.avatar_movie.start()
            else:
                pixmap = QPixmap(avatar_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(60, 60, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.avatar_lbl.setPixmap(scaled)
        else:
            self.avatar_lbl.clear()
        
        # Frame (69x69)
        frame_path = self.user_data.get("equipped_frame")
        if frame_path and os.path.exists(frame_path):
            if frame_path.lower().endswith(".gif"):
                self.frame_movie = get_cached_movie(frame_path, self.frame_lbl.size())
                self.frame_lbl.setMovie(self.frame_movie)
                self.frame_movie.start()
            else:
                pixmap = QPixmap(frame_path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(69, 69, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.frame_lbl.setPixmap(scaled)
        else:
            self.frame_lbl.clear()
        
        # Badges (36x36 each)
        badges = self.user_data.get("equipped_badges", [])
        if len(badges) > 0 and os.path.exists(badges[0]):
            name, desc = parse_badge_filename(badges[0])
            tooltip = f"{name}\n{desc}" if desc else name
            self.badge1_lbl.setStyleSheet("""
                QLabel {
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
            self.badge1_lbl.setToolTip(tooltip)
            if badges[0].lower().endswith(".gif"):
                self.badge1_movie = get_cached_movie(badges[0], self.badge1_lbl.size())
                self.badge1_lbl.setMovie(self.badge1_movie)
                self.badge1_movie.start()
            else:
                pixmap = QPixmap(badges[0])
                if not pixmap.isNull():
                    scaled = pixmap.scaled(36,36, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.badge1_lbl.setPixmap(scaled)
        else:
            self.badge1_lbl.clear()
            self.badge1_lbl.setToolTip("")
        
        if len(badges) > 1 and os.path.exists(badges[1]):
            name, desc = parse_badge_filename(badges[1])
            tooltip = f"{name}\n{desc}" if desc else name
            self.badge2_lbl.setStyleSheet("""
                QLabel {
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
            self.badge2_lbl.setToolTip(tooltip)
            if badges[1].lower().endswith(".gif"):
                self.badge2_movie = get_cached_movie(badges[1], self.badge2_lbl.size())
                self.badge2_lbl.setMovie(self.badge2_movie)
                self.badge2_movie.start()
            else:
                pixmap = QPixmap(badges[1])
                if not pixmap.isNull():
                    scaled = pixmap.scaled(36,36, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.badge2_lbl.setPixmap(scaled)
        else:
            self.badge2_lbl.clear()
            self.badge2_lbl.setToolTip("")

    def refresh_data(self):
        # Fetch fresh data from DB
        user = self.db.users.find_one({"_id": self.user_data["_id"]})
        if user:
            # Check for pending level ups
            if user.get("xp", 0) >= user.get("max_xp", 100):
                self.db.check_level_up(user["_id"])
                user = self.db.users.find_one({"_id": self.user_data["_id"]})

            self.user_data = user
            self.refresh_ui()
            self.user_updated.emit(self.user_data)
            self.status_lbl.setText("") # Clear status when data is refreshed

    def buy_premium(self, days):
        success, msg = self.db.buy_premium(self.user_data["_id"], days)
        if success:
            # User said to remove the "Premium extended" hint, so we just refresh
            self.refresh_data()
        else:
            self.status_lbl.setText(msg)
            self.status_lbl.setStyleSheet("color: #ff2b2b;")

    def open_buy_premium_dialog(self):
        self.open_buy_premium.emit()
