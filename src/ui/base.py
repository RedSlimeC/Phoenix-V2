from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint
import ctypes

class DraggableWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Added Qt.WindowType.Window to ensure it shows up in the taskbar
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                           Qt.WindowType.WindowStaysOnTopHint |
                           Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._dragging = False
        self._drag_pos = QPoint()
        self._always_on_top = True # Default state

    def set_always_on_top_state(self, state):
        """Helper to track if always on top is active."""
        self._always_on_top = state

    def set_no_activate(self, enable=True):
        """Sets the window to not take focus when clicked (Windows only)."""
        GWL_EXSTYLE = -20
        WS_EX_NOACTIVATE = 0x08000000
        
        hwnd = self.winId().__int__()
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        
        if enable:
            new_style = style | WS_EX_NOACTIVATE
        else:
            new_style = style & ~WS_EX_NOACTIVATE
            
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)

    def enterEvent(self, event):
        # When mouse enters, allow the window to become active if clicked
        self.set_no_activate(False)
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Only prevent focus theft if Always on Top is active
        # If it's OFF, the user wants it to behave like a normal window
        if self._always_on_top:
            self.set_no_activate(True)
        else:
            self.set_no_activate(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def contextMenuEvent(self, event):
        # Context menu with "Close" disabled as requested
        pass
