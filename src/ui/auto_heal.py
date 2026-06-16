from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSpinBox, QPushButton, QFrame, QScrollArea, 
                             QComboBox, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal

class ConditionWidget(QFrame):
    delete_clicked = pyqtSignal(int)
    
    def __init__(self, index, data):
        super().__init__()
        self.index = index
        self.data = data
        self.init_ui()

    def init_ui(self):
        self.setObjectName("condition_item")
        self.setStyleSheet("""
            QFrame#condition_item {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 4px;
                margin-bottom: 5px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Display: Stat Operator Threshold (Comparison) -> Key
        stat = self.data.get("stat", "HP")
        op = self.data.get("operator", "<=")
        val = self.data.get("value", 50)
        unit = "%" if self.data.get("comparison") == "Percent" else ""
        key = self.data.get("key", "q")
        
        text = f"{stat} {op} {val}{unit} -> {key.upper()}"
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #ffffff; font-size: 11px;")
        layout.addWidget(lbl)
        
        layout.addStretch()
        
        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet("""
            QPushButton {
                color: #8c2b2b;
                background: transparent;
                font-weight: bold;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                color: #ff2b2b;
            }
        """)
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.index))
        layout.addWidget(del_btn)

class AddConditionWidget(QWidget):
    condition_added = pyqtSignal(dict)
    back_clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 5)
        layout.setSpacing(4)

        # Stat
        layout.addWidget(self.create_label("Stat"))
        self.stat_combo = QComboBox()
        self.stat_combo.addItems(["Health (HP)", "Mana (MP)"])
        layout.addWidget(self.stat_combo)

        # Comparison
        layout.addWidget(self.create_label("Comparison"))
        self.comp_combo = QComboBox()
        self.comp_combo.addItems(["Percent", "Absolute"])
        layout.addWidget(self.comp_combo)

        # Operator
        layout.addWidget(self.create_label("Operator"))
        self.op_combo = QComboBox()
        self.op_combo.addItems(["<", "<=", ">", ">=", "=="])
        layout.addWidget(self.op_combo)

        # Threshold
        layout.addWidget(self.create_label("Threshold"))
        self.val_input = QLineEdit()
        self.val_input.setPlaceholderText("e.g. 50")
        self.val_input.setText("50")
        layout.addWidget(self.val_input)

        # Key
        layout.addWidget(self.create_label("Key"))
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("e.g. q")
        self.key_input.setText("q")
        layout.addWidget(self.key_input)

        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("SAVE")
        save_btn.setObjectName("action_btn_green")
        save_btn.clicked.connect(self.save)
        
        back_btn = QPushButton("CANCEL")
        back_btn.setObjectName("link_btn_red")
        back_btn.clicked.connect(self.back_clicked.emit)
        
        btn_layout.addWidget(back_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)
        layout.addStretch()

    def create_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #8c8c8c; font-size: 10px; font-weight: bold; margin-top: 2px;")
        return lbl

    def save(self):
        data = {
            "stat": "HP" if "Health" in self.stat_combo.currentText() else "MP",
            "comparison": self.comp_combo.currentText(),
            "operator": self.op_combo.currentText(),
            "value": int(self.val_input.text() if self.val_input.text().isdigit() else 50),
            "key": self.key_input.text().lower()
        }
        self.condition_added.emit(data)

class AutoHealSettingsWidget(QWidget):
    back_to_main = pyqtSignal()
    settings_changed = pyqtSignal()

    def __init__(self, user_data, db):
        super().__init__()
        self.user_data = user_data
        self.db = db
        self.settings = self.db.get_auto_heal_settings(user_data["_id"])
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        # Container for different views (Settings vs Add Condition)
        self.stack = QWidget()
        self.stack_layout = QVBoxLayout(self.stack)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        
        # View 1: Main Settings
        self.settings_view = QWidget()
        self.setup_settings_view()
        
        # View 2: Add Condition
        self.add_view = AddConditionWidget()
        self.add_view.condition_added.connect(self.add_condition)
        self.add_view.back_clicked.connect(self.show_settings)
        self.add_view.hide()
        
        self.stack_layout.addWidget(self.settings_view)
        self.stack_layout.addWidget(self.add_view)
        
        self.main_layout.addWidget(self.stack)

        # Back Button
        back_btn = QPushButton("BACK")
        back_btn.setObjectName("link_btn_red")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.back_to_main.emit)

        back_container = QHBoxLayout()
        back_container.addStretch()
        back_container.addWidget(back_btn)
        back_container.addStretch()
        self.main_layout.addLayout(back_container)

    def setup_settings_view(self):
        layout = QVBoxLayout(self.settings_view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Header (Only in settings view)
        header = QLabel("Auto Heal Settings")
        header.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(header)

        # Interval
        layout.addWidget(QLabel("Check Interval (ms)", styleSheet="color: #8c8c8c; font-size: 12px;"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 5000)
        self.interval_spin.setSingleStep(100)
        self.interval_spin.setValue(self.settings.get("interval", 500))
        self.interval_spin.valueChanged.connect(self.save_settings)
        layout.addWidget(self.interval_spin)

        # Conditions Header
        cond_header_layout = QHBoxLayout()
        cond_header_layout.addWidget(QLabel("Conditions", styleSheet="color: #8c8c8c; font-size: 12px;"))
        
        add_btn = QPushButton("+ Condition")
        add_btn.setStyleSheet("""
            QPushButton {
                color: #8c8c8c;
                background: transparent;
                font-size: 11px;
                border: none;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.show_add_view)
        cond_header_layout.addWidget(add_btn)
        layout.addLayout(cond_header_layout)

        # Conditions List
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background-color: #000000; border: 1px solid #333333; border-radius: 4px;")
        self.scroll.setMinimumHeight(150)
        
        self.scroll_content = QWidget()
        self.cond_layout = QVBoxLayout(self.scroll_content)
        self.cond_layout.setContentsMargins(5, 5, 5, 5)
        self.cond_layout.setSpacing(5)
        self.cond_layout.addStretch()
        
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)
        
        self.refresh_conditions()

    def show_add_view(self):
        self.settings_view.hide()
        self.back_btn_container.hide()
        self.add_view.show()

    def show_settings(self):
        self.add_view.hide()
        self.settings_view.show()
        self.back_btn_container.show()

    def refresh_conditions(self):
        # Clear current list
        while self.cond_layout.count() > 1:
            item = self.cond_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        conditions = self.settings.get("conditions", [])
        if not conditions:
            empty_lbl = QLabel("No Conditions")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #444444; font-size: 12px; margin-top: 50px;")
            self.cond_layout.insertWidget(0, empty_lbl)
        else:
            for i, cond in enumerate(conditions):
                w = ConditionWidget(i, cond)
                w.delete_clicked.connect(self.remove_condition)
                self.cond_layout.insertWidget(i, w)

    def add_condition(self, data):
        self.settings["conditions"].append(data)
        self.save_settings()
        self.refresh_conditions()
        self.show_settings()

    def remove_condition(self, index):
        if 0 <= index < len(self.settings["conditions"]):
            self.settings["conditions"].pop(index)
            self.save_settings()
            self.refresh_conditions()

    def save_settings(self):
        self.settings["interval"] = self.interval_spin.value()
        self.db.save_auto_heal_settings(self.user_data["_id"], self.settings)
        self.settings_changed.emit()
