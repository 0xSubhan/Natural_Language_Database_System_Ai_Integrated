from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton, QHBoxLayout, QFileDialog
)
from PySide6.QtCore import Qt, Signal
import os
from app.db_connection import get_db_connection
from app.ui.postgres_dialog import PostgresConnectionDialog

class DBBrowser(QWidget):
    # Signal emitted when a database is opened (passes the config dict)
    db_opened = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = None
        self.current_db_config = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tree Widget for tables and schemas
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Database Schema")
        layout.addWidget(self.tree)

        # Buttons layout
        btn_layout = QHBoxLayout()
        
        self.btn_open = QPushButton("Open DB")
        self.btn_open.setShortcut("Ctrl+O")
        self.btn_open.clicked.connect(self.on_open_db)
        
        self.btn_new = QPushButton("New DB")
        self.btn_new.setShortcut("Ctrl+N")
        self.btn_new.clicked.connect(self.on_new_db)

        self.btn_pg = QPushButton("Connect PG")
        self.btn_pg.clicked.connect(self.on_pg_connect)
        
        btn_layout.addWidget(self.btn_open)
        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_pg)
        layout.addLayout(btn_layout)

    def on_open_db(self):
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
        os.makedirs(data_dir, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self, "Open SQLite Database", data_dir, "SQLite Databases (*.db *.sqlite);;All Files (*)"
        )
        if path:
            self.load_database({"type": "sqlite", "path": path})

    def on_new_db(self):
        # Default save location is data/ folder
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
        os.makedirs(data_dir, exist_ok=True)
        
        path, _ = QFileDialog.getSaveFileName(
            self, "New SQLite Database", data_dir, "SQLite Databases (*.db *.sqlite);;All Files (*)"
        )
        if path:
            if not path.endswith('.db') and not path.endswith('.sqlite'):
                path += '.db'
            self.load_database({"type": "sqlite", "path": path})

    def on_pg_connect(self):
        dialog = PostgresConnectionDialog(self)
        if dialog.exec():
            config = dialog.get_config()
            self.load_database(config)

    def load_database(self, config: dict):
        self.current_db_config = config
        self.db = get_db_connection(config)
        try:
            self.db.connect(config)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to database:\n{str(e)}")
            self.db = None
            self.current_db_config = None
            return
            
        self.refresh_tree()
        self.db_opened.emit(config)

    def refresh_tree(self):
        self.tree.clear()
        if not self.current_db_config or not self.db:
            return
            
        schema = self.db.get_schema()
        for table, columns in schema.items():
            table_item = QTreeWidgetItem(self.tree)
            table_item.setText(0, table)
            table_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
            
            for col in columns:
                col_item = QTreeWidgetItem(table_item)
                col_item.setText(0, f"{col['name']} ({col['type']})")
                col_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
                
        self.tree.expandAll()
