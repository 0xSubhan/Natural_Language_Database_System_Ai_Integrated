from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt

class SafetyDialog(QDialog):
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Warning: Destructive Operation")
        self.setModal(True)
        self.setup_ui(message)

    def setup_ui(self, message: str):
        layout = QVBoxLayout(self)
        
        # Warning icon/text
        warning_label = QLabel("⚠️ DESTRUCTIVE QUERY DETECTED")
        warning_label.setStyleSheet("color: #ff3b30; font-weight: bold; font-size: 15px;")
        warning_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(warning_label)
        
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)
        
        confirm_label = QLabel("Are you sure you want to execute this query?")
        layout.addWidget(confirm_label)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setStyleSheet("background-color: #e5e5ea; color: #1d1d1f; border: none;")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_confirm = QPushButton("Yes, Delete")
        self.btn_confirm.setStyleSheet("background-color: #ff3b30; color: #ffffff; border: none; font-weight: bold;")
        self.btn_confirm.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        
        layout.addLayout(btn_layout)
