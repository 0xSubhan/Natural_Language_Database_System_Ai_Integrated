from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton,
    QHBoxLayout, QFileDialog, QLabel, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
import os, json
from app.db_connection import get_db_connection
from app.ui.postgres_dialog import PostgresConnectionDialog

RECENT_FILES_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "recent_files.json")
)

class DBBrowser(QWidget):
    db_opened = Signal(dict)
    table_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = None
        self.current_db_config = None
        self.setup_ui()
        self._load_recent_files()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.title_label = QLabel("Database Browser")
        self.title_label.setObjectName("sectionTitle")
        layout.addWidget(self.title_label)

        self.db_name_label = QLabel("No database loaded")
        self.db_name_label.setObjectName("dbSubtitle")
        layout.addWidget(self.db_name_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Tables")
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        layout.addWidget(self.tree)

        self.recent_label = QLabel("Recent Files")
        self.recent_label.setObjectName("schemaSectionLabel")
        layout.addWidget(self.recent_label)

        self.recent_list = QListWidget()
        self.recent_list.setObjectName("recentFilesList")
        self.recent_list.setMaximumHeight(100)
        self.recent_list.itemDoubleClicked.connect(self._on_recent_file_clicked)
        layout.addWidget(self.recent_list)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(6)

        self.btn_open = QPushButton("Open Database")
        self.btn_open.setObjectName("btnOpenDB")
        self.btn_open.setShortcut("Ctrl+O")
        self.btn_open.clicked.connect(self.on_open_db)

        self.btn_new = QPushButton("New Database")
        self.btn_new.setObjectName("btnNewDB")
        self.btn_new.setShortcut("Ctrl+N")
        self.btn_new.clicked.connect(self.on_new_db)

        self.btn_pg = QPushButton("Connect PG")
        self.btn_pg.setObjectName("btnConnectPG")
        self.btn_pg.clicked.connect(self.on_pg_connect)

        btn_layout.addWidget(self.btn_open)
        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_pg)
        layout.addLayout(btn_layout)

    def _on_tree_item_clicked(self, item, column):
        if item.parent() is None:
            text = item.text(0)
            table_name = text.split(" (")[0] if " (" in text else text
            self.table_selected.emit(table_name)

    def _load_recent_files(self):
        self.recent_files = []
        try:
            if os.path.exists(RECENT_FILES_PATH):
                with open(RECENT_FILES_PATH, "r") as f:
                    self.recent_files = json.load(f)
        except Exception:
            self.recent_files = []
        self._refresh_recent_list()

    def _save_recent_files(self):
        try:
            os.makedirs(os.path.dirname(RECENT_FILES_PATH), exist_ok=True)
            with open(RECENT_FILES_PATH, "w") as f:
                json.dump(self.recent_files[:5], f)
        except Exception:
            pass

    def _add_recent_file(self, path):
        self.recent_files = [p for p in self.recent_files if p != path]
        self.recent_files.insert(0, path)
        self.recent_files = self.recent_files[:5]
        self._save_recent_files()
        self._refresh_recent_list()

    def _refresh_recent_list(self):
        self.recent_list.clear()
        for path in self.recent_files:
            item = QListWidgetItem(os.path.basename(path))
            item.setToolTip(path)
            item.setData(Qt.UserRole, path)
            self.recent_list.addItem(item)

    def _on_recent_file_clicked(self, item):
        path = item.data(Qt.UserRole)
        if path and os.path.exists(path):
            self.load_database({"type": "sqlite", "path": path})

    def on_open_db(self):
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
        os.makedirs(data_dir, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(self, "Open SQLite Database", data_dir, "SQLite Databases (*.db *.sqlite);;All Files (*)")
        if path:
            self.load_database({"type": "sqlite", "path": path})

    def on_new_db(self):
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
        os.makedirs(data_dir, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "New SQLite Database", data_dir, "SQLite Databases (*.db *.sqlite);;All Files (*)")
        if path:
            if not path.endswith('.db') and not path.endswith('.sqlite'):
                path += '.db'
            self.load_database({"type": "sqlite", "path": path})

    def on_pg_connect(self):
        dialog = PostgresConnectionDialog(self)
        if dialog.exec():
            self.load_database(dialog.get_config())

    def load_database(self, config):
        self.current_db_config = config
        self.db = get_db_connection(config)
        try:
            self.db.connect(config)
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Connection Error", f"Failed to connect:\n{e}")
            self.db = None
            self.current_db_config = None
            return
        if config.get("type") == "sqlite":
            self.db_name_label.setText(os.path.basename(config.get("path", "")))
            self._add_recent_file(config["path"])
        else:
            self.db_name_label.setText(f"{config.get('dbname', 'postgres')} (PG)")
        self.refresh_tree()
        self.db_opened.emit(config)

    def refresh_tree(self):
        self.tree.clear()
        if not self.current_db_config or not self.db:
            return
        schema = self.db.get_schema()
        first_table = None
        for table, columns in schema.items():
            if first_table is None:
                first_table = table
            t_item = QTreeWidgetItem(self.tree)
            t_item.setText(0, f"{table} ({len(columns)} cols)")
            t_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
            for col in columns:
                c_item = QTreeWidgetItem(t_item)
                c_item.setText(0, f"{col['name']} ({col['type']})")
                c_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
        self.tree.expandAll()
        if first_table:
            self.table_selected.emit(first_table)

    def get_db_display_name(self):
        if not self.current_db_config:
            return ""
        if self.current_db_config.get("type") == "sqlite":
            return os.path.basename(self.current_db_config.get("path", ""))
        return self.current_db_config.get("dbname", "postgres")
