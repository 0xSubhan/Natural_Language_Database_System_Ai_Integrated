from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QWidget, QVBoxLayout, QLabel,
    QMenuBar, QStatusBar, QFrame, QHBoxLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from app.ui.db_browser import DBBrowser
from app.ui.query_panel import QueryPanel
from app.ui.schema_inspector import SchemaInspector


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NL-DB — Natural Language Database Manager")
        self.resize(1200, 700)
        self._setup_menu_bar()
        self._setup_info_bar()
        self._setup_ui()
        self._setup_status_bar()
        self._connect_signals()

    # ── Menu Bar ──────────────────────────────────────────────
    def _setup_menu_bar(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("File")

        open_act = QAction("Open Database", self)
        open_act.setShortcut("Ctrl+O")
        file_menu.addAction(open_act)

        new_act = QAction("New Database", self)
        new_act.setShortcut("Ctrl+N")
        file_menu.addAction(new_act)

        pg_act = QAction("Connect PostgreSQL", self)
        file_menu.addAction(pg_act)

        file_menu.addSeparator()

        exit_act = QAction("Exit", self)
        exit_act.setShortcut("Ctrl+Q")
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # Store actions to wire later
        self._open_act = open_act
        self._new_act = new_act
        self._pg_act = pg_act

        # Edit
        mb.addMenu("Edit")

        # View
        view_menu = mb.addMenu("View")
        self._toggle_schema_act = QAction("Toggle Schema Inspector", self)
        self._toggle_schema_act.setShortcut("Ctrl+I")
        view_menu.addAction(self._toggle_schema_act)

        toggle_sql_act = QAction("Toggle SQL Panel", self)
        toggle_sql_act.setShortcut("Ctrl+S")
        view_menu.addAction(toggle_sql_act)
        self._toggle_sql_act = toggle_sql_act

        # Settings
        mb.addMenu("Settings")

        # Help
        mb.addMenu("Help")

    # ── Info Toolbar ──────────────────────────────────────────
    def _setup_info_bar(self):
        self.info_bar = QFrame()
        self.info_bar.setObjectName("infoBar")
        self.info_bar.setFixedHeight(30)
        info_layout = QHBoxLayout(self.info_bar)
        info_layout.setContentsMargins(12, 0, 12, 0)

        self.info_label = QLabel("NL-DB  |  No database  |  Ollama: Checking...")
        self.info_label.setObjectName("infoLabel")
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()

    # ── Main 3-panel Layout ──────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Info bar at top
        root_layout.addWidget(self.info_bar)

        # Content area with padding
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(0)

        # Splitter with 3 panels
        self.splitter = QSplitter(Qt.Horizontal)

        self.db_browser = DBBrowser()
        self.query_panel = QueryPanel()
        self.schema_inspector = SchemaInspector()

        self.splitter.addWidget(self.db_browser)
        self.splitter.addWidget(self.query_panel)
        self.splitter.addWidget(self.schema_inspector)

        # Proportions ~25% / 50% / 25%
        self.splitter.setSizes([250, 500, 250])

        content_layout.addWidget(self.splitter)
        root_layout.addWidget(content, 1)

    # ── Status Bar ────────────────────────────────────────────
    def _setup_status_bar(self):
        sb = QStatusBar()
        sb.setObjectName("mainStatusBar")
        self.setStatusBar(sb)
        self._status_ready = QLabel("Ready")
        self._status_rows = QLabel("")
        self._status_shortcuts = QLabel("Query History  |  Ctrl+; Settings  |  Ctrl+N: New DB")
        sb.addWidget(self._status_ready)
        sb.addWidget(self._status_rows, 1)
        sb.addPermanentWidget(self._status_shortcuts)

    # ── Signal Wiring ─────────────────────────────────────────
    def _connect_signals(self):
        # DB opened → all panels + info bar
        self.db_browser.db_opened.connect(self.query_panel.set_db_config)
        self.db_browser.db_opened.connect(self.schema_inspector.set_db_config)
        self.db_browser.db_opened.connect(self._on_db_opened)

        # Table selected in browser → schema inspector
        self.db_browser.table_selected.connect(self.schema_inspector.update_table)

        # Query signals
        self.query_panel.query_executed.connect(self._on_query_executed)
        self.query_panel.query_added.connect(self.schema_inspector.add_query)

        # Schema inspector history click → fill query panel
        self.schema_inspector.query_clicked.connect(self.query_panel.fill_query)

        # Menu actions → browser
        self._open_act.triggered.connect(self.db_browser.on_open_db)
        self._new_act.triggered.connect(self.db_browser.on_new_db)
        self._pg_act.triggered.connect(self.db_browser.on_pg_connect)

        # View toggles
        self._toggle_schema_act.triggered.connect(
            lambda: self.schema_inspector.setVisible(not self.schema_inspector.isVisible())
        )
        self._toggle_sql_act.triggered.connect(self.query_panel.toggle_sql)

    # ── Slots ─────────────────────────────────────────────────
    def _on_db_opened(self, config):
        db_name = self.db_browser.get_db_display_name()
        self.info_label.setText(
            f"NL-DB  |  {db_name}  |  Ollama: Connected (qwen2.5:3b)"
        )
        self._status_ready.setText("Ready")
        self._status_rows.setText(f"| Connected to {db_name}")

    def _on_query_executed(self, sql, row_count):
        self._status_ready.setText("Ready")
        self._status_rows.setText(f"| {row_count} rows returned")

    def closeEvent(self, event):
        if hasattr(self, 'query_panel'):
            self.query_panel.shutdown()
        super().closeEvent(event)
