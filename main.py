import sys
from PyQt6.QtWidgets import QApplication
from src.app import PhoenixApp
from src.ui.startup import StartupWidget
from src.styles.theme import STYLESHEET


class AppLauncher:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyleSheet(STYLESHEET)
        self.main_window = None
        
        self.startup_widget = StartupWidget()
        self.startup_widget.start_app.connect(self.launch_main_app)
        self.startup_widget.show()
    
    def launch_main_app(self):
        self.startup_widget.close()
        self.main_window = PhoenixApp()
        self.main_window.show()


if __name__ == "__main__":
    launcher = AppLauncher()
    sys.exit(launcher.app.exec())
