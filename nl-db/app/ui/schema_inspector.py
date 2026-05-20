from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QFrame, QScrollArea, QSizePolicy, QPushButton
)
from PySide6.QtCore import Qt, Signal
from app.db_connection import get_db_connection


class SchemaInspector(QWidget):
    """Right-side panel showing column details, sample data, and query history."""
    query_clicked = Signal(str)  # Emitted when a history item is clicked

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = None
        self.current_db_config = None
        self.query_history_list = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # --- Title ---
        self.title_label = QLabel("Schema Inspector")
        self.title_label.setObjectName("sectionTitle")
        layout.addWidget(self.title_label)

        self.table_name_label = QLabel("No table selected")
        self.table_name_label.setObjectName("schemaSubtitle")
        layout.addWidget(self.table_name_label)

        # --- Scrollable content area ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("schemaScroll")

        scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(8)

        # --- Column pills container ---
        self.columns_frame = QFrame()
        self.columns_frame.setObjectName("columnsFrame")
        self.columns_layout = QVBoxLayout(self.columns_frame)
        self.columns_layout.setContentsMargins(0, 0, 0, 0)
        self.columns_layout.setSpacing(4)
        self.scroll_layout.addWidget(self.columns_frame)

        # --- Sample Data section ---
        self.sample_label = QLabel("Sample (0 rows):")
        self.sample_label.setObjectName("schemaSectionLabel")
        self.scroll_layout.addWidget(self.sample_label)

        self.sample_list = QListWidget()
        self.sample_list.setObjectName("sampleList")
        self.sample_list.setMaximumHeight(120)
        self.scroll_layout.addWidget(self.sample_list)

        # --- Query History section ---
        self.history_label = QLabel("Query History:")
        self.history_label.setObjectName("schemaSectionLabel")
        self.scroll_layout.addWidget(self.history_label)

        self.history_frame = QFrame()
        self.history_frame.setObjectName("historyFrame")
        self.history_layout = QVBoxLayout(self.history_frame)
        self.history_layout.setContentsMargins(0, 0, 0, 0)
        self.history_layout.setSpacing(4)
        self.scroll_layout.addWidget(self.history_frame)

        self.scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def set_db_config(self, config: dict):
        """Called when a database is opened."""
        self.current_db_config = config
        self.db = get_db_connection(config)
        try:
            self.db.connect(config)
        except Exception:
            self.db = None

        # Clear all previous state when switching databases
        self.table_name_label.setText("No table selected")
        # Clear column pills
        while self.columns_layout.count():
            item = self.columns_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Clear sample data
        self.sample_list.clear()
        self.sample_label.setText("Sample (0 rows):")
        # Clear query history
        self.query_history_list.clear()
        self._refresh_history_buttons()

    def update_table(self, table_name: str):
        """Update the inspector to show schema and sample data for the given table."""
        self.table_name_label.setText(f"Table: {table_name}")

        # Clear old column pills
        while self.columns_layout.count():
            item = self.columns_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.db:
            return

        # Get schema for this table
        try:
            schema = self.db.get_schema()
        except Exception:
            return

        columns = schema.get(table_name, [])

        for col in columns:
            pill_text = f"{col['name']}  {col['type']}"
            tags = []
            if col.get("pk"):
                tags.append("PK")
            if col.get("notnull"):
                tags.append("NOT NULL")
            if col.get("unique"):
                tags.append("UNIQUE")
            if col.get("default") is not None:
                tags.append(f"DEFAULT {col['default']}")
            if tags:
                pill_text += "  " + "  ".join(tags)

            pill = QLabel(pill_text)
            pill.setObjectName("columnPill")
            pill.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            pill.setWordWrap(False)
            pill.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.columns_layout.addWidget(pill)

        # Get sample rows
        try:
            sample = self.db.get_sample_rows(table_name, limit=3)
        except Exception:
            sample = {"columns": [], "rows": []}

        self.sample_list.clear()
        sample_rows = sample.get("rows", [])
        sample_cols = sample.get("columns", [])
        self.sample_label.setText(f"Sample ({len(sample_rows)} rows):")

        for i, row in enumerate(sample_rows, 1):
            # Show abbreviated row content
            parts = []
            for ci, val in enumerate(row):
                col_name = sample_cols[ci] if ci < len(sample_cols) else f"col{ci}"
                text = str(val) if val is not None else "NULL"
                if len(text) > 20:
                    text = text[:17] + "..."
                parts.append(f"{col_name}: {text}")
            display = f"{i}. " + ", ".join(parts)
            if len(display) > 80:
                display = display[:77] + "..."
            self.sample_list.addItem(display)

    def add_query(self, query_text: str):
        """Add a query to the history."""
        # Avoid duplicates at the top
        if self.query_history_list and self.query_history_list[0] == query_text:
            return
        self.query_history_list.insert(0, query_text)
        # Keep max 10
        self.query_history_list = self.query_history_list[:10]
        self._refresh_history_buttons()

    def _refresh_history_buttons(self):
        """Rebuild the query history buttons."""
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for q in self.query_history_list[:5]:
            display = q if len(q) <= 30 else q[:27] + "..."
            btn = QPushButton(display)
            btn.setObjectName("historyBtn")
            btn.setToolTip(q)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, text=q: self.query_clicked.emit(text))
            self.history_layout.addWidget(btn)
