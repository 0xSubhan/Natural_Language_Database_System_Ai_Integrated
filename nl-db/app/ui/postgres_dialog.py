from PySide6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout

class PostgresConnectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to PostgreSQL")
        self.resize(300, 200)
        self.setStyleSheet("""
            QDialog { background-color: #f5f5f5; color: #333333; }
            QLabel { color: #333333; }
            QLineEdit { background-color: #ffffff; color: #333333; border: 1px solid #cccccc; border-radius: 4px; padding: 4px; }
            QPushButton { background-color: #e0e0e0; color: #333333; border: 1px solid #cccccc; border-radius: 4px; padding: 6px; }
            QPushButton:hover { background-color: #d0d0d0; }
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.host_edit = QLineEdit("localhost")
        self.port_edit = QLineEdit("5432")
        self.user_edit = QLineEdit("postgres")
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.dbname_edit = QLineEdit()

        form.addRow("Host:", self.host_edit)
        form.addRow("Port:", self.port_edit)
        form.addRow("Username:", self.user_edit)
        form.addRow("Password:", self.password_edit)
        form.addRow("Database:", self.dbname_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Connect")
        self.btn_cancel = QPushButton("Cancel")
        btn_layout.addWidget(self.btn_connect)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_connect.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        layout.addLayout(btn_layout)

    def get_config(self) -> dict:
        return {
            "type": "postgres",
            "host": self.host_edit.text().strip(),
            "port": int(self.port_edit.text().strip() or 5432),
            "user": self.user_edit.text().strip(),
            "password": self.password_edit.text(),
            "dbname": self.dbname_edit.text().strip()
        }
