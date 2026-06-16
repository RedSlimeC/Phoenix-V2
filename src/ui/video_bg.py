import cv2
import numpy as np
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap

class VideoBackground(QLabel):
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        
        # Lower resolution for better performance if needed, 
        # but for a border it should be fine.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        
        # Calculate delay based on video FPS
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0: fps = 30
        self.timer.start(int(1000 / fps))
        
        self.setScaledContents(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            # Loop the video
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret: return

        # Convert OpenCV BGR to RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create QImage from frame
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Convert to Pixmap and display
        pixmap = QPixmap.fromImage(q_img)
        
        # Round the corners of the video pixmap
        rounded_pixmap = QPixmap(pixmap.size())
        rounded_pixmap.fill(Qt.GlobalColor.transparent)
        
        from PyQt6.QtGui import QPainter, QPainterPath
        painter = QPainter(rounded_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), 12, 12)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        
        self.setPixmap(rounded_pixmap)

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()
