from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QFrame
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from app.query_handler import handle_nl_query, DestructiveQueryError, explain_sql

class ExplainWorker(QThread):
    finished_explanation = Signal(str)

    def __init__(self, sql, nl_text, parent=None):
        super().__init__(parent)
        self.sql = sql
        self.nl_text = nl_text

    def run(self):
        explanation = explain_sql(self.sql, self.nl_text)
        self.finished_explanation.emit(explanation)
from app.ui.safety_dialog import SafetyDialog
from app.db_connection import get_db_connection

class QueryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_db_config = None
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # NL Input Area
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("Type your plain English query here...\n(e.g., 'Show me all users who signed up this month')")
        self.input_edit.setMaximumHeight(100)
        layout.addWidget(self.input_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Run Query")
        self.btn_run.setToolTip("Ctrl+Enter")
        self.btn_run.clicked.connect(self.on_run_query)
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setToolTip("Esc")
        # Cancel just clears for synchronous MVP or closes dialog
        self.btn_cancel.clicked.connect(self.on_cancel)
        
        btn_layout.addWidget(self.btn_run)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        
        self.status_label = QLabel("Ready")
        btn_layout.addWidget(self.status_label)
        layout.addLayout(btn_layout)

        # SQL Display (Amber Box)
        self.sql_box = QFrame()
        self.sql_box.setStyleSheet("background-color: #FFF8E1; border: 1px solid #FFC107; border-radius: 4px;")
        sql_layout = QVBoxLayout(self.sql_box)
        self.sql_label = QLabel("Generated SQL:")
        self.sql_label.setStyleSheet("font-weight: bold; color: #555;")
        self.sql_content = QTextEdit()
        self.sql_content.setReadOnly(True)
        self.sql_content.setMaximumHeight(80)
        self.sql_content.setStyleSheet("background-color: transparent; border: none; font-family: monospace; color: #333;")
        
        self.explanation_label = QLabel("Explanation:")
        self.explanation_label.setStyleSheet("font-weight: bold; color: #555; margin-top: 5px;")
        self.explanation_content = QTextEdit()
        self.explanation_content.setReadOnly(True)
        self.explanation_content.setMaximumHeight(80)
        self.explanation_content.setStyleSheet("background-color: transparent; border: none; color: #333;")

        sql_layout.addWidget(self.sql_label)
        sql_layout.addWidget(self.sql_content)
        sql_layout.addWidget(self.explanation_label)
        sql_layout.addWidget(self.explanation_content)
        layout.addWidget(self.sql_box)
        self.sql_box.hide() # Hidden by default

        # Results Table
        self.table = QTableWidget()
        layout.addWidget(self.table)

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Return"), self, self.on_run_query)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self.on_run_query)
        QShortcut(QKeySequence("Ctrl+S"), self, self.toggle_sql)
        QShortcut(QKeySequence("Esc"), self, self.on_cancel)

    def set_db_config(self, config: dict):
        self.current_db_config = config
        self.status_label.setText(f"Connected to DB")

    def toggle_sql(self):
        self.sql_box.setVisible(not self.sql_box.isVisible())

    def on_cancel(self):
        self.input_edit.clear()

    def on_run_query(self):
        if not self.current_db_config:
            self.status_label.setText("Error: No database opened.")
            return

        nl_text = self.input_edit.toPlainText().strip()
        if not nl_text:
            return
            
        self.status_label.setText("Generating query...")
        self.btn_run.setEnabled(False)
        
        # Use QTimer to allow UI update before blocking call
        QTimer.singleShot(100, lambda: self._execute_query(nl_text))
        
    def _execute_query(self, nl_text):
        try:
            result = handle_nl_query(nl_text, self.current_db_config)
            self.sql_content.setText(result.get("sql", ""))
            self._render_results(result, nl_text)
        except DestructiveQueryError as e:
            self.sql_content.setText(e.sql)
            dialog = SafetyDialog(str(e), self)
            if dialog.exec():
                self._execute_sql_direct(e.sql)
            else:
                self.status_label.setText("Query cancelled by user.")
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
        finally:
            self.btn_run.setEnabled(True)

    def _execute_sql_direct(self, sql):
        db = get_db_connection(self.current_db_config)
        db.connect(self.current_db_config)
        try:
            cursor = db.conn.cursor()
            cursor.execute(sql)
            db.conn.commit()
            affected = cursor.rowcount
            result = {"sql": sql, "columns": [], "rows": [], "affected": affected, "error": None}
            self._render_results(result, None)
        except Exception as e:
            self.status_label.setText(f"Execution Error: {str(e)}")
        finally:
            db.disconnect()

    def _render_results(self, result, nl_text=None):
        if result.get("error"):
            self.status_label.setText(f"Error: {result['error']}")
            return
            
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        affected = result.get("affected", 0)
        
        if columns:
            self.table.setColumnCount(len(columns))
            self.table.setHorizontalHeaderLabels(columns)
            self.table.setRowCount(len(rows))
            
            for row_idx, row_data in enumerate(rows):
                for col_idx, col_data in enumerate(row_data):
                    self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(col_data)))
                    
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            self.status_label.setText(f"Returned {len(rows)} rows.")
        else:
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.status_label.setText(f"Query executed. {affected} rows affected.")

        if nl_text and result.get("sql"):
            self.explanation_content.setText("Generating explanation...")
            self.sql_box.show()
            self.worker = ExplainWorker(result["sql"], nl_text, self)
            self.worker.finished_explanation.connect(self._on_explanation_ready)
            self.worker.start()

    def _on_explanation_ready(self, explanation: str):
        self.explanation_content.setText(explanation)
