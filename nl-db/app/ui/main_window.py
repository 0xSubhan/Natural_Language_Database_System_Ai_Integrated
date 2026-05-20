from PySide6.QtWidgets import QMainWindow, QSplitter, QWidget, QHBoxLayout
from PySide6.QtCore import Qt
from app.ui.db_browser import DBBrowser
from app.ui.query_panel import QueryPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NL-DB Lightweight App")
        self.resize(1000, 600)
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        self.db_browser = DBBrowser()
        self.query_panel = QueryPanel()
        
        splitter.addWidget(self.db_browser)
        splitter.addWidget(self.query_panel)
        
        # Set initial sizes (e.g. 30% left, 70% right)
        splitter.setSizes([300, 700])
        
        # Connect signals
        self.db_browser.db_opened.connect(self.query_panel.set_db_config)
