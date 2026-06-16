from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QStackedWidget, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QTimer, QElapsedTimer
from PyQt6.QtGui import QColor
from src.ui.base import DraggableWindow
from src.ui.auth import LoginWidget, RegisterWidget
from src.ui.main_view import MainWidget
from src.ui.account import AccountSettingsWidget, AvatarSelectionWidget, BuyPremiumWidget, BuyCoinsWidget
from src.ui.lucky_wheel import LuckyWheelWidget
from src.ui.chat import ChatWidget, InspectWidget
from src.ui.guides import GuidesWidget
from src.ui.auto_heal import AutoHealSettingsWidget
from src.ui.ultra_zoom import UltraZoomSettingsWidget
from src.ui.fast_mining import FastMiningSettingsWidget
from src.ui.auto_quest import AutoQuestSettingsWidget
from src.ui.app_settings import AppSettingsWidget
from src.ui.video_bg import VideoBackground
from src.logic.database import Database

class PhoenixApp(DraggableWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.init_ui()
        self.xp_elapsed_timer = QElapsedTimer()  # Track elapsed time since last XP
        self.xp_elapsed_timer.start()  # Start immediately
        # Apply non-activating style after window creation
        self.show()
        self.set_no_activate()

    def init_ui(self):
        self.setFixedSize(268, 420)
        
        # Main layout for the window
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Root widget to stack video and content
        self.root = QWidget(self)
        main_layout.addWidget(self.root)
        
        # Video Background (Bottom layer)
        self.video_bg = VideoBackground(r"c:\Users\havan\Downloads\Phoenix\src\videos\bg_main.mp4", self.root)
        self.video_bg.setFixedSize(268, 420)
        self.video_bg.lower()
        
        # Container (Top layer)
        # Border thickness = 2px
        self.container = QFrame(self.root)
        self.container.setObjectName("container")
        self.container.setGeometry(2, 2, 264, 416) # 268 - (2*2) = 264, 420 - (2*2) = 416
        
        # Enable dragging from the container
        self.container.mousePressEvent = self.mousePressEvent
        self.container.mouseMoveEvent = self.mouseMoveEvent
        self.container.mouseReleaseEvent = self.mouseReleaseEvent
        
        # Shadow effect (reduced for video border)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 200))
        self.container.setGraphicsEffect(shadow)

        self.stack = QStackedWidget(self.container)
        
        self.login_widget = LoginWidget(self.db)
        self.register_widget = RegisterWidget(self.db)
        
        self.stack.addWidget(self.login_widget)
        self.stack.addWidget(self.register_widget)
        
        self.login_widget.switch_to_register.connect(lambda: self.stack.setCurrentWidget(self.register_widget))
        self.login_widget.login_success.connect(self.on_login_success)
        self.register_widget.switch_to_login.connect(lambda: self.stack.setCurrentWidget(self.login_widget))

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.stack)

    def on_login_success(self, user_data):
        # Cleanup old widgets if they exist (e.g. from previous login)
        if hasattr(self, 'main_widget') and self.main_widget:
            self.main_widget.stop_threads()
            self.stack.removeWidget(self.main_widget)
            self.main_widget.deleteLater()

        self.user_data = user_data
        self.main_widget = MainWidget(user_data, self.db)
        self.account_widget = AccountSettingsWidget(user_data, self.db, self)
        self.chat_widget = ChatWidget(user_data, self.db)
        self.guides_widget = GuidesWidget(user_data, self.db)
        self.auto_heal_widget = AutoHealSettingsWidget(user_data, self.db)
        self.ultra_zoom_widget = UltraZoomSettingsWidget(user_data, self.db)
        self.fast_mining_widget = FastMiningSettingsWidget(user_data, self.db)
        self.auto_quest_widget = AutoQuestSettingsWidget(user_data, self.db)
        self.app_settings_widget = AppSettingsWidget(user_data, self.db)
        
        # Avatar Selection Widget
        self.avatar_widget = AvatarSelectionWidget(user_data, self.db)
        
        # Buy Coins and Buy Premium Widgets
        self.buy_premium_widget = BuyPremiumWidget(self.db, user_data)
        self.lucky_wheel_widget = LuckyWheelWidget(user_data, self.db)
        
        # Inspect Widget
        self.inspect_widget = InspectWidget(user_data, self.db)
        
        self.stack.addWidget(self.main_widget)
        self.stack.addWidget(self.account_widget)
        self.stack.addWidget(self.avatar_widget)
        self.stack.addWidget(self.chat_widget)
        self.stack.addWidget(self.guides_widget)
        self.stack.addWidget(self.auto_heal_widget)
        self.stack.addWidget(self.ultra_zoom_widget)
        self.stack.addWidget(self.fast_mining_widget)
        self.stack.addWidget(self.auto_quest_widget)
        self.stack.addWidget(self.app_settings_widget)
        self.stack.addWidget(self.buy_premium_widget)
        self.stack.addWidget(self.lucky_wheel_widget)
        self.stack.addWidget(self.inspect_widget)
        
        # Navigation
        self.main_widget.switch_to_account.connect(self.switch_to_account)
        self.main_widget.switch_to_chat.connect(lambda: self.stack.setCurrentWidget(self.chat_widget))
        self.main_widget.open_guides.connect(lambda: self.stack.setCurrentWidget(self.guides_widget))
        self.main_widget.open_auto_heal_settings.connect(lambda: self.stack.setCurrentWidget(self.auto_heal_widget))
        self.main_widget.open_ultra_zoom_settings.connect(lambda: self.stack.setCurrentWidget(self.ultra_zoom_widget))
        self.main_widget.open_fast_mining_settings.connect(lambda: self.stack.setCurrentWidget(self.fast_mining_widget))
        self.main_widget.open_auto_quest_settings.connect(lambda: self.stack.setCurrentWidget(self.auto_quest_widget))
        self.main_widget.open_app_settings.connect(lambda: self.stack.setCurrentWidget(self.app_settings_widget))
        
        self.account_widget.back_to_main.connect(lambda: self.stack.setCurrentWidget(self.main_widget))
        self.account_widget.open_avatar_selection.connect(self.open_avatar_selection)
        self.account_widget.open_buy_premium.connect(lambda: self.stack.setCurrentWidget(self.buy_premium_widget))
        self.account_widget.open_lucky_wheel.connect(self.open_lucky_wheel)
        
        self.avatar_widget.back_to_account.connect(lambda: self.stack.setCurrentWidget(self.account_widget))
        self.lucky_wheel_widget.back_to_main.connect(lambda: self.stack.setCurrentWidget(self.account_widget))
        self.lucky_wheel_widget.user_updated.connect(self.update_local_user_data)
        
        self.chat_widget.back_to_main.connect(lambda: self.stack.setCurrentWidget(self.main_widget))
        self.chat_widget.inspect_user.connect(self.open_inspect)
        
        self.guides_widget.back_to_main.connect(lambda: self.stack.setCurrentWidget(self.main_widget))
        
        self.auto_heal_widget.back_to_main.connect(lambda: self.stack.setCurrentWidget(self.main_widget))
        self.auto_heal_widget.settings_changed.connect(self.main_widget.auto_heal_mgr.reload_settings)
        
        self.ultra_zoom_widget.back_to_main.connect(lambda: self.stack.setCurrentWidget(self.main_widget))
        self.ultra_zoom_widget.zoom_changed.connect(self.main_widget.update_zoom_value)

        self.fast_mining_widget.back_to_main.connect(lambda: self.stack.setCurrentWidget(self.main_widget))
        self.auto_quest_widget.back_to_main.connect(lambda: self.stack.setCurrentWidget(self.main_widget))

        self.app_settings_widget.back_to_main.connect(lambda: self.stack.setCurrentWidget(self.main_widget))
        self.app_settings_widget.settings_changed.connect(self.apply_app_settings)
        
        self.buy_premium_widget.back_to_account.connect(self.switch_to_account)
        
        self.inspect_widget.back_to_chat.connect(lambda: self.stack.setCurrentWidget(self.chat_widget))

        # Initial apply of app settings
        self.apply_app_settings(self.app_settings_widget.settings)
        
        # Data synchronization
        self.account_widget.user_updated.connect(self.update_local_user_data)
        
        # Passive XP Timer - restart when user logs in so it's synced
        self.xp_timer = QTimer(self)
        self.xp_timer.timeout.connect(self.give_passive_xp)
        self.xp_elapsed_timer.restart()  # Restart elapsed timer on login
        self.xp_timer.start(10000)  # 10 seconds
        
        self.stack.setCurrentWidget(self.main_widget)

    def update_local_user_data(self, data):
        self.user_data = data
        self.main_widget.update_user_data(data)
        setattr(self.chat_widget, "user_data", data)

    def closeEvent(self, event):
        """Ensure all threads are stopped when the app is closed."""
        if hasattr(self, 'main_widget') and self.main_widget:
            self.main_widget.stop_threads()
        super().closeEvent(event)

    def apply_app_settings(self, settings):
        always_on_top = settings.get("always_on_top", True)
        self.set_always_on_top_state(always_on_top)
        
        # Define base flags that should always be present
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        
        if always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        
        self.setWindowFlags(flags)
        
        # We must call show() after changing flags
        self.show()
        
        # Re-apply NOACTIVATE style if mouse is not over the window
        # This is important because setWindowFlags resets the native window style
        if always_on_top:
            self.set_no_activate(True)
        else:
            self.set_no_activate(False)

    def give_passive_xp(self):
        if hasattr(self, 'user_data') and self.user_data:
            user_level = self.user_data.get("level", 1)
            xp_amount = max(1, user_level // 10)
            self.db.add_xp(self.user_data["_id"], xp_amount)
            # We don't necessarily need to refresh the UI every minute unless the user is looking at it,
            # but let's trigger a silent update to keep local data fresh
            new_data = self.db.users.find_one({"_id": self.user_data["_id"]})
            if new_data:
                self.update_local_user_data(new_data)
            # Reset the elapsed timer
            self.xp_elapsed_timer.restart()
            # Reset the account widget's XP timer if it exists
            if hasattr(self, 'account_widget'):
                self.account_widget.ms_until_next_xp = 10000

    def open_avatar_selection(self):
        # Refresh user data in avatar widget before showing it
        self.avatar_widget.refresh_user_data(self.account_widget.user_data)
        self.stack.setCurrentWidget(self.avatar_widget)

    def open_lucky_wheel(self):
        self.lucky_wheel_widget.refresh_user_data(self.user_data)
        self.stack.setCurrentWidget(self.lucky_wheel_widget)
        
    def open_inspect(self, user_data):
        # Remove old inspect widget
        self.stack.removeWidget(self.inspect_widget)
        self.inspect_widget.deleteLater()
        
        # Create new inspect widget with the user data
        self.inspect_widget = InspectWidget(user_data, self.db)
        self.stack.addWidget(self.inspect_widget)
        self.inspect_widget.back_to_chat.connect(lambda: self.stack.setCurrentWidget(self.chat_widget))
        
        self.stack.setCurrentWidget(self.inspect_widget)

    def switch_to_account(self):
        # Refresh data before showing the account section
        self.account_widget.refresh_data()
        self.stack.setCurrentWidget(self.account_widget)
