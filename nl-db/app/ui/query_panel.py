import csv
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from app.query_handler import handle_nl_query, DestructiveQueryError, explain_sql, analyze_database


class ExplainWorker(QThread):
    finished_explanation = Signal(str)

    def __init__(self, sql, nl_text, parent=None):
        super().__init__(parent)
        self.sql = sql
        self.nl_text = nl_text

    def run(self):
        explanation = explain_sql(self.sql, self.nl_text)
        self.finished_explanation.emit(explanation)


class AnalyzeWorker(QThread):
    finished_analysis = Signal(str)

    def __init__(self, nl_text, db_config, parent=None):
        super().__init__(parent)
        self.nl_text = nl_text
        self.db_config = db_config

    def run(self):
        analysis = analyze_database(self.nl_text, self.db_config)
        self.finished_analysis.emit(analysis)


from app.ui.safety_dialog import SafetyDialog
from app.db_connection import get_db_connection


class QueryPanel(QWidget):
    query_executed = Signal(str, int)   # sql, row_count
    query_added = Signal(str)           # nl_text for history

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_db_config = None
        self.explanation_min_height = 80
        self.last_columns = []
        self.last_rows = []
        self.setup_ui()
        self.setup_shortcuts()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Section title
        title = QLabel("Natural Language Query Panel")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # NL Input Area
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            "Type a question in plain English...\n"
            "e.g. show top 5 customers by total spend"
        )
        self.input_edit.setMaximumHeight(80)
        self.input_edit.setObjectName("nlInput")
        layout.addWidget(self.input_edit)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_cancel = QPushButton("Cancel Exec")
        self.btn_cancel.setObjectName("btnCancelExec")
        self.btn_cancel.setToolTip("Esc")
        self.btn_cancel.clicked.connect(self.on_cancel)

        self.btn_run = QPushButton("Run NatLang")
        self.btn_run.setObjectName("btnRunNatLang")
        self.btn_run.setToolTip("Ctrl+Enter")
        self.btn_run.clicked.connect(self.on_run_query)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_run)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # SQL Display
        self.sql_box = QFrame()
        self.sql_box.setObjectName("sqlBox")
        sql_layout = QVBoxLayout(self.sql_box)
        sql_layout.setContentsMargins(10, 10, 10, 10)
        sql_layout.setSpacing(6)

        self.sql_label = QLabel("Generated SQL:")
        self.sql_label.setObjectName("schemaSectionLabel")
        self.sql_content = QTextEdit()
        self.sql_content.setReadOnly(True)
        self.sql_content.setMaximumHeight(60)
        self.sql_content.setObjectName("sqlContent")

        sql_layout.addWidget(self.sql_label)
        sql_layout.addWidget(self.sql_content)
        layout.addWidget(self.sql_box)
        self.sql_box.hide()

        # Results label
        self.results_label = QLabel("Results:")
        self.results_label.setObjectName("schemaSectionLabel")
        layout.addWidget(self.results_label)

        # Results Table
        self.table = QTableWidget()
        layout.addWidget(self.table)

        # Export CSV row
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        self.btn_export = QPushButton("Export CSV")
        self.btn_export.setObjectName("btnExportCSV")
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.clicked.connect(self.on_export_csv)
        self.btn_export.hide()
        export_layout.addWidget(self.btn_export)
        layout.addLayout(export_layout)

        # Explanation
        self.explanation_box = QFrame()
        self.explanation_box.setObjectName("explanationBox")
        expl_layout = QVBoxLayout(self.explanation_box)
        expl_layout.setContentsMargins(10, 10, 10, 10)
        expl_layout.setSpacing(6)

        self.explanation_label = QLabel("Plain English Explanation:")
        self.explanation_label.setObjectName("schemaSectionLabel")
        self.explanation_content = QTextEdit()
        self.explanation_content.setReadOnly(True)
        self.explanation_content.setObjectName("explanationContent")
        self.explanation_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.explanation_content.setMinimumHeight(self.explanation_min_height)
        self.explanation_content.textChanged.connect(self._adjust_explanation_height)

        expl_layout.addWidget(self.explanation_label)
        expl_layout.addWidget(self.explanation_content)
        layout.addWidget(self.explanation_box)
        self.explanation_box.hide()

        # Status label (kept for internal use, but status bar is primary)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusInline")
        self.status_label.hide()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Return"), self, self.on_run_query)
        QShortcut(QKeySequence("Ctrl+Enter"), self, self.on_run_query)
        QShortcut(QKeySequence("Ctrl+S"), self, self.toggle_sql)
        QShortcut(QKeySequence("Esc"), self, self.on_cancel)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjust_explanation_height()

    def set_db_config(self, config):
        self.current_db_config = config
        # Clear all previous state when switching databases
        self.input_edit.clear()
        self.sql_content.clear()
        self.sql_box.hide()
        self.explanation_content.clear()
        self.explanation_box.hide()
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.results_label.setText("Results:")
        self.btn_export.hide()
        self.last_columns = []
        self.last_rows = []

    def toggle_sql(self):
        self.sql_box.setVisible(not self.sql_box.isVisible())

    def on_cancel(self):
        self.input_edit.clear()

    def fill_query(self, text):
        """Fill the input box with a query (e.g. from history)."""
        self.input_edit.setText(text)

    def on_run_query(self):
        if not self.current_db_config:
            self.status_label.setText("Error: No database opened.")
            return
        nl_text = self.input_edit.toPlainText().strip()
        if not nl_text:
            return
        self.btn_run.setEnabled(False)
        self.query_added.emit(nl_text)
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
            self.status_label.setText(f"Error: {e}")
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
            self.status_label.setText(f"Execution Error: {e}")
        finally:
            db.disconnect()

    def _render_results(self, result, nl_text=None):
        if result.get("error"):
            self.status_label.setText(f"Error: {result['error']}")
            return
        columns = result.get("columns", [])
        rows = result.get("rows", [])
        affected = result.get("affected", 0)

        self.last_columns = columns
        self.last_rows = rows

        if columns:
            self.table.setColumnCount(len(columns))
            self.table.setHorizontalHeaderLabels(columns)
            self.table.setRowCount(len(rows))
            for r_idx, r_data in enumerate(rows):
                for c_idx, c_data in enumerate(r_data):
                    self.table.setItem(r_idx, c_idx, QTableWidgetItem(str(c_data)))
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            self.results_label.setText(f"Results ({len(rows)} rows):")
            self.btn_export.show()
            self.query_executed.emit(result.get("sql", ""), len(rows))
        else:
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.results_label.setText(f"Query executed. {affected} rows affected.")
            self.btn_export.hide()

        # Show SQL box
        self.sql_box.show()
        self.sql_label.setText(f"Generated SQL ({len(columns)} Cols):")

        if nl_text and result.get("sql"):
            self.explanation_content.setText("Generating explanation...")
            self.explanation_box.show()
            self._adjust_explanation_height()
            self.worker = ExplainWorker(result["sql"], nl_text, self)
            self.worker.finished_explanation.connect(self._on_explanation_ready)
            self.worker.start()

    def _on_explanation_ready(self, explanation):
        self.explanation_content.setText(explanation)
        self._adjust_explanation_height()

    def on_analyze_db(self):
        if not self.current_db_config:
            return
        nl_text = self.input_edit.toPlainText().strip()
        if not nl_text:
            return
        self.btn_run.setEnabled(False)
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setColumnCount(0)
        self.sql_box.show()
        self.sql_content.setText("-- N/A (Analysis Mode) --")
        self.explanation_content.setText("Generating analysis...")
        self.explanation_box.show()
        self._adjust_explanation_height()
        self.analyze_worker = AnalyzeWorker(nl_text, self.current_db_config, self)
        self.analyze_worker.finished_analysis.connect(self._on_analysis_ready)
        self.analyze_worker.start()

    def _on_analysis_ready(self, analysis):
        self.explanation_content.setText(analysis)
        self._adjust_explanation_height()
        self.btn_run.setEnabled(True)

    def on_export_csv(self):
        if not self.last_columns:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv);;All Files (*)")
        if not path:
            return
        if not path.endswith(".csv"):
            path += ".csv"
        try:
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(self.last_columns)
                writer.writerows(self.last_rows)
        except Exception:
            pass

    def _adjust_explanation_height(self):
        vw = self.explanation_content.viewport().width()
        if vw > 0:
            self.explanation_content.document().setTextWidth(vw)
        doc_h = self.explanation_content.document().size().height()
        margins = self.explanation_content.contentsMargins()
        frame = self.explanation_content.frameWidth()
        new_h = int(doc_h + margins.top() + margins.bottom() + (frame * 2))
        if new_h < self.explanation_min_height:
            new_h = self.explanation_min_height
        self.explanation_content.setFixedHeight(new_h)

    def shutdown(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        if hasattr(self, 'analyze_worker') and self.analyze_worker.isRunning():
            self.analyze_worker.terminate()
            self.analyze_worker.wait()
