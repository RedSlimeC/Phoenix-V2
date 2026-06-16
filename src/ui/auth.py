from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

class LoginWidget(QWidget):
    switch_to_register = pyqtSignal()
    login_success = pyqtSignal(dict)

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(5)

        # Logo/Header
        logo_layout = QHBoxLayout()
        logo_layout.setContentsMargins(0, 0, 0, 5)
        
        # Simulating the logo in the image
        logo_container = QWidget()
        logo_container_layout = QHBoxLayout(logo_container)
        logo_container_layout.setContentsMargins(0, 0, 0, 0)
        logo_container_layout.setSpacing(5)
        
        logo_icon = QLabel("🔥") # Phoenix emoji as placeholder for the icon
        logo_icon.setStyleSheet("font-size: 18px;")
        
        logo_text = QLabel("Phoenix")
        logo_text.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold; letter-spacing: 0.5px;")
        
        logo_container_layout.addWidget(logo_icon)
        logo_container_layout.addWidget(logo_text)
        
        logo_layout.addStretch()
        logo_layout.addWidget(logo_container)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)

        # title removed to save space

        # Inputs
        layout.addWidget(QLabel("ACCOUNTNAME / EMAIL", objectName="label"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name or Email")
        self.name_input.returnPressed.connect(self.handle_login)
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("PASSWORD", objectName="label"))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("********")
        self.pass_input.returnPressed.connect(self.handle_login)
        layout.addWidget(self.pass_input)

        layout.addSpacing(10)

        # Login Button
        login_btn = QPushButton("LOGIN")
        login_btn.setObjectName("primary_btn")
        login_btn.clicked.connect(self.handle_login)
        layout.addWidget(login_btn)

        # Error Message Label
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #ff2b2b; font-size: 11px; font-weight: bold;")
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_lbl)

        # Register Link
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(0)
        
        no_account_label = QLabel("Don't have an account?")
        no_account_label.setStyleSheet("color: #888888; font-size: 12px;")
        no_account_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(no_account_label)

        register_btn = QPushButton("Register")
        register_btn.setObjectName("link_btn_red")
        register_btn.clicked.connect(self.switch_to_register.emit)
        footer_layout.addWidget(register_btn)
        
        layout.addLayout(footer_layout)
        layout.addStretch()
        self.setLayout(layout)

    def handle_login(self):
        self.error_lbl.setText("")
        if self.db.users is None:
            self.error_lbl.setText("Database Connection Error")
            return
        name = self.name_input.text()
        password = self.pass_input.text()
        success, result = self.db.authenticate_user(name, password)
        if success:
            self.login_success.emit(result)
        else:
            self.error_lbl.setText(str(result))

class RegisterWidget(QWidget):
    switch_to_login = pyqtSignal()

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(5)

        # title removed to save space

        layout.addWidget(QLabel("ACCOUNTNAME", objectName="label"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Choose a name")
        self.name_input.returnPressed.connect(self.handle_register)
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("EMAIL", objectName="label"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@mail.com")
        self.email_input.returnPressed.connect(self.handle_register)
        layout.addWidget(self.email_input)

        layout.addWidget(QLabel("PASSWORD", objectName="label"))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("********")
        self.pass_input.returnPressed.connect(self.handle_register)
        layout.addWidget(self.pass_input)

        layout.addWidget(QLabel("CONFIRM PASSWORD", objectName="label"))
        self.confirm_pass_input = QLineEdit()
        self.confirm_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pass_input.setPlaceholderText("********")
        self.confirm_pass_input.returnPressed.connect(self.handle_register)
        layout.addWidget(self.confirm_pass_input)

        # register button and footer with less spacing
        register_btn = QPushButton("CREATE ACCOUNT")
        register_btn.setObjectName("primary_btn")
        register_btn.clicked.connect(self.handle_register)
        layout.addWidget(register_btn)

        # Error Message Label
        self.error_lbl = QLabel("")
        self.error_lbl.setStyleSheet("color: #ff2b2b; font-size: 11px; font-weight: bold;")
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error_lbl)

        back_btn = QPushButton("Back to Login")
        back_btn.setObjectName("link_btn")
        back_btn.clicked.connect(self.switch_to_login.emit)
        layout.addWidget(back_btn)

        layout.addStretch()
        self.setLayout(layout)

    def handle_register(self):
        self.error_lbl.setText("")
        if self.db.users is None:
            self.error_lbl.setText("Database Connection Error")
            return
        name = self.name_input.text()
        email = self.email_input.text()
        password = self.pass_input.text()
        confirm_password = self.confirm_pass_input.text()

        if password != confirm_password:
            self.error_lbl.setText("Passwords do not match")
            return

        success, message = self.db.create_user(name, email, password)
        if success:
            self.switch_to_login.emit()
        else:
            self.error_lbl.setText(str(message))
