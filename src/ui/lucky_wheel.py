import math
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QToolTip
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty, QPointF, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap, QBrush, QPolygonF

POINTER_ANGLE = 90  # Qt pie coords: 12 o'clock (top)


def parse_badge_filename(path):
    filename = os.path.basename(path)
    if "@" in filename:
        name_part, desc_part = filename.split("@", 1)
        desc, ext = os.path.splitext(desc_part)
        return (name_part, desc)
    else:
        name, ext = os.path.splitext(filename)
        return (name, "")


def segment_index_at_pointer(rotation, segment_count):
    """Which segment center is closest to the fixed top pointer."""
    angle_per = 360.0 / segment_count
    best_index = 0
    best_dist = 360.0
    for i in range(segment_count):
        center = i * angle_per + angle_per / 2
        screen_angle = (center - rotation) % 360
        dist = min(abs(screen_angle - POINTER_ANGLE), 360 - abs(screen_angle - POINTER_ANGLE))
        if dist < best_dist:
            best_dist = dist
            best_index = i
    return best_index


def get_segment_index_at_pos(pos, cx, cy, rotation, segment_count):
    """Get the segment index at the given mouse position."""
    dx = pos.x() - cx
    dy = pos.y() - cy
    distance = math.hypot(dx, dy)
    if distance > (min(cx, cy) - 6):
        return None  # Outside the wheel
    # Compute angle from center
    angle_rad = math.atan2(-dy, dx)  # y is down in screen coords
    angle_deg = math.degrees(angle_rad)
    # Adjust for wheel rotation
    local_angle = (angle_deg + rotation) % 360
    angle_per = 360.0 / segment_count
    return int(local_angle // angle_per)


class WheelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rotation = 0.0
        self.segments = []
        self.setFixedSize(220, 220)
        self.setMouseTracking(True)  # Enable mouse tracking for hover events
        self.setStyleSheet("""
            QToolTip {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #ff2b2b;
                padding: 4px;
                font-size: 11px;
            }
        """)

    def get_rotation(self):
        return self._rotation

    def set_rotation(self, value):
        self._rotation = value
        self.update()

    rotation = pyqtProperty(float, get_rotation, set_rotation)

    def set_segments(self, segments):
        self.segments = segments
        self.update()

    def _segment_point(self, mid_angle, radius_factor):
        # Pies use painter.rotate(R) -> screen angle = local - R
        screen_angle = mid_angle - self._rotation
        rad = math.radians(screen_angle)
        r = self._radius * radius_factor
        return math.cos(rad) * r, -math.sin(rad) * r

    def mouseMoveEvent(self, event):
        if not self.segments or len(self.segments) == 0:
            super().mouseMoveEvent(event)
            return
        
        cx = self.width() / 2
        cy = self.height() / 2
        seg_idx = get_segment_index_at_pos(event.pos(), cx, cy, self._rotation, len(self.segments))
        
        if seg_idx is not None and 0 <= seg_idx < len(self.segments):
            seg = self.segments[seg_idx]
            if seg.get("type") == "badge":
                path = seg.get("icon_path", "")
                name, desc = parse_badge_filename(path)
                tooltip = f"{name}\n{desc}" if desc else name
                QToolTip.showText(event.globalPosition().toPoint(), tooltip, self)
            else:
                QToolTip.hideText()
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)
    
    def paintEvent(self, event):
        if not self.segments:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2
        radius = min(cx, cy) - 6
        self._radius = radius
        count = len(self.segments)
        angle_per = 360.0 / count

        colors = [
            QColor("#ff2b2b"), QColor("#ffd700"), QColor("#26d17d"), QColor("#4a90d9"),
            QColor("#ff6b35"), QColor("#9b59b6"), QColor("#e74c3c"), QColor("#f39c12"),
            QColor("#1abc9c"), QColor("#3498db"),
        ]

        painter.translate(cx, cy)
        painter.rotate(self._rotation)

        for i, seg in enumerate(self.segments):
            start_angle = i * angle_per
            color = colors[i % len(colors)]
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor("#0c0c0c"), 2))
            painter.drawPie(
                int(-radius), int(-radius), int(radius * 2), int(radius * 2),
                int(start_angle * 16), int(angle_per * 16)
            )

        painter.resetTransform()

        icon_size = 28
        for i, seg in enumerate(self.segments):
            mid_angle = i * angle_per + angle_per / 2
            icon_path = seg.get("icon_path")
            if not icon_path or not os.path.exists(icon_path):
                continue
            pixmap = QPixmap(icon_path)
            if pixmap.isNull():
                continue
            scaled = pixmap.scaled(
                icon_size, icon_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            ix, iy = self._segment_point(mid_angle, 0.78)
            half_w = scaled.width() // 2
            half_h = scaled.height() // 2
            painter.drawPixmap(int(cx + ix - half_w), int(cy + iy - half_h), scaled)

        painter.setBrush(QBrush(QColor("#ffffff")))
        painter.setPen(QPen(QColor("#ff2b2b"), 3))
        painter.drawEllipse(int(cx - 8), int(cy - 8), 16, 16)

        # Pointer at top — tip points down into the wheel
        painter.setBrush(QBrush(QColor("#ff2b2b")))
        painter.setPen(QPen(QColor("#0c0c0c"), 1))
        points = [
            (cx - 9, 2),
            (cx + 9, 2),
            (cx, 20),
        ]
        polygon = QPolygonF([QPointF(x, y) for x, y in points])
        painter.drawPolygon(polygon)


class LuckyWheelWidget(QWidget):
    back_to_main = pyqtSignal()
    user_updated = pyqtSignal(dict)

    def __init__(self, user_data, db):
        super().__init__()
        self.user_data = user_data
        self.db = db
        self.is_spinning = False
        self.init_ui()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(1000)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        title = QLabel("LUCKY WHEEL")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px;")
        layout.addWidget(title)

        self.spins_lbl = QLabel()
        self.spins_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spins_lbl.setStyleSheet("color: #ffd700; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.spins_lbl)

        self.timer_lbl = QLabel()
        self.timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_lbl.setStyleSheet("color: #8c8c8c; font-size: 10px;")
        layout.addWidget(self.timer_lbl)

        wheel_container = QHBoxLayout()
        wheel_container.addStretch()
        self.wheel = WheelWidget()
        wheel_container.addWidget(self.wheel)
        wheel_container.addStretch()
        layout.addLayout(wheel_container)

        self.prize_lbl = QLabel()
        self.prize_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prize_lbl.setStyleSheet("color: #26d17d; font-size: 11px; font-weight: bold;")
        self.prize_lbl.setWordWrap(True)
        layout.addWidget(self.prize_lbl)

        self.spin_btn = QPushButton("SPIN")
        self.spin_btn.setObjectName("primary_btn")
        self.spin_btn.setFixedHeight(36)
        self.spin_btn.clicked.connect(self.on_spin)
        layout.addWidget(self.spin_btn)

        back_btn = QPushButton("BACK")
        back_btn.setObjectName("link_btn_red")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.back_to_main.emit)

        back_container = QHBoxLayout()
        back_container.addStretch()
        back_container.addWidget(back_btn)
        back_container.addStretch()
        layout.addLayout(back_container)

        self.refresh_status()

    def refresh_user_data(self, user_data):
        self.user_data = user_data
        self.refresh_status()

    def refresh_status(self):
        status = self.db.get_wheel_status(self.user_data["_id"])
        if not status:
            return

        remaining = status["spins_remaining"]
        max_spins = status["max_spins"]
        self.spins_lbl.setText(f"Spins: {remaining}/{max_spins}")

        seconds = status["seconds_until_refresh"]
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        self.timer_lbl.setText(f"Refresh in {hours:02d}:{minutes:02d}:{secs:02d}")

        if not self.is_spinning:
            self.wheel.set_segments(status["segments"])
            self.spin_btn.setEnabled(remaining > 0)
            if remaining <= 0:
                self.spin_btn.setText("NO SPINS")
            else:
                self.spin_btn.setText("SPIN")

    def _compute_target_rotation(self, prize_index, segment_count):
        angle_per = 360.0 / segment_count
        prize_center = prize_index * angle_per + angle_per / 2
        target_mod = (prize_center - POINTER_ANGLE) % 360
        current = self.wheel.rotation
        current_mod = current % 360
        delta = (target_mod - current_mod) % 360
        if delta < 1:
            delta = 360
        return current + 360 * 5 + delta

    def on_spin(self):
        if self.is_spinning:
            return

        status = self.db.get_wheel_status(self.user_data["_id"])
        if not status or status["spins_remaining"] <= 0:
            return

        segments = status["segments"]
        success, message, prize_index, prize, spin_segments = self.db.spin_wheel(self.user_data["_id"])
        if not success:
            self.prize_lbl.setStyleSheet("color: #ff2b2b; font-size: 11px; font-weight: bold;")
            self.prize_lbl.setText(message)
            self.refresh_status()
            return

        self.is_spinning = True
        self.spin_btn.setEnabled(False)
        self.prize_lbl.setText("")

        count = len(spin_segments)
        target_angle = self._compute_target_rotation(prize_index, count)

        self.anim = QPropertyAnimation(self.wheel, b"rotation")
        self.anim.setDuration(4000)
        self.anim.setStartValue(self.wheel.rotation)
        self.anim.setEndValue(target_angle)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(lambda: self._on_spin_finished(message, prize, prize_index, count, target_angle))
        self.anim.start()

    def _on_spin_finished(self, message, prize, prize_index, segment_count, target_angle):
        self.is_spinning = False
        visual_index = segment_index_at_pointer(target_angle, segment_count)
        if visual_index != prize_index:
            print(
                f"[LuckyWheel] pointer mismatch: prize_index={prize_index}, "
                f"visual_index={visual_index}, rotation={target_angle}"
            )
        self.prize_lbl.setStyleSheet("color: #26d17d; font-size: 11px; font-weight: bold;")
        self.prize_lbl.setText(message)

        user = self.db.users.find_one({"_id": self.user_data["_id"]})
        if user:
            self.user_data = user
            self.user_updated.emit(user)

        self.refresh_status()
