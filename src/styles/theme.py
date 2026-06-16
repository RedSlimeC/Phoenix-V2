STYLESHEET = """
QWidget {
    background-color: #1e1e1e;
    color: #ffffff;
    font-family: 'Segoe UI', sans-serif;
}

QFrame#container {
    background-color: #1e1e1e;
    border: none;
    border-radius: 8px;
}

QLabel#title {
    font-size: 22px;
    font-weight: 900;
    color: #ffffff;
    margin-bottom: 5px;
    letter-spacing: 1px;
}

QLabel#label {
    color: #8c8c8c;
    font-size: 11px;
    font-weight: bold;
    margin-bottom: 5px;
    letter-spacing: 0.5px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QLineEdit {
    background-color: #262626;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 25px;
    color: #ffffff;
    font-size: 12px;
    margin-bottom: 10px;
}

QLineEdit:focus {
    border: 1px solid #ff2b2b;
}

QPushButton#primary_btn {
    background-color: #ff2b2b;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 10px;
    font-size: 15px;
    font-weight: 800;
}

QPushButton#primary_btn:hover {
    background-color: #ff4545;
}

QPushButton#link_btn {
    background-color: transparent;
    color: #8c8c8c;
    border: none;
    font-size: 13px;
}

QPushButton#link_btn_red {
    background-color: transparent;
    color: #ff2b2b;
    border: none;
    font-size: 13px;
    font-weight: bold;
}

/* Circle buttons */
QPushButton#circle_red {
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #ff2b2b, stop:1 #cc0000);
    border-radius: 15px;
    min-width: 30px;
    min-height: 30px;
    color: white;
    font-size: 14px;
    border: none;
}

QPushButton#circle_blue {
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #3b82f6, stop:1 #1d4ed8);
    border-radius: 15px;
    min-width: 30px;
    min-height: 30px;
    color: white;
    font-size: 14px;
    border: none;
}

QPushButton#circle_lightblue {
    background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #38bdf8, stop:1 #0ea5e9);
    border-radius: 15px;
    min-width: 30px;
    min-height: 30px;
    color: white;
    font-size: 14px;
    border: none;
}

/* New UI Styles */
QProgressBar {
    border: none;
    border-radius: 0px;
    background-color: #333333;
    text-align: center;
    color: white;
    font-weight: bold;
    font-size: 11px;
    height: 22px;
}

QProgressBar#hp_bar::chunk {
    background-color: #ff3333;
}

QProgressBar#mp_bar::chunk {
    background-color: #3366ff;
}

QLabel#char_name_display {
    color: #ff3333;
    font-weight: bold;
    font-size: 14px;
    letter-spacing: 1px;
}

QLabel#stone_lbl {
    color: #cccccc;
    font-size: 10px;
    font-weight: bold;
}

QLabel#stone_val {
    color: #ffffff;
    font-size: 10px;
    font-weight: bold;
}

/* Feature Toggle Switch */
QWidget#toggle_container {
    background-color: #000000;
    border: 1px solid #333333;
    border-radius: 4px;
}

/* Base button style for ON/OFF */
QPushButton.toggle_btn {
    border: none;
    border-radius: 3px;
    font-size: 10px;
    font-weight: bold;
}

/* Specific state styles using property-based matching or object names */
QPushButton#toggle_on_active {
    background-color: #26d17d;
    color: #ffffff;
}

QPushButton#toggle_off_inactive {
    background-color: transparent;
    color: #ffffff;
}

QPushButton#toggle_off_active {
    background-color: #8c2b2b;
    color: #ffffff;
}

QPushButton#toggle_on_inactive {
    background-color: transparent;
    color: #ffffff;
}

QLabel#feature_name {
    color: #ffffff;
    font-size: 12px;
}

QLabel#feature_name_locked {
    color: #555555;
    font-size: 12px;
}

QLabel#premium_hint {
    color: #ff3333;
    font-size: 10px;
    font-weight: bold;
}

QLabel#settings_icon {
    color: #999999;
    font-size: 14px;
}

QFrame#red_separator {
    background-color: #ff2b2b;
    max-height: 1px;
    min-height: 1px;
    border: none;
}

QFrame#feature_separator {
    background-color: #2a2a2a;
    max-height: 1px;
    min-height: 1px;
    border: none;
}

QComboBox {
    background-color: #262626;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 5px;
    color: #ffffff;
}

QComboBox::drop-down {
    border: none;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #8c8c8c;
    margin-right: 10px;
}

QSpinBox {
    background-color: #262626;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 5px;
    color: #ffffff;
}

QPushButton#action_btn_green {
    background-color: #26d17d;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton#action_btn_green:hover {
    background-color: #2edb85;
}
"""
